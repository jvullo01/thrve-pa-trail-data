#!/usr/bin/env python3
"""Build THRVE's bundled trail pack from an OpenStreetMap extract.

Output (see PIPELINE.md for the byte layout):
  <out>.bin   index + one raw-deflate blob per 0.05-degree square (TrailTile grid)
  <out>.json  metadata shown in the app's credit (source, licence, extract date, counts)

Usage:
  build_trail_pack.py osm   pennsylvania-latest.osm.pbf  TrailsPennsylvania  --region Pennsylvania
  build_trail_pack.py json  overpass_like_fixture.json   trail_walk_pack     --region "Test fixture"

Deterministic: the same input file always produces byte-identical output.
"""
import argparse, json, math, struct, sys, zlib
from collections import defaultdict

TILE_SIZE_DEGREES = 0.05            # must match TrailTile.sizeDegrees in the app
COORDINATE_SCALE = 100_000          # 1e-5 degree (about 1 m)
FILE_MAGIC = b"THRVETP1"
WALKABLE_KINDS = ["path", "footway", "track", "bridleway", "steps", "cycleway"]   # index = kind code in the file
ALWAYS_KEPT_KINDS = {"path", "track", "bridleway", "steps"}           # footway and cycleway only when named
NAMED_ONLY_KINDS = {"footway", "cycleway"}                          # named bike paths and rail trails are trails
HIKING_ROUTE_TYPES = {"hiking", "foot"}
SIDEWALK_FOOTWAY_TAGS = {"sidewalk", "crossing"}                     # footway=* values that are street furniture
TOWN_WALKWAY_KINDS = {"path", "footway", "steps", "track", "cycleway"}  # dropped when named after a street
# Service roads are left out of STREET_KINDS on purpose: trail access roads often carry the trail's name.
STREET_KINDS = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
                "living_street", "motorway_link", "trunk_link", "primary_link", "secondary_link",
                "tertiary_link", "road"}


def tile_index(value):
    return math.floor(value / TILE_SIZE_DEGREES)


def tiles_touched(coordinates):
    """Every square a way passes through (bounding box of each piece, so diagonal crossings are kept)."""
    touched = set()
    for (lat_a, lon_a), (lat_b, lon_b) in zip(coordinates, coordinates[1:]):
        for lat_i in range(tile_index(min(lat_a, lat_b)), tile_index(max(lat_a, lat_b)) + 1):
            for lon_i in range(tile_index(min(lon_a, lon_b)), tile_index(max(lon_a, lon_b)) + 1):
                touched.add((lat_i, lon_i))
    return touched


def normalized_street_name(name):
    return " ".join(name.lower().split()) if name else None


def is_kept(highway, name, footway_tag=None, street_names=frozenset(), cycleway_tag=None):
    """Trails only: sidewalks and crossings, and paths, footways, steps, tracks or cycleways named after a street (a
    sidewalk, bike lane, alley or town stairway mapped as its own way, e.g. "Pine Street"), are dropped so towns don't
    read as "On trail". Cycleways count only when named (rail trails and greenways, e.g. Lackawanna River Heritage Trail)."""
    if footway_tag in SIDEWALK_FOOTWAY_TAGS or cycleway_tag in SIDEWALK_FOOTWAY_TAGS:
        return False
    if highway in TOWN_WALKWAY_KINDS and name and normalized_street_name(name) in street_names:
        return False
    if highway in ALWAYS_KEPT_KINDS:
        return True
    return highway in NAMED_ONLY_KINDS and name is not None


def write_varint(buffer, value):
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            buffer.append(byte | 0x80)
        else:
            buffer.append(byte)
            return


def zigzag(value):
    return (value << 1) ^ (value >> 63)


def write_text(buffer, text):
    encoded = (text or "").encode("utf-8")
    write_varint(buffer, len(encoded))
    buffer.extend(encoded)


def encode_tile(trails):
    payload = bytearray()
    write_varint(payload, len(trails))
    for trail in trails:
        write_varint(payload, trail["id"])
        payload.append(WALKABLE_KINDS.index(trail["highway"]))
        write_text(payload, trail["name"])
        write_text(payload, trail["sac_scale"])
        write_varint(payload, len(trail["coordinates"]))
        previous_lat = previous_lon = 0
        for lat, lon in trail["coordinates"]:
            lat_e5, lon_e5 = round(lat * COORDINATE_SCALE), round(lon * COORDINATE_SCALE)
            write_varint(payload, zigzag(lat_e5 - previous_lat))
            write_varint(payload, zigzag(lon_e5 - previous_lon))
            previous_lat, previous_lon = lat_e5, lon_e5
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)      # raw deflate = Apple's COMPRESSION_ZLIB
    return compressor.compress(bytes(payload)) + compressor.flush()


