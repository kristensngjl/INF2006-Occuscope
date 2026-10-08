# Deployment log: Occuscope on AWS

Owner: Kristen (Cloud / Scalability). Region: `us-east-1`, AWS Academy Learner Lab.
Group: G007. AWS bucket names end in `g017` (a naming suffix chosen at creation; S3 buckets cannot be renamed). Redaction: account ID, API ID and live URL are never written here.

Architecture diagram: [`architecture.png`](architecture.png) (source: `architecture.svg`).
Rebuild scripts: [`../src/infra/build_lambda_package.sh`](../src/infra/build_lambda_package.sh), [`../src/infra/verify_deployment.sh`](../src/infra/verify_deployment.sh).

## 1. What is deployed now

| Resource | Name | Key settings |
|---|---|---|
| API Gateway (HTTP API) | `crowdmap-http` | HTTPS only, stage `$default` with auto-deploy |
| Throttling | stage `$default` | All routes: 50 req/s, burst 100. `POST /api/chat`: 1 req/s, burst 5. `ANY /api/auth/{proxy+}`: 2 req/s, burst 5. Evidence: `throttling-config.txt` |
| Route `GET /`, `GET /{proxy+}` | → `crowdmap-web` | Serves the frontend |
| Route `GET /api/{proxy+}`, `POST /api/chat` | → `crowdmap-api` | Map, forecasts, events, chatbot |
| Route `ANY /api/auth/{proxy+}`, `ANY /api/bookings`, `ANY /api/bookings/{proxy+}` | → `crowdmap-bookings` | Login and room booking |
| Lambda | `crowdmap-web` | Python 3.11. Reads the 7 frontend files from the private web bucket. Adds security headers and a 5-minute browser cache. |
| Lambda | `crowdmap-api` (reader) | Python 3.11, 512 MB, 29 s. FastAPI + Mangum (`src/backend/lambda_handler.py`). Copies the DB from S3 to `/tmp` and re-checks the S3 ETag at most every 60 s. Env keys: `DB_BUCKET`, `DB_KEY`, `COOKIE_SECURE`, `GROQ_API_KEY`. |
| Lambda | `crowdmap-bookings` (writer) | Python 3.11, 1024 MB, 15 s. Same code package as `crowdmap-api`. Env keys: `DB_BUCKET`, `DB_KEY`, `DB_WRITER=1`, `COOKIE_SECURE`. Uploads the DB back to S3 after every successful write. Reserved concurrency 1 (single writer); confirm in `aws-deployment-check.txt`. |
| IAM | `LabRole` | Execution role for all 3 Lambdas. Learner Lab does not allow custom roles. |
| S3 | `crowdmap-web-g017` | Block Public Access ON, SSE-S3. Holds `index.html`, `styles.css`, `login.css`, `app.js`, `data.js`, `model.js`, `bookings.js`. |
| S3 | `crowdmap-lake-g017` | Block Public Access ON, SSE-S3, versioning ON. Holds `db/occuscope.db` (SQLite, about 24 MB), plus `raw/` and `models/` (reserved). |
| VPC | `crowdmap` | 2 AZs, 2 public + 2 private subnets, S3 gateway endpoint, no NAT gateway. Provisioned for a future RDS; not in the request path. |
| AWS Budgets | `crowdmap-monthly` | Monthly cost alert by email. |
| CloudWatch Logs | `/aws/lambda/crowdmap-*` | Created automatically for each Lambda. Used for debugging (see the 25 Sep entry below). |
| External | Groq API | Chatbot LLM on the free tier, called by `crowdmap-api` over HTTPS. The key is kept in a Lambda environment variable and never in Git. |

## 2. Timeline

