# Threat–control map

Intended controls for Occuscope. Rows marked **done** can be shown from the repo today. Rows marked **pending** wait on a redacted AWS export. Ryan fills evidence as those land.

| Threat | Control | Where it lives | Status | Evidence |
|---|---|---|---|---|
| Secrets in git | `.env` gitignored; `.env.example` placeholders only | repo root | done | `.gitignore`, `.env.example`, `tests/test_gitignore_secrets.py` |
| NUS raw dumps / brief / local cloud notes in git | `data/raw/*`, `CLOUDPROJ.md`, brief PDFs gitignored | repo root | done | `.gitignore`; Lideon reminder not to commit these |
| Trained weights committed by accident | `analytics/models/*` and `*.joblib` gitignored | `analytics/models/` | done | `.gitignore` |
| Unauthenticated access (auth decision) | Unauthenticated **GET** of the crowd map, occupancy, predictions and today’s events is appropriate (public generated occupancy, not personal data). Login, booking and cancel are **POST** and require a demo-student session (`app_user`) plus header `X-Occuscope-Request: 1`. Chat POST is unauthenticated but rate-limited and cannot book. | `src/backend/api.py`, `bookings.py`, `chat.py` | done locally | `tests/test_api_security.py`; `src.backend.test_bookings` |
| Database reachable from the internet | App DB is a private S3 object (`crowdmap-lake-g07`, Block Public Access). The only door in is API Gateway. Local SQLite is a gitignored file. RDS is designed-not-deployed (diagram dashed box). | S3 + API Gateway | done (design + deploy-log); IAM JSON still pending | `evidence/deploy-log.md`; `evidence/architecture.png` |
| Client supplies `crowd_level` (named security-test threat) | Crowd band is derived only in `v_occupancy_current` (quiet ≤ 0.30, moderate ≤ 0.70, else crowded). API must not accept a client band. | `src/db/schema.sql`, backend | done locally (server-side CASE in api.py) | `tests/test_api_security.py` |
| Injection via API input | Validate `location_id`, `building_id`, floor, timestamps, query params on contract paths. Unknown IDs → 4xx, not 500. | backend | done locally (parameterised SQL, 404/422) | `tests/test_api_security.py` |
| Occupancy DB written by map GET | Occupancy queries open SQLite `?mode=ro`. Booking writes use a separate read-write connection on the writer Lambda / local API. | `src/backend/api.py`, `bookings.py` | done locally | `tests/test_api_security.py` (`test_db_is_read_only`, `test_occupancy_has_no_write_verbs`) |
| Deployed Lambda reads DB from S3 | Private bucket; readers GetObject; only `crowdmap-bookings` PutObject after successful POST; DB copied to /tmp | AWS (redacted) | pending (IAM export) | `src/backend/lambda_handler.py`; `evidence/deploy-log.md` |
| NUS training files loaded into the app DB | `init_app_db.py` seeds only `data/sample/`. Never import `data/raw/`. | `src/db/` | done locally | `src/README.md`; data/AI test |
| Treating synthetic SIT counts as live people | Docs and UI must say occupancy is **generated**, not a Punggol sensor. Do not claim campus accuracy. | README, report, UI copy | done (docs and UI copy) | `evidence/test-data-ai.md`, README limitations; `evidence/functional-run-local.txt` (2f: served page shows "Not live sensors" and "MODEL-GENERATED DATA") |
| Over-privileged cloud IAM | Learner Lab **cannot** custom-role: all three Lambdas use `LabRole`. Intended: web-bucket read, lake-bucket read/write only `db/occuscope.db`, own logs. | AWS LabRole | limitation (honest) | `evidence/deploy-log.md` §3 |
| Secrets in CloudWatch screenshots | Redact account IDs, IPs, keys before pasting | `evidence/monitoring.md` | done for 8 Oct artefacts | `evidence/alarm-notifications.txt`, screenshots |
| Unauthenticated booking POST | Session cookie + `X-Occuscope-Request: 1`; login throttle 10/min; HttpOnly SameSite=Strict cookies | `src/backend/bookings.py` | done locally | `tests/test_api_security.py` |
| Chatbot prompt / quota abuse | Message max 800 chars; 5 calls/min in-process; API Gateway 1 req/s on POST /chat; cannot book; treats user text as untrusted | `src/backend/chat.py` | done in code; no named-threat test | `chat.py`; `evidence/throttling-config.txt` |
| Wrong Lambda runtime vs v0 joblib | `src/infra/build_lambda_package.sh` installs CPython **3.11** manylinux wheels (`--python-version 3.11`, fastapi + mangum), so the Lambda runtime must be 3.11 or the compiled wheels will not import. The package copies only `api.py`, `lambda_handler.py` and the DB; **no joblib model is packaged** (predictions are precomputed rows in `occupancy_prediction`). Kristen to confirm the deployed runtime and that no model file is loaded at request time. The v0 joblib (Python 3.11.9, sklearn 1.9.1, joblib 1.6.0) matters only if inference moves into Lambda later. | Kristen deploy | pending (Kristen confirms) | `src/infra/build_lambda_package.sh`, `src/backend/lambda_handler.py`, Lambda configuration export (pending Kristen) |
| Deployed resource names exposed in the repo | Docstring uses `<data-bucket>`; never commit the deployed URL | `src/backend/lambda_handler.py` | done (SR-6 closed) | `tests/test_no_secrets_in_tracked_files.py` |
| OpenAPI docs exposed on API app | Disable `/docs`, `/redoc`, `/openapi.json` in production | `src/backend/api.py` | finding (open, SR-1) | `evidence/security-review.md` |
| Verbose DB-unavailable error | Generic 503 message without repo paths | `src/backend/api.py` | finding (open, SR-2) | `evidence/security-review.md` |
| Missing browser security headers on static host | CSP, frameguard, referrer, permissions on production | production hosting | finding (open, SR-3) | `evidence/security-review.md` |
| Floor label HTML interpolation | Escape or use DOM APIs for floor chips | `src/frontend/app.js`, `model.js` | finding (open, SR-4, SR-5) | `evidence/security-review.md` |
| Example bucket name in Lambda docstring | Placeholder `<data-bucket>` in docs | `src/backend/lambda_handler.py` | closed (was SR-6) | `evidence/security-review.md` |
| Unpinned Lambda dependency install | Pin versions in `build_lambda_package.sh` | `src/infra/build_lambda_package.sh` | finding (open, SR-7) | `evidence/security-review.md` |
| Third-party font request leaks visitor data | Self-host fonts or use a system font stack; keeps a future CSP tight | `src/frontend/styles.css` | finding (open, SR-9) | `evidence/security-review.md` |
| Compromised S3 DB object | IAM deny writes; integrity of `occuscope.db` object | S3 + Lambda | finding (open, SR-8) | `evidence/security-review.md` |

Ryan owns filling **pending** rows as controls are implemented.
