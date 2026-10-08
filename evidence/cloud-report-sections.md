# Report drafts: cloud sections (Kristen)

Drafts for report sections 3, 6 (scalability and monitoring part) and 7. Copy into `report.pdf` and shorten as needed.
Items marked **TODO** must be filled or checked before submission. Prices are AWS `us-east-1` list prices, before free tier, checked October 2026.

---

## 3. Cloud service/deployment choices and trade-offs

**Deployment model.** Public cloud, single region (`us-east-1`), in an AWS Academy Learner Lab account. The service has no private or on-premises part, and its users (SIT students) are on the public internet.

**Service model.** Serverless (FaaS, with managed PaaS services around it):

| Layer | Service | Managed by AWS | Managed by the team |
|---|---|---|---|
| Entry point | API Gateway HTTP API `crowdmap-http` | TLS, servers, availability, throttling engine | Routes, integrations, throttle limits |
| Compute | Lambda `crowdmap-web`, `crowdmap-api`, `crowdmap-bookings` (Python 3.11) | Servers, OS, runtime patching, scaling out, restarts | Application code, memory/timeout, concurrency limits, environment variables |
| Storage | S3 `crowdmap-web-<group>`, `crowdmap-lake-<group>` | Durability, replication, encryption at rest | Bucket privacy (Block Public Access), versioning, object layout |
| Operations | CloudWatch Logs/alarms, SNS, AWS Budgets | Collection, storage, delivery | Alarm thresholds, dashboard, who is notified |
| Chatbot | Groq API (external SaaS) | Model hosting | API key handling, rate limit (`POST /api/chat` 1 req/s) |

The IaaS/PaaS boundary therefore sits **below our code**: we never manage a VM, an OS or a load balancer. We are responsible for code, configuration, data and access, and AWS is responsible for everything underneath. This matches the workload, which is mostly short read requests that rise and fall with class timetables and drop to zero at night.

**Alternatives considered**

| Alternative | Why not selected |
|---|---|
| **EC2 + Application Load Balancer + Auto Scaling (IaaS)** | Billed per hour even when idle: two small instances plus an ALB cost about USD 30/month before any traffic, which is too much for a USD 50 lab credit. The team would also own OS patching and the scaling configuration. |
| **Containers (ECS on Fargate) behind an ALB** | Removes OS patching, but tasks and the ALB are still billed per hour, and it adds image build and registry steps the team does not need for a small Python API. |
| **Amazon RDS for the database** | The right choice for concurrent writes (see section 6), but a `db.t3.micro` running 24/7 costs about USD 12–15/month, and Lambda would have to run inside the VPC to reach it. Kept as the documented production path; the `crowdmap` VPC (2 AZs, private subnets, S3 gateway endpoint, no NAT) is provisioned for it. |
| **CloudFront + private S3 for the frontend** | Preferred design (CDN, edge cache, WAF). Learner Lab denied `cloudfront:CreateOriginAccessControl` and `CreateDistribution`. Replaced by the `crowdmap-web` Lambda, which keeps the bucket private and the site on HTTPS. |
| **S3 static website hosting** | Requires a public bucket. Rejected for security. |

**Key constraints and assumptions**

- Learner Lab: fixed IAM role `LabRole` (no custom least-privilege roles), CloudFront blocked, sessions end after a few hours (`voc-cancel-cred` revokes credentials), USD 50 credit. Each constraint and how it was handled is listed in `evidence/deploy-log.md` §3.
- Data is synthetic: generated occupancy, 1,998 fictional demo accounts. No personal data.
- Expected workload (assumption): up to about 2,000 daily users, each making about 40 API requests per visit (map loads, time changes, booking checks), so about 80,000 requests/day, with short peaks between classes.

---

## 6. Testing, scalability/resilience and monitoring results (cloud part)

**Mechanisms implemented**

1. **Horizontal scaling (Lambda).** Each concurrent request gets its own Lambda instance; no scaling policy needs to be configured. In the spike test `crowdmap-api` reached about **66 concurrent instances**.
2. **Throttling (API Gateway).** Stage limit 50 req/s, burst 100. Tighter limits on `POST /api/chat` (1 req/s, protects the Groq quota) and `ANY /api/auth/{proxy+}` (2 req/s, slows password guessing). Excess traffic gets HTTP 429 before it reaches Lambda. Config: `evidence/throttling-config.txt`.
3. **Single writer with S3 persistence.** SQLite cannot be shared between Lambda instances, so all writes (login sessions, bookings) go to `crowdmap-bookings` with reserved concurrency 1. It uploads the database to S3 after each successful write. The reader Lambdas check the S3 ETag every 60 s and reload when it changes. Code: `src/backend/lambda_handler.py`.
4. **Recovery.** S3 versioning on `crowdmap-lake-<group>` keeps earlier database versions. `/api/health` is used by the deployment check.

**Test 4 (scalability and resilience).** Full record in `evidence/test-resilience.md`. Run from AWS CloudShell with `tests/load_test.py` on 8 Oct 2026.

