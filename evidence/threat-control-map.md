# Threat–control map

Intended controls for Occuscope. Rows marked **done** can be shown from the repo today. Rows marked **pending** wait on Zul (API) or Kristen (AWS). Ryan fills evidence as those land.

| Threat | Control | Where it lives | Status | Evidence |
|---|---|---|---|---|
| Secrets in git | `.env` gitignored; `.env.example` placeholders only | repo root | done | `.gitignore`, `.env.example`, `tests/test_gitignore_secrets.py` |
| NUS raw dumps / brief / local cloud notes in git | `data/raw/*`, `CLOUDPROJ.md`, brief PDFs gitignored | repo root | done | `.gitignore`; Lideon reminder not to commit these |
| Trained weights committed by accident | `analytics/models/*` and `*.joblib` gitignored | `analytics/models/` | done | `.gitignore` |
| Unauthenticated access (auth decision) | **Decision:** unauthenticated **GET** of the crowd map, occupancy, predictions, and today’s events is appropriate (public campus occupancy, not personal data). Mutating routes (POST/PUT/DELETE), **if they exist**, require auth via `app_user`. If the API stays read-only, the control is “no writes”. | backend | pending (API) | this table; security test |
| Database reachable from the internet | **Intended:** RDS not publicly reachable; security group allows the DB port only from the application; no `0.0.0.0/0` on the database port. Local SQLite is file-based only. | AWS SG / RDS; later config | pending (deploy) | redacted SG/RDS export after Kristen |
| Client supplies `crowd_level` (named security-test threat) | Crowd band is derived only in `v_occupancy_current` (quiet ≤ 0.30, moderate ≤ 0.70, else crowded). API must not accept a client band. | `src/db/schema.sql`, backend | pending (API) | schema now; `evidence/test-security.md` |
| Injection via API input | Validate `location_id`, `building_id`, floor, timestamps, query params on contract paths. Unknown IDs → 4xx, not 500. | backend | pending (API) | security test |
| NUS training files loaded into the app DB | `init_app_db.py` and RDS must seed only `data/sample/`. Never import `data/raw/`. | `src/db/`, later RDS | done locally / pending RDS | `src/README.md`; data/AI test |
| Treating synthetic SIT counts as live people | Docs and UI must say occupancy is **generated**, not a Punggol sensor. Do not claim campus accuracy. | README, report, UI copy | done in docs / pending UI | `evidence/test-data-ai.md`, README limitations |
| Over-privileged cloud IAM | Least-privilege roles for compute, RDS, S3 model object, CloudWatch | AWS (redacted) | pending (deploy) | exported policy after Kristen |
| Secrets in CloudWatch screenshots | Redact account IDs, IPs, keys before pasting | `evidence/monitoring.md` | pending (deploy) | monitoring export |
| Wrong Lambda runtime vs v0 joblib | Model trained on Python 3.11.9 + sklearn 1.9.1 + joblib 1.6.0. Confirm Lambda is 3.11 before upload; 3.14 would fail unpickle. No SageMaker required; S3 `models/` is the intended store. | Kristen deploy | pending (deploy) | runtime note + resilience/security actuals |

Ryan owns filling **pending** rows as controls are implemented.
