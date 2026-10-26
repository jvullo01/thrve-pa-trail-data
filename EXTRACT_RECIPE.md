# Recreate the THRVE Pennsylvania trail pack

Source extract (OpenStreetMap data, Geofabrik):
- File: `pennsylvania-261024.osm.pbf` (the dated copy of `pennsylvania-latest.osm.pbf` for 2026-10-24)
- URL: https://download.geofabrik.de/north-america/us/pennsylvania-261024.osm.pbf
- OSM data timestamp: 2026-10-24T20:20:51Z
- Size: 349,315,100 bytes
- MD5 (published by Geofabrik at the URL + `.md5`): `8d54c665e59374aeded290b352325eb8`
  (the local copy used for the build was deleted afterwards, so we have no SHA-256 we computed ourselves; check with `md5sum` after downloading)

Steps:
```sh
python3 -m venv .venv && . .venv/bin/activate && pip install osmium
curl -LO https://download.geofabrik.de/north-america/us/pennsylvania-261024.osm.pbf
md5sum pennsylvania-261024.osm.pbf   # expect 8d54c665e59374aeded290b352325eb8
python3 script/build_trail_pack.py osm pennsylvania-261024.osm.pbf TrailsPennsylvania --region Pennsylvania
sha256sum TrailsPennsylvania.bin     # expect 308c868d52df1bade5ee06898f795f62fbc80ad2072e7841f73eab382a5380ad
```
The same input should give byte-identical output. Geofabrik keeps dated extracts for a limited time only. If the file is gone, ship `data/TrailsPennsylvania.bin` itself, which ODbL accepts.

## Filter rules (what is kept)
- Kept: `highway=path|track|bridleway|steps`. Also `highway=footway` and `highway=cycleway` when they have a name (named cycleways cover bike paths, greenways and rail trails such as the Lackawanna River Heritage Trail).
- Dropped: sidewalks and crossings (`footway=sidewalk|crossing`, `cycleway=sidewalk|crossing`), and any kept way whose name matches a street's name (service roads don't count as streets), plus ways with fewer than 2 points.
- Name: the way's `name`, else its `ref`, else the name of a `route=hiking|foot` relation it belongs to.
- Format THRVETP1: see `script/PIPELINE.md`. Filter tests: `python3 script/test_build_trail_pack.py`.
