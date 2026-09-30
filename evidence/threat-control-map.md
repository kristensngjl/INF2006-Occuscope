# Threat–control map

Intended controls for Occuscope. Rows marked **done** can be shown from the repo today. Rows marked **pending** wait on Zul (API) or Kristen (AWS). Ryan fills evidence as those land.

| Threat | Control | Where it lives | Status | Evidence |
|---|---|---|---|---|
| Secrets in git | `.env` gitignored; `.env.example` placeholders only | repo root | done | `.gitignore`, `.env.example`, `tests/test_gitignore_secrets.py` |
| NUS raw dumps / brief / local cloud notes in git | `data/raw/*`, `CLOUDPROJ.md`, brief PDFs gitignored | repo root | done | `.gitignore`; Lideon reminder not to commit these |
| Trained weights committed by accident | `analytics/models/*` and `*.joblib` gitignored | `analytics/models/` | done | `.gitignore` |
| Unauthenticated access (auth decision) | **Decision:** unauthenticated **GET** of the crowd map, occupancy, predictions, and today’s events is appropriate (public campus occupancy, not personal data). Mutating routes (POST/PUT/DELETE), **if they exist**, require auth via `app_user`. If the API stays read-only, the control is “no writes”. | backend | done (local API is GET-only) | this table; `tests/test_api_security.py`; if writes are added later, auth via `app_user` |
| Database reachable from the internet | **Intended:** RDS not publicly reachable; security group allows the DB port only from the application; no `0.0.0.0/0` on the database port. Local SQLite is file-based only. | AWS SG / RDS; later config | pending (deploy) | redacted SG/RDS export after Kristen |
| Client supplies `crowd_level` (named security-test threat) | Crowd band is derived only in `v_occupancy_current` (quiet ≤ 0.30, moderate ≤ 0.70, else crowded). API must not accept a client band. | `src/db/schema.sql`, backend | done locally (server-side CASE in api.py) | `tests/test_api_security.py` |
| Injection via API input | Validate `location_id`, `building_id`, floor, timestamps, query params on contract paths. Unknown IDs → 4xx, not 500. | backend | done locally (parameterised SQL, 404/422) | `tests/test_api_security.py` |
| Database written to by the API | API opens SQLite with `?mode=ro`; no write routes | `src/backend/api.py` | done locally | `tests/test_api_security.py` (`test_db_is_read_only`) |
| Deployed Lambda reads DB from S3 | Private bucket; Lambda role read-only on that one object; DB copied to /tmp | AWS (redacted) | pending (Kristen export) | IAM policy export |
| NUS training files loaded into the app DB | `init_app_db.py` and RDS must seed only `data/sample/`. Never import `data/raw/`. | `src/db/`, later RDS | done locally / pending RDS | `src/README.md`; data/AI test |
| Treating synthetic SIT counts as live people | Docs and UI must say occupancy is **generated**, not a Punggol sensor. Do not claim campus accuracy. | README, report, UI copy | done (docs and UI copy) | `evidence/test-data-ai.md`, README limitations; `evidence/functional-run-local.txt` (2f: served page shows "Not live sensors" and "MODEL-GENERATED DATA") |
| Over-privileged cloud IAM | Least-privilege roles for compute, RDS, S3 model object, CloudWatch | AWS (redacted) | pending (deploy) | exported policy after Kristen |
| Secrets in CloudWatch screenshots | Redact account IDs, IPs, keys before pasting | `evidence/monitoring.md` | pending (deploy) | monitoring export |
| Wrong Lambda runtime vs v0 joblib | `src/infra/build_lambda_package.sh` installs CPython **3.11** manylinux wheels (`--python-version 3.11`, fastapi + mangum), so the Lambda runtime must be 3.11 or the compiled wheels will not import. The package copies only `api.py`, `lambda_handler.py` and the DB; **no joblib model is packaged** (predictions are precomputed rows in `occupancy_prediction`). Kristen to confirm the deployed runtime and that no model file is loaded at request time. The v0 joblib (Python 3.11.9, sklearn 1.9.1, joblib 1.6.0) matters only if inference moves into Lambda later. | Kristen deploy | pending (Kristen confirms) | `src/infra/build_lambda_package.sh`, `src/backend/lambda_handler.py`, Lambda configuration export (pending Kristen) |
| Deployed resource names exposed in the repo | Example bucket name in the `lambda_handler.py` docstring; replace with a placeholder like `<data-bucket>` and never commit the deployed URL | `src/backend/lambda_handler.py` | pending (Kristen) | `tests/test_no_secrets_in_tracked_files.py` (deployed URL pattern) |
| OpenAPI docs exposed on API app | Disable `/docs`, `/redoc`, `/openapi.json` in production | `src/backend/api.py` | finding (open, SR-1) | `evidence/security-review.md` |
| Verbose DB-unavailable error | Generic 503 message without repo paths | `src/backend/api.py` | finding (open, SR-2) | `evidence/security-review.md` |
| Missing browser security headers on static host | CSP, frameguard, referrer, permissions on production | production hosting | finding (open, SR-3) | `evidence/security-review.md` |
| Floor label HTML interpolation | Escape or use DOM APIs for floor chips | `src/frontend/app.js`, `model.js` | finding (open, SR-4, SR-5) | `evidence/security-review.md` |
| Example bucket name in Lambda docstring | Placeholder bucket name in docs | `src/backend/lambda_handler.py` | finding (open, SR-6) | `evidence/security-review.md` |
| Unpinned Lambda dependency install | Pin versions in `build_lambda_package.sh` | `src/infra/build_lambda_package.sh` | finding (open, SR-7) | `evidence/security-review.md` |
| Third-party font request leaks visitor data | Self-host fonts or use a system font stack; keeps a future CSP tight | `src/frontend/styles.css` | finding (open, SR-9) | `evidence/security-review.md` |
| Compromised S3 DB object | IAM deny writes; integrity of `occuscope.db` object | S3 + Lambda | finding (open, SR-8) | `evidence/security-review.md` |

Ryan owns filling **pending** rows as controls are implemented.
