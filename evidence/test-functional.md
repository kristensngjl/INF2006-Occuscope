# Objective

Verify one user workflow end to end on the local stack: pick building E2, floor 4, room DR223, read the crowd level for a teaching-day hour, view the day's history, and see today's events, with no live-sensor claim.

# Setup

From the repository root: Python 3.11+ (`.venv` with FastAPI and httpx), Node 18+ (no `npm install` required for the dev server). Rebuild SQLite with `python src/db/init_app_db.py`. Start the API (`uvicorn src.backend.api:app --port 8000`) and the frontend proxy (`node src/frontend/server.mjs` on port 5173). This run is **local only**, not the deployed AWS stack (API Gateway / Lambda / S3).

# Command / steps

1. **2a — Proxy API:** `GET /api/buildings`, `GET /api/locations?building_id=E2&floor=4`, `GET /api/occupancy/current` (no `at`), `GET /api/occupancy/current?at=2026-09-30T15:00:00%2B08:00` via `http://127.0.0.1:5173`.
2. **2b — DR223 and floors:** Python check on saved `cur.json`; distinct floors for W3 and W5 from `/api/locations`.
3. **2c — Chart data:** `GET /api/occupancy/E2-04-20-DR223?from=…&to=…` and `GET /api/occupancy/E2-04-20-DR223/prediction?at=2026-09-30T15:00:00+08:00`.
4. **2d — Events:** `GET /api/events/today`.
5. **2e — Frontend tests:** `OCCUSCOPE_INTEGRATION=1` and `node --test tests/*.test.mjs` under `src/frontend`.
6. **2f — Static copy:** `curl` index and `app.js` for generated / live-sensor wording.
7. **2g — Browser:** follow **Ryan click-through (10 Oct)** below. Same steps as `src/frontend/README.md` Manual functional check.

Full command output: `evidence/functional-run-local.txt`.

# Expected result

- Buildings include E2, E6, W1, W3, W5; E2 floor 4 lists DR223 and DR224 (`location_id` `E2-04-20-DR223`, `E2-04-21-DR224`).
- `/api/occupancy/current` without `at` returns **422**; with demo `at` returns one row per seeded location (**64** in the current catalogue: E2, E4 Foodgle, E6, W1, W3, W5). The 30 September run below recorded **47** rows on that day’s seed.
- DR223 at `2026-09-30T15:00:00+08:00`: 30 Sep run was 3/8 moderate generated. **Current seed (10 Oct API):** 4/8, moderate, generated, `booked=1`. Write what the UI shows.
- W3 floors 3, 4, 6, 7, 8; W5 floors 3, 5, 7, 8.
- Timeline for DR223 on 30 Sep: non-empty hourly list, every `source` is `generated`; prediction is a list (may be older than 30 Sep).
- `/api/events/today` returns **200** and a JSON list (may be empty).
- Frontend automated tests: all pass with both servers up.
- UI copy states generated / not live sensors (negation acceptable).

# Actual result

**Servers (Step 1):** API **200** on `/buildings`, frontend **200** on `/` (after using `C:\Windows\System32\curl.exe`; `curl.exe` was not on PATH in this shell).


| Sub-check                | Result                                                                                                                                                                                                                    |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2a proxy API             | **Pass** — five buildings; E2 L4 has DR223/DR224; no-`at` **422**; `cur.json` saved                                                                                                                                       |
| 2b DR223 + floors        | **Pass (30 Sep seed)** — **47** rows that day; DR223 3/8 moderate generated at demo time; W3 `[3,4,6,7,8]`, W5 `[3,5,7,8]`. **Current seed (10 Oct rebuild): 64 locations.** A new proxy run has not replaced this table. |
| 2c timeline / prediction | **Pass** (retry) — first timeline curl failed (PowerShell stripped query params → 422); retried with quoted URL: **13** hourly rows, all `source` `generated`; prediction **2** rows (29 Sep v0)                          |
| 2d events                | **Pass** — HTTP **200**, **3** events returned for "today"                                                                                                                                                                |
| 2e `node --test`         | **Pass** — **4** tests, **4** passed, **0** failed                                                                                                                                                                        |
| 2f static strings        | **Pass** — index shows "MODEL-GENERATED DATA" and "Not live sensors"; `app.js` includes "generated occupancy" and chart heading "generated"                                                                               |
| 2g browser               | **Pass**, 10 October 2026, Ryan — all 10 click-through steps. DR223 at 15:00 SGT 30 Sep: **4/8**, 50%, booked this hour and occupied, generated. Login, book, cancel, then API-down error + Try again. |


