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

## Data modes

The optional **Sample dataset** mode reads the existing five CSV files under `data/sample/` through an allowlisted local server. It does not create or rebuild the database. Buildings and room identities come from the CSVs; selected-time occupancy uses the latest reading at or before that time. Missing data is never treated as zero. Sample-mode crowd bands mirror the API contract; API mode uses the server's room crowd bands directly.

**Local backend API is the default.** Start FastAPI using `src/backend/README.md` before opening the frontend. The local frontend server proxies `/api/*` to `http://127.0.0.1:8000`, avoiding cross-origin configuration. Set `API_ORIGIN` before starting to change this address. Backend errors are shown explicitly; the interface does not silently substitute sample data. `/events/today` returns today's Singapore events regardless of the selected occupancy date, and the UI labels this distinction.

The default view is 30 September 2026 at 15:00 SGT. Data covers 31 August–27 December 2026, 08:00–20:00. Saved predictions cover only 29 September at 16:00 and 17:00; other times show forecast unavailability. Occupancy is generated, not live sensors or booking availability. W5 room codes require confirmation.

## Interface and map

The main map embeds the actual visitor map used by SIT's official Campus Wayfinder: https://pcmap-sit-visitor.netlify.app/. The provider retains its search, pan/zoom and floor-selection controls; map assets/code are not copied or rehosted. The standalone map was inspected in-browser. The embedded map stayed blank in the Codex in-app preview during verification, so embedded operation is **not verified**. A visible direct-map link and reload control are included; the official map requires internet access.

The map is a cross-origin third-party application. Its clicks do not filter Occuscope, and Occuscope does not inject occupancy colours into it. A supported provider SDK/message API and a verified room-to-map coordinate mapping would be needed for synchronized selection and a crowd overlay. Do not claim these are implemented.

Occuscope provides separate building/floor/type/crowd filters, room search, location details and daily occupancy charts for 32 spaces across E2, E6, W1, W3 and W5. The **Crowd positions** view uses API `map_x` / `map_y` (normalized dataset coordinates), with building selection fitting the selected points. It is explicitly labelled as uncalibrated to the official map. Unknown/null coordinates are omitted from this plot, while those rooms remain in the list. Occupancy ratio sizes the room-card meters; server `crowd_level` controls their CSS presentation. No colour or crowd band is sent as an API input. Sidebar building indicators aggregate mapped-room counts and capacities only.

Default request: `GET /occupancy/current?at=2026-09-30T15:00:00+08:00`. `URLSearchParams` encodes the plus as `%2B`. The client does not read the unfiltered latest-row database view. Room selection joins by `location_id`. Missing readings remain unknown, not zero.

Responsive layouts, keyboard-operated buttons, visible focus indicators, labelled controls, text crowd labels and accessible chart descriptions are included. Fonts optionally load from Google Fonts, with system fallbacks offline. All local sample data remains usable without internet access.

## Files and deployment

- `index.html`: application shell, official map embed and coordinate-view container.
- `styles.css`: responsive visual design.
- `app.js`: views, controls, asynchronous loading and API integration.
- `data.js`: CSV parsing, sample readings and data adapters.
- `server.mjs`: loopback-only development server with an explicit static-file allowlist and API proxy. Does not expose the repository or `.env` files.

For cloud deployment, serve the four frontend assets through the team's chosen hosting service and route `/api/` through a same-origin reverse proxy. Sample mode additionally requires the five `/sample/` CSV routes. The local server is a development tool, not a production hosting/security implementation.

## Manual functional check

1. Start the API and frontend, then open the default API view: 32 spaces at 30 September 2026, 15:00 SGT.
2. Select E2, then Level 4: DR223 and DR224 appear.
3. Choose Crowd positions, select DR223, and verify 3/8 people, 38% displayed, moderate, generated, and the 30 September 15:00 timestamp.
4. The daily chart is populated. The forecast states that no saved forecast exists for this time; September 29 forecasts are not relabelled.
5. Choose Campus map. If the embedded provider map is blank, open the visible direct-map link. Search a room and use the provider's floor/zoom controls. These do not synchronize with Occuscope's filters.
6. Choose Sample dataset explicitly for offline occupancy. API mode never silently falls back.
7. Stop the API and refresh: an error and retry action appear, with no stale occupancy cards.

## Integration test

With both servers running, from `src/frontend`:

```powershell
$env:OCCUSCOPE_INTEGRATION='1'
node --test tests/*.test.mjs
```

Checks 32 distinct rooms at the requested teaching-day timestamp, required fields, nonzero counts, generated source, ratio/band consistency, and rejection of requests with no `at` argument. Without the environment flag, only this integration test is skipped.
