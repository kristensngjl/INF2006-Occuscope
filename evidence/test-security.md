# Named threat

Client cannot forge `crowd_level`. Quiet / Moderate / Crowded are derived only in `v_occupancy_current` (`occupancy_count / capacity`). The API must not persist a client-supplied band.

Supporting checks (not this named threat): injection on IDs, secrets/gitignore, occupancy not claimed as live SIT sensors.

# Objective

Demonstrate that `crowd_level` cannot be written by the client and that GET occupancy bands match the view. Supporting: unknown IDs fail closed; gitignore keeps secrets and the brief PDF out of git; docs do not claim live Punggol sensors.

# Setup

**Primary threat:** expected results locked against `src/api-contract.md` and `src/db/schema.sql`. Local API exists (`src/backend/api.py`). Build steps: `python -m venv .venv`, install `src/backend/requirements.txt` and `tests/requirements-test.txt`, then `python src/db/init_app_db.py`.

**Secrets supporting check (runnable now):** from the repository root, Python 3.11+:

```
python tests/test_gitignore_secrets.py
```

Copy `.env.example` to `.env` (never commit `.env`). Use `data/occuscope.db` (gitignored). Do not import `data/raw/` into the database.

# Command / steps

Named threat (local API; replace base URL when Kristen shares API Gateway):

1. `GET /occupancy/current?at=2026-09-30T15:00:00%2B08:00` — each row has `occupancy_ratio` and `crowd_level`; band matches quiet ≤ 0.30 / moderate ≤ 0.70 / else crowded from count / capacity.
2. `GET /occupancy/current` without `at` returns 422.
3. The API defines only GET routes. POST/PUT/PATCH/DELETE return 404 or 405.

Automated (local SQLite + FastAPI TestClient):

```
python tests/test_api_security.py -v
```

Supporting:

4. `GET /occupancy/{location_id}/prediction` for a seeded id (for example `E2-03-07-DR209`).
5. Unknown `location_id` on occupancy and prediction paths — 4xx, not 500.
6. `python tests/test_gitignore_secrets.py` from the repository root.
7. Confirm responses and docs do not claim live Punggol sensors (`source` is `generated` after seed).
8. `python tests/test_no_secrets_in_tracked_files.py` from the repository root.
9. `python tests/test_frontend_server_security.py` from the repository root (Node required).

# Expected result

- Named threat: heatmap payload exposes derived `crowd_level` only; the client cannot persist a band.
- Unknown identifiers return 4xx, not an unhandled 500.
- `tests/test_gitignore_secrets.py` exits 0.
- Occupancy is labelled generated / not live SIT accuracy (`evidence/test-data-ai.md`).

# Date

- Secrets supporting check: 26 September 2026 (Ryan).
- Named threat (API): 30 September 2026 (Ryan, local API).

# Actual result

- Named threat (local only, not deployed AWS): `python tests/test_api_security.py -v` — **10 tests run, 10 passed**, 30 September 2026, Ryan (`evidence/security-api-local.txt`). `crowd_level` / `colour` query params do not change the JSON versus the baseline `at` request. Injection-style location ids returned **404** (not 500); `GET /buildings` still **200** after probes. OpenAPI exposes only **GET** operations; POST/PUT/PATCH/DELETE on `/occupancy/current` and `/locations` returned **404** or **405**. Live `curl` against uvicorn on port 8000: **422** without `at`, **200** with demo `at`, **405** on POST.
- Offline supporting checks: `test_gitignore_secrets.py` (2), `test_data_store_hygiene.py` (4), `test_crowd_and_seed.py` (4) — **10 passed**, 30 September 2026 (`evidence/security-offline-tests.txt`).
- Secrets supporting check (earlier run): `python tests/test_gitignore_secrets.py` — all tests passed, 26 September 2026, Ryan.
- Secret-pattern scan (tracked + uncommitted files): `python tests/test_no_secrets_in_tracked_files.py` — **8 tests run, 8 passed**, 30 September 2026, Ryan (`evidence/secret-scan-local.txt`).
- Frontend dev server checks: `python tests/test_frontend_server_security.py` — **6 tests run, 6 passed**, 30 September 2026, Ryan (`evidence/frontend-server-security-local.txt`). Static review: **9** findings (**8** Low, **1** Medium) in `evidence/security-review.md`.

**Not yet covered:** deployed API Gateway URL, IAM, network security groups, CloudWatch (Kristen).

# Artefact path

- `src/api-contract.md`
- `src/db/schema.sql` (`v_occupancy_current`, `app_user`)
- `tests/test_gitignore_secrets.py`
- `tests/test_api_security.py`
- `src/backend/api.py`
- `evidence/security-api-local.txt`
- `evidence/security-offline-tests.txt`
- `tests/test_no_secrets_in_tracked_files.py`
- `evidence/secret-scan-local.txt`
- `tests/test_frontend_server_security.py`
- `evidence/security-review.md`
- `evidence/frontend-server-security-local.txt`
- `.gitignore`, `.env.example`
- `evidence/threat-control-map.md`
- `evidence/test-data-ai.md`
- Redacted request/response once the deployed API exists (no keys, account IDs, or IPs)
