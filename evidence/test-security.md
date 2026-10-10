# Named threat

Client cannot forge `crowd_level`. Quiet / Moderate / Crowded are derived server-side from `occupancy_count / capacity` (CASE in `src/backend/api.py`, also `v_occupancy_current`). The API must not persist a client-supplied band.

Supporting checks (not this named threat): injection on IDs; occupancy GET has no write verbs; login/booking POSTs need a session and `X-Occuscope-Request: 1`; secrets/gitignore; occupancy not claimed as live SIT sensors.

# Objective

Demonstrate that `crowd_level` cannot be written by the client and that GET occupancy bands match count/capacity. Supporting: unknown IDs fail closed; mutating routes are not anonymous occupancy writes; gitignore keeps secrets and the brief PDF out of git; docs do not claim live Punggol sensors.

# Setup

**Primary threat:** expected results locked against `src/api-contract.md` and `src/db/schema.sql`. Local API: `src/backend/api.py` plus `src/backend/bookings.py`. Build: `python -m venv .venv`, install `src/backend/requirements.txt` and `tests/requirements-test.txt`, then `python src/db/init_app_db.py` (needs `analytics/requirements.txt` for demo bookings).

Copy `.env.example` to `.env` (never commit `.env`). Use `data/occuscope.db` (gitignored). Do not import `data/raw/` into the database.

# Command / steps

Named threat (local API; deployed URL not used in this run):

1. `GET /occupancy/current?at=2026-09-30T15:00:00%2B08:00` — each row has `occupancy_ratio` and `crowd_level`; band matches quiet ≤ 0.30 / moderate ≤ 0.70 / else crowded from count / capacity.
2. `GET /occupancy/current` without `at` returns 422.
3. Occupancy and location collection paths still reject POST/PUT/PATCH/DELETE with 404 or 405. OpenAPI **may** list POST on `/auth/*`, `/bookings*`, `/chat`.

Automated (local SQLite + FastAPI TestClient):

```
python tests/test_api_security.py -v
```

Supporting:

4. `GET /occupancy/{location_id}/prediction?at=` for a seeded id (for example `E2-03-07-DR209` at `2026-09-30T15:00:00+08:00`).
5. Unknown `location_id` on occupancy and prediction paths — 4xx, not 500.
6. `python tests/test_gitignore_secrets.py` from the repository root.
7. Confirm responses and docs do not claim live Punggol sensors (`source` is `generated` after seed).
8. `python tests/test_no_secrets_in_tracked_files.py` from the repository root.
9. `python tests/test_frontend_server_security.py` from the repository root (Node required).
10. POST `/bookings` without a session → 401 or 403; POST `/auth/login` without `X-Occuscope-Request: 1` → 403; bad password → 401; successful Set-Cookie is HttpOnly + SameSite=Strict; 11th login attempt in a minute → 429.

# Expected result

- Named threat: heatmap payload exposes derived `crowd_level` only; extra `crowd_level` / `colour` query params do not change JSON.
- Unknown identifiers return 4xx, not an unhandled 500.
- Occupancy has no write verbs; booking/login writes are not public occupancy updates.
- `tests/test_gitignore_secrets.py` exits 0.
- Occupancy is labelled generated / not live SIT accuracy (`evidence/test-data-ai.md`).

# Date

- Secrets supporting check: 26 September 2026 (Ryan).
- Named threat (API, GET-only snapshot): 30 September 2026 (Ryan, local API).
- Named threat + auth/booking supporting tests: 10 October 2026 (Ryan, local API).

# Actual result

- Named threat (local only, not deployed AWS): `python tests/test_api_security.py -v` — **14 tests run, 14 passed**, 10 October 2026, Ryan (`evidence/security-api-local.txt`). `crowd_level` / `colour` query params do not change the JSON versus the baseline `at` request. Injection-style location ids returned **404** (not 500). POST/PUT/PATCH/DELETE on `/occupancy/current` and `/locations` returned **404** or **405**. OpenAPI allows POST only on auth, bookings and chat. POST `/bookings` without a session: **403** (no header) / **401** (header, no cookie). POST `/auth/login` without the custom header: **403**. Bad password: **401**. Successful login Set-Cookie: **HttpOnly**, **SameSite=Strict**. 11th login attempt in a minute: **429**. Occupancy SQLite URI `?mode=ro` still rejects INSERT.
- Offline supporting checks: `test_gitignore_secrets.py` (2), `test_data_store_hygiene.py` (4), `test_crowd_and_seed.py` (15) — **21 passed**, 10 October 2026.
- Secret-pattern scan: `python tests/test_no_secrets_in_tracked_files.py` — **8 tests run, 8 passed**, 10 October 2026.
- Frontend dev server checks: `python tests/test_frontend_server_security.py` — **6 tests run, 6 passed**, 10 October 2026. Static review: **8** open findings (**7** Low, **1** Medium); SR-6 closed (placeholder `<data-bucket>`).
- Booking/chat unit tests (Zul): `python -m unittest src.backend.test_bookings src.backend.test_chat` — **24 passed**, 10 October 2026.

**Not yet covered:** deployed API Gateway smoke (422/401/403/headers), IAM export, Groq key rotation.

# Artefact path

- `src/api-contract.md`
- `src/db/schema.sql` (`v_occupancy_current`, `app_user`)
- `src/backend/api.py`, `src/backend/bookings.py`
- `tests/test_api_security.py`
- `evidence/security-api-local.txt`
- `tests/test_gitignore_secrets.py`
- `tests/test_no_secrets_in_tracked_files.py`
- `tests/test_frontend_server_security.py`
- `evidence/security-review.md`
- `.gitignore`, `.env.example`
- `evidence/threat-control-map.md`
- `evidence/test-data-ai.md`
- Redacted request/response once a deployed smoke exists (no keys, account IDs, or IPs)