No teammate bug filed: timeline failure was operator/shell quoting, not API behaviour.

# Date

- Workflow run: 30 September 2026, Ryan (47-location seed).
- Catalogue note: 10 October 2026, Ryan — `data/sample/locations.csv` and rebuilt `data/occuscope.db` have **64** locations. Login button label is **Login** (`d67cb1c`). Sign-off lines below still wait on Zi Qian and Zul.
- Browser click-through: 10 October 2026, Ryan (local http://127.0.0.1:5173).

# Artefact path

- `evidence/functional-run-local.txt`
- `src/frontend/tests/*.test.mjs`
- `evidence/test-frontend-map.md` (Zi Qian — detailed map and browser evidence)
- `src/frontend/README.md` (manual functional check)
- `src/api-contract.md`

# Ryan click-through (10 October 2026)

Start two terminals from the repo root (`.venv` active):

```powershell
python -m uvicorn src.backend.api:app --host 127.0.0.1 --port 8000
node src/frontend/server.mjs
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Demo: `2500001@sit.singaporetech.edu.sg` / `OccuscopeDemo26!`

Tick after you do it. In “What I saw”, copy the words on screen (especially DR223 people/capacity). Same steps, more click-by-click, in `src/frontend/README.md`.


| #   | What to do                                                                                                                                                                        | Tick | What I saw                                                                                                                                                 |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Top-right says **Login**. Page says occupancy is generated / not live sensors.                                               | ✓    | as expected                                                                                                                                                |
| 2   | Turn **off** Follow Singapore time. Date **30 Sep 2026**, hour **15:00**. Wait until the room list fills.                                                                         | ✓    | as expected                                                                                                                                                |
| 3   | Click **E2** → **Level 4** → **DR223**. Write people/capacity, Quiet/Moderate/Crowded, generated, Booked or Available.                                                            | ✓    | 4/8 people, 50% occupancy, Reading: 2026-09-30, 15:00 SGT,Booked this hour · currently occupied., Highlighted in our campus model: **DR223**, E2, Level 4. |
| 4   | On that same DR223 panel: history chart has bars. “Next two hours” can be empty.                                                                                                  | ✓    | as expected                                                                                                                                                |
| 5   | Switch to **Crowd positions**. Find the DR223 dot. Same crowd band as the panel. No way to type a colour.                                                                         | ✓    | as expected                                                                                                                                                |
| 6   | Switch to **3D campus**. Click **W3** → **Level 8**. See DR15, DR16, DR17. Drag to rotate.                                                                                        | ✓    | as expected                                                                                                                                                |
| 7   | Filter to **food courts**. See Foodgle and Wholesome. **No Book button** on those two.                                                                                            | ✓    | as expected                                                                                                                                                |
| 8   | Click **Login**. Email `2500001@sit.singaporetech.edu.sg` (grey text is a hint, type it anyway). Password `OccuscopeDemo26!`. You see a name/email, not the password on the page. | ✓    | as expected                                                                                                                                                |
| 9   | Open a discussion room → **Book** → tomorrow + one free 30-min block → confirm. **My account** lists it. **Cancel booking**.                                                      | ✓    | as expected                                                                                                                                                |
| 10  | Ctrl+C the API terminal. Refresh the site. Error + **Try again**, not leftover room numbers looking live.                                                                         | ✓    | as expected                                                                                                                                                |


Chat is optional (503 if no Groq key).

# Sign-off (owners)


| Owner            | Confirmation |
| ---------------- | ------------ |
| Zi Qian (map UI) | 10 Oct 2026, team chat: Crowd positions + 3D checked; DR223 band matches the panel; 64 locations; generated copy visible. |
| Zul (API)        | 10 Oct 2026, team chat: occupancy `?at=` + DR223 4/8 moderate generated; login and book/cancel OK locally; `crowd_level` not client-set. |


# Limitations

Occupancy is **generated**, not live SIT sensors. 30 Sep automated proxy steps remain in the table above. 10 Oct local browser checklist completed by Ryan. Deployed stack (same evening, Ryan): map, login, book and cancel worked on API Gateway after the Lambda zip upload; live URL not recorded. Zi Qian and Zul confirmed in team chat (10 Oct 2026); lines above.