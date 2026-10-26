# Trail data pipeline

Builds the offline trail pack bundled in the app (the app's TrailData resources). Run on a Mac or Linux box; nothing here runs in the app, and nothing is uploaded.

## Rebuild Pennsylvania
```sh
python3 -m venv .venv && . .venv/bin/activate && pip install osmium
curl -LO https://download.geofabrik.de/north-america/us/pennsylvania-latest.osm.pbf   # ~350 MB
python3 script/build_trail_pack.py osm pennsylvania-latest.osm.pbf TrailsPennsylvania --region Pennsylvania
# then copy TrailsPennsylvania.bin and .json into the app's TrailData resources
```
The extract date in the JSON comes from the .pbf header and is shown in the app's credit. Same input gives byte-identical output.

## Test fixture
```sh
python3 script/build_trail_pack.py json script/test_fixture_trails.overpass.json trail_walk_pack --region "Test fixture"
```

## What is kept
`highway=path|track|bridleway|steps`, plus `footway` and `cycleway` when named (named cycleways are bike paths, greenways and rail trails such as the Lackawanna River Heritage Trail). Sidewalks and crossings (`footway=sidewalk|crossing`, `cycleway=sidewalk|crossing`) are dropped, and so is a path, footway, steps, track or cycleway whose name matches a street's name (a sidewalk, town stairway or unpaved alley mapped on its own, e.g. "Pine Street"; service roads don't count as streets because trail access roads often carry the trail name). Filter tests: `python3 script/test_build_trail_pack.py`. Ways with fewer than 2 points are dropped. Name: way `name`, else `ref`, else the name of a `route=hiking|foot` relation it belongs to.

## Format THRVETP1 (little-endian)
- `"THRVETP1"` (8 bytes), `UInt32` tile count.
- Index, sorted by (lat, lon): `Int32 latIndex, Int32 lonIndex, UInt32 offset (from body start), UInt32 length`. Index = floor(degrees / 0.05).
- Body: one raw-deflate blob per tile. Decoded: varint trail count, then per trail: varint way id, `UInt8` kind (0 path, 1 footway, 2 track, 3 bridleway, 4 steps, 5 cycleway), varint-length UTF-8 name (empty = none), varint-length sac_scale, varint point count, zigzag-varint deltas of lat/lon in 1e-5°.
- A way is stored in every tile its segments' bounding boxes touch.

## Licence
Data © OpenStreetMap contributors, ODbL 1.0. The pack is a derivative database of OpenStreetMap. Shipping it in the app is a public use, so ODbL asks for the credit (shown in the app) and for the derived database, or a way to recreate it (this script plus the named source extract), to be offered under ODbL.
