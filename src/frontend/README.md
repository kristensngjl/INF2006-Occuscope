# Occuscope frontend

Dependency-free HTML/CSS/JavaScript frontend. Requires Node.js 18+ for the local server; no package installation is needed.

From the repository root in the VS Code terminal:

```powershell
node src/frontend/server.mjs
```

Open http://127.0.0.1:5173. Stop with Ctrl+C. To run the data tests:

```powershell
cd src/frontend
node --test tests/*.test.mjs
```

## API-only data

Start the backend before opening the frontend. The frontend proxies /api requests to http://127.0.0.1:8000 (override with API_ORIGIN). All buildings, rooms, occupancy, history, predictions and events come from the API. No source selector, CSV loader, sample routes or offline fallback remains. Failed requests show an error and retry. Events use today's Singapore date.

The default view follows Singapore time when that control is on (clamped to 31 August–27 December 2026, 08:00–20:00). Occupancy is generated, not live sensors or booking availability. `GET /occupancy/{id}/prediction?at=` returns the next two generated hours after the selected instant.

## Interface and map

The **3D campus** view is our original procedural model, projected from 3D coordinates into SVG. Select a building to expand its floors, select a floor, then a crowd marker to open that room. Rotate, zoom and reset controls adjust the model. The SIT wayfinder is a reference link only; no provider map is embedded or copied. Shapes and room positions are illustrative, not surveyed architectural plans. The authored scenery includes facade fins, glazing, planted balconies, individual solar panels, entrance canopies, steps, forecourts, benches, planted beds and tree-lined paths. Roads and paths are decorative approximations, not routing data.

The model, floor controls and room list use the current location catalogue: 62 spaces across E2, E6, W1, W3 and W5. W3 includes Levels 3, 4, 6, 7 and 8; W5 includes Levels 3, 5, 7 and 8. The **Crowd positions** view retains the dataset map_x/map_y plot. Server crowd_level controls room marker presentation, while occupancy_ratio controls meters. Missing readings remain unknown.

Example selected-time request: `GET /occupancy/current?at=2026-09-30T15:00:00+08:00`. `URLSearchParams` encodes the plus as `%2B`. The client does not read the unfiltered latest-row database view. Room selection joins by `location_id`. Missing readings remain unknown, not zero.

Responsive layouts, keyboard-operated buttons, visible focus indicators, labelled controls, text crowd labels and accessible chart descriptions are included. Fonts optionally load from Google Fonts, with system fallbacks offline. The backend must be running.

## Files and deployment

- `index.html`: application shell, original model and coordinate-view containers.
- `styles.css`: responsive campus design.
- `login.css`: student login and time-block picker styling.
- `bookings.js`: email/password login, student profile and weekly room reservations.
- `app.js`: views, controls, asynchronous loading and API integration.
- `model.js`: original geometry, projection, camera controls and floor/room selection.
- `data.js`: API requests and display helpers.
- `server.mjs`: loopback-only development server with an explicit static-file allowlist and API proxy. Does not expose the repository or `.env` files.

For cloud deployment, serve the frontend assets through the team's chosen hosting service and route `/api/` through a same-origin reverse proxy.  The local server is a development tool, not a production hosting/security implementation.

## Manual functional check

1. Start the API and frontend, then open the default API view: 62 spaces at the selected Singapore time (Follow Singapore time, or a demo date/hour).
2. Select E2, then Level 4: DR223 and DR224 appear.
3. Choose Crowd positions, select DR223, and verify 3/8 people, 38% displayed, moderate, generated, and the 30 September 15:00 timestamp.
4. The daily chart is populated. The forecast states that no saved forecast exists for this time; September 29 forecasts are not relabelled.
5. Choose 3D campus, select W3 and Level 8: DR15, DR16 and DR17 appear. W5 Level 8 contains DR25 and DR26. Test model rotation, zoom and room selection.
6. Verify there is no source selector; /sample/locations.csv returns 404.
7. Stop the API and refresh: an error and retry action appear, with no stale occupancy cards.

## Integration test

With both servers running, from `src/frontend`:

```powershell
$env:OCCUSCOPE_INTEGRATION='1'
node --test tests/*.test.mjs
```

Checks all current catalogue rooms at the requested teaching-day timestamp, required fields, nonzero counts, generated source, ratio/band consistency, and rejection of requests with no `at` argument. Without the environment flag, only this integration test is skipped.

## Database freshness

Updating the CSVs does not update an existing SQLite database. The API integration test compares occupancy location IDs against the API locations endpoint. The standard init script deletes the existing database; preserve any teammate data before using it. For an isolated preview, seed a separate SQLite file using the existing schema and seed function, and point the backend DATABASE_URL at that file. The frontend never reads CSVs directly.

## Level 5 bridges and reference landmarks

The model includes an illustrative E6–E1 Level 5 connection, supported by SIT's Facilities page (https://www.singaporetech.edu.sg/life-at-sit/facilities). Western bridge spans illustrate the Campus Heart Level 5 Collaboration Loop described by BCA (https://www1.bca.gov.sg/growth-and-transformation/bca-awards/universal-design-excellence-award/award-winners-2025/). Exact western endpoints and all alignments are schematic, not verified navigation routes. E1, E3, E4 and E5 are context landmarks only, identified from the official visitor wayfinder. Their heights and footprints are approximate and they have no invented crowd data. The model now displays at least five levels for bridge context, rather than inferring total building height solely from available rooms. Level 5 selection can legitimately have zero dataset rooms.
