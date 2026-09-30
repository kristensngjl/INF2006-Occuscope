# Frontend model and occupancy integration

Date: 30 September 2026. Agent-run checks; human team review pending.

## Implementation

Original procedural 3D-coordinate SVG campus model, with building focus, expanded floors, rotation, zoom and room markers. SIT wayfinder is a reference link only; no iframe or copied provider geometry. Crowd positions remains a separate dataset-coordinate view. Geometry and room placement are illustrative rather than surveyed.

## Data update

Latest CSV catalogue has 47 locations: E2 6, E6 5, W1 13, W3 16, W5 7. Generated occupancy has 72,709 rows; predictions have 94. The existing repository SQLite database still contained 32 locations, so verification used a separately seeded preview SQLite file through DATABASE_URL. The original database was not altered. Sample mode reads the current CSVs directly.

## Verification

- PASS: five frontend data/API tests, including exact API location-ID agreement with the current CSV catalogue. Run OCCUSCOPE_INTEGRATION=1 node --test tests/*.test.mjs from src/frontend with both servers running.
- PASS: GET /occupancy/current at 2026-09-30T15:00:00+08:00 returned all 47 spaces, generated source, populated readings, map_x/map_y, occupancy_ratio and derived crowd_level. No colour is sent. Missing at returns 422.
- PASS: CSV escaping, crowd boundaries, at-or-before readings (no future trimester-break row), and multi-day events.
- PASS (browser, keyboard): W3 expands with floors 3, 4, 6, 7, 8. Level 8 shows DR15/DR16/DR17; DR15 details show 5/8, 63% rounded, moderate, generated and the selected timestamp. Daily history renders.
- PASS (browser, keyboard): W5 expands with floors 3, 5, 7, 8. Level 8 shows DR25/DR26; model rotation changes geometry.
- LIMITATION: automated mouse clicks in the in-app browser did not activate the model during this run, while keyboard activation worked. Manual mouse/touch verification in the intended browser remains necessary.

## Limits

This is an illustrative model, not a surveyed architectural model. Dataset floors determine its displayed height. Coordinates are normalized within each building footprint. Saved forecasts still cover September 29 only; the UI does not relabel them. Events API is Singapore-today, not selected occupancy date. All occupancy is labelled generated, never live sensors or booking availability.

## Visual detail update

Inspected the hosted SIT visitor model as a visual reference, then authored facade, solar-module, entrance and landscape geometry locally. No provider geometry/assets embedded or downloaded. JavaScript syntax and diff checks passed; browser verified W3 Level 8 -> DR15 still shows 5/8, moderate, generated at the selected timestamp.

Level 5 update: syntax check passed. Browser keyboard verification selected E6 Level 5, displayed its bridge and zero occupancy rooms as expected. Campus overview showed context landmark labels and all three schematic bridge spans. Exact geometry and mouse/touch operation still need human verification.

E1 rendering repair: camera-facing cuboid walls now change with rotation. Context landmarks and dataset buildings share a depth-sorted drawing list. E1 has a closed tower shell, two-sided facade fins, glazing divisions and roof structures. Browser screenshots checked default angle and a rotation of nine steps (about 113 degrees); tower walls and roof remain complete. Syntax and diff checks passed. Dimensions remain illustrative.

## API-only update

Earlier sample-mode verification is historical. Removed the source selector, CSV adapter and sample routes. Backend seed files remain unchanged. All four current frontend tests pass, including the API contract, removed sample route returning 404, crowd bands, event overlap and gesture handling.
