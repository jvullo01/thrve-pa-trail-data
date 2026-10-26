# THRVE Pennsylvania trail pack: OpenStreetMap derived database

THRVE (iOS) ships a Pennsylvania trail pack inside the app so it can draw trail lines offline. THRVE downloads nothing to show them (the trail data never comes from a network); Apple's base map under the trails loads map tiles from Apple. The pack is a derivative database of OpenStreetMap.

## Credit
© OpenStreetMap contributors, ODbL. https://www.openstreetmap.org/copyright

## Licence
- Data (`data/TrailsPennsylvania.bin`, `data/TrailsPennsylvania.json`): Open Database License 1.0 (ODbL), © OpenStreetMap contributors, https://opendatacommons.org/licenses/odbl/1-0/. Any public use must credit OpenStreetMap contributors, and any adapted database you share must also be under ODbL.
- Script (`script/`): MIT License, see `LICENSE`.

The data is derived from the Geofabrik extract `pennsylvania-261024.osm.pbf` (OpenStreetMap data as of 2026-10-24), as noted in `EXTRACT_RECIPE.md`. Full ODbL text: `LICENSE-DATA`.

## Contents
- `data/TrailsPennsylvania.bin`: the pack exactly as shipped in THRVE 1.0 (14). 6,298,580 bytes, SHA-256 308c868d52df1bade5ee06898f795f62fbc80ad2072e7841f73eab382a5380ad. It holds 106,565 trails (24,666 named) in 4,645 tiles of 0.05°.
- `data/TrailsPennsylvania.json`: the pack metadata (source, extract date, licence, counts).
- `script/build_trail_pack.py`: the build script. `script/test_build_trail_pack.py` holds the filter tests and `script/test_fixture_trails.overpass.json` is a small test fixture.
- `script/PIPELINE.md`: the pipeline notes and the binary format.
- `EXTRACT_RECIPE.md`: the source extract (name, date, URL, MD5), the rebuild steps and the filter rules.