| Phase | Result |
|---|---|
| A steady load, 10 clients, 60 s | All 200, 0 errors. p50 **1,582 ms** at 128 MB; after raising memory to 1024 MB, p50 **206 ms**, throughput 5.9 → **48.7 req/s** (`steady-1024mb.txt`) |
| B spike, 60 clients, above 50 req/s | 1,122 × 200, **3,150 × 429**, **0 × 5xx**: throttling shed 74% of the spike and the service stayed up |
| C auth burst, 30 requests | 401 / 429 as expected, but **7 × 503**: requests overlapping the busy single writer |
| D booking survives a forced cold start | First attempts failed (sequencing, then 503); after adding retries: **PASS**, booking read back from a fresh instance in 3.9 s (`persistence-run.txt`) |

**Interpretation.** Read paths scale out without errors, and throttling protects the backend. The weak point is the single writer: it is correct (no lost bookings) but serialises writes, so overlapping requests get 503 and must be retried. A shared relational database (RDS) is the improvement that would remove this limit. The deployment check also found that all Lambdas had reverted to the 128 MB default. Raising memory to 1024 MB gave 8× more throughput, which shows the latency was CPU-bound and not a scaling limit. **TODO:** after raising `crowdmap-bookings` to 1024 MB, re-run phase D and add the result.

**Monitoring.** 7 CloudWatch alarms send email through SNS topic `crowdmap-alerts`:

- Lambda `Errors` ≥ 1 on each of the 3 functions;
- `crowdmap-bookings` `Throttles` ≥ 1;
- API 5xx ≥ 5, API 4xx ≥ 50, p95 latency ≥ 3 s;

all over 5 minutes. There is also a `crowdmap` dashboard. Config: `evidence/alarms-config.txt`. During the test, `crowdmap-http-4xx`, `crowdmap-http-5xx` and `crowdmap-bookings-throttled` fired and emails arrived within about 5 minutes. The alarms returned to OK on their own (`evidence/alarm-notifications.txt`, screenshots in `evidence/screenshots/`). The throttle alarm count (7) matched the 7 × 503 in phase C, so the alarm led directly to the diagnosis.

---

## 7. Cost, sustainability and operational considerations

**Cost controls in place**

- Pay-per-request services only. Nothing is billed per hour while idle: no EC2, RDS, ALB or NAT gateway; the deployment check confirms 0 of each (`evidence/aws-deployment-check.txt`).
- The VPC uses a free S3 gateway endpoint instead of a NAT gateway (about USD 32/month).
- Throttling caps the request rate, so a traffic spike or abuse cannot run up unlimited cost.
- AWS Budget `crowdmap-monthly` emails the team on spend.
- The load test is short (about 2 minutes) and excludes the chatbot.
- Actual Learner Lab spend for the whole project: **USD 0.50 of 50** (1%), as of 8 Oct 2026, including all load tests.

**Estimated monthly cost at the expected workload** (about 80,000 requests/day, about 2.4 M/month, before free tier):

| Item | Basis | USD/month |
|---|---|---|
| API Gateway HTTP API | 2.4 M requests × USD 1.00 per million | 2.40 |
| Lambda requests | 2.4 M × USD 0.20 per million | 0.48 |
| Lambda compute | 2.4 M × about 0.21 s × 1 GB = about 504,000 GB-s × USD 0.0000166667 | 8.40 |
| S3 storage + requests | about 50 MB current data, ETag checks, writes | < 0.50 |
| CloudWatch alarms | 7 × USD 0.10 | 0.70 |
| **Total** | | **about 12.50** |

For comparison, the EC2 + ALB alternative costs about USD 30/month before any traffic.

**Cost risk found: database versions.** The lake bucket keeps every version, and each write uploads the whole database (about 23 MB). At about 500 bookings/day that adds about 11 GB/day of old versions, roughly USD 8 more each month and growing. Mitigation: an S3 lifecycle rule that deletes noncurrent versions after 1 day, so recovery still works for the last day. **TODO:** apply the rule or state it as recommended. In production, moving bookings to RDS removes this cost.

**Sustainability.** The service scales to zero, so no servers idle at night or during holidays, when campus demand is near zero. Right-sizing memory (1024 MB) made each request about 8× faster for roughly the same GB-seconds, so the speed-up did not increase compute use. The next efficiency step is a short cache for `/occupancy/current`: all users viewing the same hour would share one query instead of each running it.

**Operations**

- **Deployment** is scripted and repeatable: `src/infra/build_lambda_package.sh`, then upload; the steps are in `evidence/deploy-log.md` §5.
- **Drift detection:**
  - `src/infra/verify_deployment.sh` compares the live setup with the diagram, with output redacted;
  - `src/infra/check_versions.sh` confirms the deployed code and frontend match the repo (14/14 on 8 Oct).
- **Lesson:** the memory settings were lost on re-upload without anyone noticing until the check ran. Infrastructure-as-code (CloudFormation/SAM) would prevent this and is the main operational improvement.
- **Secrets:**
  - the Groq key is kept only as a Lambda environment variable;
  - the CLI is run with `--query` so commands do not print environment variables;
  - **TODO, if done:** after the key appeared in a CLI output on 8 Oct, it was rotated.
- **Lab limitation:** the live URL stops when the Learner Lab session ends. The brief allows this as long as dated, redacted evidence is supplied, which is how all results above were captured.