| Date (2026) | Change | Result / evidence |
|---|---|---|
| 23 Sep | Created the team GitHub repo and the folder structure from the brief. | Commits `Initial commit`, `Base Folders to Get Started` |
| 24–25 Sep | Checked Learner Lab access and region (`us-east-1`). Created VPC `crowdmap` (2 AZ, no NAT, S3 gateway endpoint). | VPC resource map screenshot |
| 25 Sep | Created the S3 buckets `crowdmap-web-g017` and `crowdmap-lake-g017` (private; versioning on the lake bucket) and the budget `crowdmap-monthly`. | Budget confirmed in `aws-deployment-check.txt` |
| 25 Sep | Deployed a mock API: Lambda `crowdmap-api` + HTTP API `crowdmap-http` with sample JSON, so the frontend could start before the database existed. | `/health`, `/locations`, `/occupancy/current` returned 200 |
| 25 Sep | **CloudFront attempted, blocked.** Learner Lab denied `cloudfront:CreateOriginAccessControl` and then `cloudfront:CreateDistribution`. A public S3 website was considered and rejected because the bucket would have to be public. | Error screenshots (account ID redacted) |
| 25 Sep | Replacement: Lambda `crowdmap-web` serves the frontend from the private bucket through API Gateway. This keeps HTTPS and Block Public Access. | Direct S3 object URL → Access Denied; site → 200 |
| 25 Sep | Fault: `crowdmap-web` crashed with `KeyError: 'WEB_BUCKET'`. Diagnosed from CloudWatch Logs and fixed by adding the environment variable. | CloudWatch log screenshot |
| 29 Sep | Deployed the real backend: Zul's FastAPI app wrapped with Mangum. The SQLite DB is stored in the private S3 bucket and copied to `/tmp` on cold start. Runtime pinned to Python 3.11 to match the analytics environment. Route `GET /api/{proxy+}`. | `src/backend/lambda_handler.py`, `src/infra/build_lambda_package.sh` |
| 29 Sep | Uploaded frontend v1 (Zi Qian) to the web bucket. Routing and the static-file allowlist were fixed while getting it to load. | Site loads with all assets |
| 30 Sep–2 Oct | Redeployed after each data update (47 → 62 rooms) and the forecast change. Added `chat.py` to the package after the chatbot was merged. Architecture diagram v1. | `/api/locations` count matched the seed |
| 7 Oct | Rebuilt the DB from the 3 Oct data: 64 locations, 99,008 readings, 207 events, 1,998 fictional demo accounts, demo bookings. | Seed tests passed (`tests/test_crowd_and_seed.py`) |
| 7 Oct | **Bookings need writes, but SQLite copies on Lambda are per-instance.** Added the writer Lambda `crowdmap-bookings` (single instance) that publishes the DB back to S3 after each write. Readers refresh from S3 by ETag. Tested locally: login 200, booking 201, booking visible to the reader after refresh. | `src/backend/lambda_handler.py` |
| 7 Oct | Added routes `ANY /api/auth/{proxy+}`, `ANY /api/bookings`, `ANY /api/bookings/{proxy+}` → `crowdmap-bookings`, and `POST /api/chat` → `crowdmap-api`. Granted API Gateway invoke permission on both Lambdas. | Login test returned the demo user; signed-out `/api/auth/me` → 401 |
| 7 Oct | Throttling: default 50 req/s (burst 100) set in the console. Per-route limits for chat and auth set with the AWS CLI, because the console cannot create route settings. | `throttling-config.txt` |
| 7 Oct | Set `COOKIE_SECURE=1` (session cookie sent only over HTTPS) and `GROQ_API_KEY` (chatbot) as Lambda environment variables. | Values not recorded here |
| 7 Oct | Architecture diagram v2: 3 Lambdas, Groq, throttling, trust boundaries. | `architecture.png` |
| 7 Oct 18:33 SGT | Live check passed: `/api/health` → `"role":"reader"`, 64 locations, `/` and all 6 assets → 200, signed-out `/api/auth/me` → 401, no RDS, budget present. The AWS API sections of the check were denied because the Learner Lab session had ended; they need re-running in an active session. | `aws-deployment-check.txt` (re-run pending) |
| _pending_ | Load / resilience test: steady load, spike above throttle, auth throttle, booking survives a forced cold start. | `tests/load_test.py` → `resilience-run.txt`, `test-resilience.md` |

## 3. Learner Lab constraints met (and how they were handled)

| Constraint | Effect | Handling |
|---|---|---|
| `cloudfront:CreateOriginAccessControl` and `CreateDistribution` denied | No CDN, edge cache or WAF | Frontend served by Lambda from a private bucket; throttling at API Gateway; WAF documented as production work |
| Fixed IAM role `LabRole`; custom roles not allowed | Least privilege cannot be enforced | Intended policy documented: read the web bucket, read/write only `db/occuscope.db`, write own CloudWatch logs |
| Sessions expire after a few hours; credentials revoked (`voc-cancel-cred`) | AWS API calls and cold-starting Lambdas fail when the lab is stopped | Evidence captured as dated text files during active sessions; the brief does not require a live URL |
| Console cannot create per-route throttling | | AWS CLI in CloudShell (`throttling-config.txt`) |

## 4. Cost controls

- Serverless only. Nothing is billed per hour while idle: no EC2, RDS or NAT gateway.
- VPC uses an S3 gateway endpoint (free) instead of a NAT gateway (about USD 1/day).
- API Gateway throttling caps request volume. The chatbot has its own 1 req/s limit to protect the Groq free tier.
- AWS Budget `crowdmap-monthly` sends an email alert.
- The load test excludes the chatbot route and runs for about 2 minutes.
- Lab credit used: **USD ___ of 50** _(fill in from the Learner Lab page)_.

## 5. How to redeploy

1. `bash src/infra/build_lambda_package.sh` (Python 3.11, with fastapi installed). This produces `deploy/crowdmap-api.zip` and `deploy/occuscope.db` (gitignored).
2. Upload `deploy/occuscope.db` to `s3://crowdmap-lake-g017/db/occuscope.db`.
3. Upload `deploy/crowdmap-api.zip` to **both** `crowdmap-api` and `crowdmap-bookings`. Handler: `lambda_handler.handler`.
4. Upload the 7 files in `src/frontend/` (not `server.mjs` or the tests) to `crowdmap-web-g017`.
5. Verify with `bash src/infra/verify_deployment.sh <api-id>` in CloudShell and save the redacted output to `evidence/aws-deployment-check.txt`.
