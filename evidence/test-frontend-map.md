# Frontend map and occupancy integration

Date: 29 September 2026. Agent-run checks; team review pending.

## Objective

Use the actual SIT visitor map as an embed/link and query generated occupancy at `2026-09-30T15:00:00+08:00`, never the unfiltered latest seed row.

## Setup and repeatable commands

Node.js development server on 127.0.0.1:5173; existing FastAPI backend on 127.0.0.1:8000. The previously absent local SQLite database was initialized from the repository sample data. Backend dependencies were installed in an isolated verification environment; follow `src/backend/README.md` for a normal local setup.

From the repository root, run the frontend with `node src/frontend/server.mjs` and the backend with `python -m uvicorn src.backend.api:app`. From `src/frontend`, run:

```powershell
$env:OCCUSCOPE_INTEGRATION='1'
node --test tests/*.test.mjs
```

## Expected and actual results

- **PASS:** All five tests passed: CSV quoting; band boundaries and missing data; at-or-before readings; multi-day events; real API through the frontend proxy.
- **PASS:** The real API returned 32 distinct rooms, each timestamped 30 September 2026 at 15:00 SGT, with `map_x`, `map_y`, `occupancy_ratio`, `crowd_level` and generated source. Counts were populated, rather than the mostly empty trimester-break snapshot.
- **PASS:** Omitting `at` returned HTTP 422. The frontend uses `URLSearchParams`, preserving the `+08:00` offset as `%2B08%3A00`; requests contain no colour/crowd-level input.
- **PASS (browser):** E2 -> Level 4 -> Crowd positions displayed two room markers/cards. Selecting DR223 showed 3/8 people, moderate, 38% rounded display, generated source and the requested timestamp. Its daily chart populated; old September 29 forecasts were not presented as September 30 forecasts.
- **VERIFIED STANDALONE:** SIT's official page embeds `https://pcmap-sit-visitor.netlify.app/`. Its standalone interactive map rendered, offered room search, building zoom and a floor selector.
- **UNRESOLVED EMBED:** The same URL stayed blank inside the Codex in-app local preview. No map render success is claimed. The frontend includes a visible direct link and reload action. Check embedding in the intended deployment browser before presenting it as working.

## Limitations and next integration step

The provider's cross-origin map is independent of Occuscope's controls. Map clicks do not select occupancy rooms, and occupancy is not overlaid on provider geometry. Crowd positions are a separate normalized-coordinate diagram, explicitly uncalibrated to the official map. A supported provider integration and verified location-to-map mapping are needed for synchronized map selection/overlays. No private tokens, copied map bundles, or bypasses of browser origin protections were used.

The API's events endpoint returns actual Singapore-today events rather than the selected occupancy date; the UI labels this. The official map requires network access. The UI labels all occupancy as generated, not live sensors or booking availability.
