# Objective

Verify one user workflow end to end on the local stack: pick building E2, floor 4, room DR223, read the crowd level for a teaching-day hour, view the day's history, and see today's events, with no live-sensor claim.

# Setup

From the repository root: Python 3.11+ (`.venv` with FastAPI and httpx), Node 18+ (no `npm install` required for the dev server). Rebuild SQLite with `python src/db/init_app_db.py`. Start the API (`uvicorn src.backend.api:app --port 8000`) and the frontend proxy (`node src/frontend/server.mjs` on port 5173). This run is **local only**, not the deployed AWS stack (API Gateway / Lambda / S3).

# Command / steps

1. **2a — Proxy API:** `GET /api/buildings`, `GET /api/locations?building_id=E2&floor=4`, `GET /api/occupancy/current` (no `at`), `GET /api/occupancy/current?at=2026-09-30T15:00:00%2B08:00` via `http://127.0.0.1:5173`.
2. **2b — DR223 and floors:** Python check on saved `cur.json`; distinct floors for W3 and W5 from `/api/locations`.
3. **2c — Chart data:** `GET /api/occupancy/E2-04-20-DR223?from=…&to=…` and `GET /api/occupancy/E2-04-20-DR223/prediction`.
4. **2d — Events:** `GET /api/events/today`.
5. **2e — Frontend tests:** `OCCUSCOPE_INTEGRATION=1` and `node --test tests/*.test.mjs` under `src/frontend`.
6. **2f — Static copy:** `curl` index and `app.js` for generated / live-sensor wording.
7. **2g — Browser:** not run by Ryan this session (see Zi Qian's map evidence).

Full command output: `evidence/functional-run-local.txt`.

# Expected result

- Buildings include E2, E6, W1, W3, W5; E2 floor 4 lists DR223 and DR224 (`location_id` `E2-04-20-DR223`, `E2-04-21-DR224`).
- `/api/occupancy/current` without `at` returns **422**; with demo `at` returns a **47-row** JSON array.
- DR223 at `2026-09-30T15:00:00+08:00`: `occupancy_count` 3, `capacity` 8, `crowd_level` `moderate`, `source` `generated`, matching timestamp.
- W3 floors 3, 4, 6, 7, 8; W5 floors 3, 5, 7, 8.
- Timeline for DR223 on 30 Sep: non-empty hourly list, every `source` is `generated`; prediction is a list (may be older than 30 Sep).
- `/api/events/today` returns **200** and a JSON list (may be empty).
- Frontend automated tests: all pass with both servers up.
- UI copy states generated / not live sensors (negation acceptable).

# Actual result

**Servers (Step 1):** API **200** on `/buildings`, frontend **200** on `/` (after using `C:\Windows\System32\curl.exe`; `curl.exe` was not on PATH in this shell).

| Sub-check | Result |
|---|---|
| 2a proxy API | **Pass** — five buildings; E2 L4 has DR223/DR224; no-`at` **422**; `cur.json` saved |
| 2b DR223 + floors | **Pass** — 47 rows; DR223 3/8 moderate generated at demo time; W3 `[3,4,6,7,8]`, W5 `[3,5,7,8]` |
| 2c timeline / prediction | **Pass** (retry) — first timeline curl failed (PowerShell stripped query params → 422); retried with quoted URL: **13** hourly rows, all `source` `generated`; prediction **2** rows (29 Sep v0) |
| 2d events | **Pass** — HTTP **200**, **3** events returned for "today" |
| 2e `node --test` | **Pass** — **4** tests, **4** passed, **0** failed |
| 2f static strings | **Pass** — index shows "MODEL-GENERATED DATA" and "Not live sensors"; `app.js` includes "generated occupancy" and chart heading "generated" |
| 2g browser | **Not run** — see `evidence/test-frontend-map.md` (Zi Qian, 30 Sep) |

No teammate bug filed: timeline failure was operator/shell quoting, not API behaviour.

# Date

30 September 2026, run by Ryan.

# Artefact path

- `evidence/functional-run-local.txt`
- `src/frontend/tests/*.test.mjs`
- `evidence/test-frontend-map.md` (Zi Qian — detailed map and browser evidence)
- `src/frontend/README.md` (manual functional check)
- `src/api-contract.md`

# Sign-off (owners)

| Owner | Confirmation |
|---|---|
| Zi Qian (map UI) | TODO: one dated confirmation line |
| Zul (API) | TODO: one dated confirmation line |

# Limitations

Local stack only; occupancy is **generated**, not live SIT sensors. Ryan did not run browser mouse/touch click-through; map UI evidence is Zi Qian's. Deployed API Gateway / Lambda not tested (Slice 4B). Prediction rows may predate the selected teaching day; empty forecast in the UI is expected per frontend README.