def write_pack(trails, output_stem, metadata):
    trails_by_tile = defaultdict(list)
    for trail in trails:
        for tile in tiles_touched(trail["coordinates"]):
            trails_by_tile[tile].append(trail)
    tiles = sorted(trails_by_tile)
    blobs = [encode_tile(sorted(trails_by_tile[tile], key=lambda t: t["id"])) for tile in tiles]
    header = bytearray(FILE_MAGIC) + struct.pack("<I", len(tiles))
    offset = 0
    for (lat_i, lon_i), blob in zip(tiles, blobs):
        header += struct.pack("<iiII", lat_i, lon_i, offset, len(blob))
        offset += len(blob)
    with open(output_stem + ".bin", "wb") as pack:
        pack.write(header)
        for blob in blobs:
            pack.write(blob)
    metadata.update({
        "format": "THRVETP1",
        "tileSizeDegrees": TILE_SIZE_DEGREES,
        "tileCount": len(tiles),
        "trailCount": len(trails),
        "namedTrailCount": sum(1 for t in trails if t["name"]),
        "pointCount": sum(len(t["coordinates"]) for t in trails),
        "packBytes": len(header) + offset,
    })
    with open(output_stem + ".json", "w") as meta_file:
        json.dump(metadata, meta_file, indent=2, sort_keys=True)
        meta_file.write("\n")
    return metadata


def trails_from_osm(pbf_path):
    import osmium

    route_name_by_way = {}
    street_names = set()

    class HikingRouteAndStreetNames(osmium.SimpleHandler):
        def way(self, way):
            if way.tags.get("highway") in STREET_KINDS and way.tags.get("name"):
                street_names.add(normalized_street_name(way.tags.get("name")))

        def relation(self, relation):
            tags = relation.tags
            if tags.get("type") != "route" or tags.get("route") not in HIKING_ROUTE_TYPES:
                return
            route_name = tags.get("name") or tags.get("ref")
            if not route_name:
                return
            for member in relation.members:
                if member.type == "w":
                    route_name_by_way.setdefault(member.ref, route_name)

    class WalkableWays(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.trails = []

        def way(self, way):
            highway = way.tags.get("highway")
            if highway not in WALKABLE_KINDS:
                return
            name = way.tags.get("name") or way.tags.get("ref") or route_name_by_way.get(way.id)
            if not is_kept(highway, name, way.tags.get("footway"), street_names, way.tags.get("cycleway")):
                return
            coordinates = [(node.lat, node.lon) for node in way.nodes if node.location.valid()]
            if len(coordinates) < 2:
                return
            self.trails.append({"id": way.id, "highway": highway, "name": name,
                                "sac_scale": way.tags.get("sac_scale"), "coordinates": coordinates})

    HikingRouteAndStreetNames().apply_file(pbf_path)
    handler = WalkableWays()
    handler.apply_file(pbf_path, locations=True, idx="flex_mem")
    header = osmium.io.Reader(pbf_path, osmium.osm.osm_entity_bits.NOTHING).header()
    extract_timestamp = header.get("osmosis_replication_timestamp") or ""
    return handler.trails, extract_timestamp


def trails_from_overpass_json(json_path):
    """Overpass `out tags geom` JSON (used for the deterministic test fixture)."""
    with open(json_path) as source:
        elements = json.load(source)["elements"]
    route_name_by_way = {}
    street_names = {normalized_street_name(e["tags"]["name"]) for e in elements
                    if e["type"] == "way" and e.get("tags", {}).get("highway") in STREET_KINDS and e["tags"].get("name")}
    for relation in (e for e in elements if e["type"] == "relation"):
        route_name = relation.get("tags", {}).get("name") or relation.get("tags", {}).get("ref")
        for member in relation.get("members", []):
            if route_name and member["type"] == "way":
                route_name_by_way.setdefault(member["ref"], route_name)
    trails = []
    for way in (e for e in elements if e["type"] == "way"):
        tags = way.get("tags", {})
        highway = tags.get("highway")
        name = tags.get("name") or tags.get("ref") or route_name_by_way.get(way["id"])
        coordinates = [(p["lat"], p["lon"]) for p in way.get("geometry", []) if p]
        if highway in WALKABLE_KINDS and is_kept(highway, name, tags.get("footway"), street_names, tags.get("cycleway")) and len(coordinates) >= 2:
            trails.append({"id": way["id"], "highway": highway, "name": name,
                           "sac_scale": tags.get("sac_scale"), "coordinates": coordinates})
    return trails, ""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_kind", choices=["osm", "json"])
    parser.add_argument("input_path")
    parser.add_argument("output_stem")
    parser.add_argument("--region", required=True)
    parser.add_argument("--source-url", default="")
    arguments = parser.parse_args()
    if arguments.input_kind == "osm":
        trails, extract_timestamp = trails_from_osm(arguments.input_path)
    else:
        trails, extract_timestamp = trails_from_overpass_json(arguments.input_path)
    trails.sort(key=lambda t: t["id"])
    metadata = write_pack(trails, arguments.output_stem, {
        "region": arguments.region,
        "source": "OpenStreetMap",
        "sourceURL": arguments.source_url,
        "attribution": "© OpenStreetMap contributors",
        "license": "ODbL 1.0",
        "licenseURL": "https://opendatacommons.org/licenses/odbl/1-0/",
        "extractTimestamp": extract_timestamp,
        "extractDate": extract_timestamp[:10],
    })
    json.dump(metadata, sys.stdout, indent=2, sort_keys=True)
    print()


if __name__ == "__main__":
    main()
