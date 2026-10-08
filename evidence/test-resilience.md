# Test 4: Scalability and resilience (deployed AWS stack)

Owner: Kristen (Cloud / Scalability). Date: 8 October 2026, 18:20 SGT. Region: `us-east-1`.

## Objective

Show that the deployed service (API Gateway `crowdmap-http` → Lambda → S3) handles demand and protects itself:

1. Lambda scales out under steady and spiky load with **no server errors on the map routes**.
2. API Gateway **throttling** (stage 50 req/s, burst 100; `/api/auth/*` 2 req/s, burst 5) sheds excess traffic with HTTP 429 instead of overloading the backend.
3. **Monitoring detects the event**: CloudWatch alarms fire and email the team, then return to OK without manual action.
4. **Recovery:** a booking written by the single-writer Lambda survives a forced cold start (data persisted in S3).

## Setup

- Deployed stack as in `evidence/architecture.png` and `evidence/deploy-log.md`. Versions confirmed identical to the repo just before the test (`evidence/version-check.txt`, 14/14 MATCH).
- Throttling: `evidence/throttling-config.txt`. Alarms and dashboard: `src/infra/setup_alarms.sh` → `evidence/alarms-config.txt`.
- Load generator: `tests/load_test.py` (Python standard library only), run from AWS CloudShell in the same region. The chatbot route is deliberately excluded to protect the Groq free-tier quota.

## Command / steps

```bash
bash setup_alarms.sh <email> <API_ID>          # 7 alarms + SNS email + dashboard
python3 load_test.py https://<API_ID>.execute-api.us-east-1.amazonaws.com --persistence --out resilience-run.txt
```

| Phase | Load | Endpoint |
|---|---|---|
| A steady load | 10 parallel clients, 60 s | `GET /api/occupancy/current?at=…` (map at a time; heaviest read) |
| B spike | 60 parallel clients, 15 s, above the 50 req/s limit | `GET /api/locations` |
| C auth throttle | 30 rapid requests | `GET /api/auth/me` (signed out) |
| D persistence | sign in, book one slot, force a cold start of `crowdmap-bookings`, read the booking back, cancel it | `/api/auth/login`, `/api/bookings*` |

## Expected result

- A: all 200, no 5xx.
- B: a mix of 200 and 429, **no 5xx**.
- C: 401 (signed out) for allowed calls, 429 for throttled calls.
- D: booking still present after the cold start.
- Alarms: `crowdmap-http-4xx` enters ALARM during the spike and an email arrives; alarms return to OK afterwards.

## Actual result

Raw output: `evidence/resilience-run.txt` (A–C) and `evidence/persistence-run.txt` (D). Alarm emails: `evidence/alarm-notifications.txt`. Screenshots: `evidence/screenshots/2026-10-08-cloudwatch-*.png`.

| Phase | Requests | Throughput | Status codes | 5xx | Latency of 200s (p50 / p95 / p99 / max) | Verdict |
|---|---|---|---|---|---|---|
| A steady load | 364 in 61.4 s | 5.9 req/s | 200 × 364 | **0** | 1582 / 1700 / 5799 / 6167 ms | **Pass** (correct, but slow; see diagnosis) |
| B spike | 4,272 in 15.2 s | 281.5 req/s offered; about 74 req/s served | 200 × 1,122, **429 × 3,150** | **0** | 158 / 577 / 3577 / 3871 ms | **Pass**: throttling shed 74% of the spike; no errors |
| C auth throttle | 30 | n/a | 401 × 14, 429 × 9, **503 × 7** | 7 | n/a | **Partial**: throttle works, but 7 requests reached a busy single-writer Lambda |
| D persistence (run 1, 18:20) | n/a | n/a | login → 429 | n/a | n/a | **Not run as intended**: the test design was at fault (see diagnosis) |
| D persistence (run 2, 19:00) | n/a | n/a | login 200, booking **503** | 1 | n/a | **Fail**: booking rejected by the busy single writer (see diagnosis) |
| D persistence (run 3, 19:04) | 7 steps | n/a | login 200 → book **201** → forced cold start → my bookings 200 (booking present) → cancel 503, retry 200 | 0 after retry | my bookings after cold start: 3,887 ms | **Pass**: booking survived the restart |

**CloudWatch during the test** (dashboard screenshot):

- `crowdmap-api` ConcurrentExecutions peaked at about **66**. Lambda scaled out horizontally to absorb the spike.
- Requests peaked at about 4.35K per minute, most of the excess answered with 4xx (429).
- p95 latency peaked at about 5.4 s at the start of the spike (cold starts of new instances), then settled below about 2.7 s.

**Alarms:**

- `crowdmap-http-4xx` (2,962 in 5 min), `crowdmap-http-5xx` (7) and `crowdmap-bookings-throttled` (7) entered ALARM at 10:22 UTC, and SNS emails were received within about 5 minutes.
- 4xx and 5xx returned to **OK** automatically once the load stopped.

## Diagnosis and improvement plan

1. **Map endpoint latency (phase A, p50 about 1.6 s).**
   - Cause: `/occupancy/current` runs a correlated "latest reading at or before time" subquery over 99,008 rows for each of 64 rooms, with `julianday()` on the indexed column. That prevents index use. The same query takes about 0.9 s on a laptop, and Lambda at 512 MB has less CPU.
   - With 10 clients each waiting about 1.6 s, throughput is capped near 6 req/s. The cost is CPU per request, not a capacity limit: no errors occurred.
   - Improvements, cheapest first:
     - (a) give `crowdmap-api` more memory, which also gives it more CPU. **Applied and measured, see "Improvement verified" below.**
     - (b) cache the result per `at` hour inside the Lambda for 60 s. All users looking at the same hour share one query.
     - (c) compare ISO timestamps as text, so the existing `(location_id, timestamp)` index is used.
2. **503 in phase C (7 requests).**
   - Cause: `crowdmap-bookings` has reserved concurrency 1 (single writer by design). Requests that passed the 2 req/s route throttle but overlapped an in-flight request were rejected by Lambda. API Gateway returned them as 503.
   - This matches the `crowdmap-bookings-throttled` and `crowdmap-http-5xx` alarm counts (7 and 7).
   - Improvements:
     - (a) lower the auth/booking route throttle to 1 req/s, burst 1, so excess traffic gets a clean 429 at the gateway;
     - (b) in production, move bookings to a shared relational database (RDS) so writes can run concurrently and the writer can scale out.
3. **Phase D did not run as intended.**
   - Cause: it started immediately after phase C had drained the `/api/auth/*` throttle bucket, so the login itself was throttled (429). The throttle behaved correctly; the test was badly sequenced.
   - Fix (applied in `tests/load_test.py`): wait 30 s after phase C and retry login with back-off. `--only-persistence` allows phase D to be re-run on its own.
4. **Phase D run 2: booking returned 503.**
   - Cause: same mechanism as phase C. `crowdmap-bookings` accepts one request at a time, and a request arriving while it is busy is rejected (Lambda throttle, shown by API Gateway as 503) instead of queued. A request that overlaps another one (for example an open browser tab polling `/api/auth/me`) is enough.
   - A throttled request never reaches the application, so retrying it cannot create a duplicate booking.
   - Fix (applied in `tests/load_test.py`, `call_retry`): retry booking, read-back and cancel on 503/429/timeout, up to 5 times with a 3 s, 6 s, 9 s… back-off. Open browser tabs were closed before run 3.
   - Run 3 passed. The cancel step was rejected once (503) and succeeded on the retry, which shows that the retry recovers from the single-writer limit.
   - Recommendation: the frontend should apply the same retry on 503 for booking actions; long term, move bookings to RDS (see 2b).
5. **Persistence verified (run 3).** The booking created before the forced cold start (`aws lambda update-function-configuration`) was returned by a fresh `crowdmap-bookings` instance, which had re-downloaded the database from S3. The 3.9 s read-back includes that cold start (about 24 MB download).

## Improvement verified: Lambda memory 128 MB → 1024 MB (8 Oct, 19:13–19:15 SGT)

The deployment check (`aws-deployment-check.txt`) showed that all three Lambdas were running at the 128 MB default; the intended memory settings had been lost when the code was re-uploaded. Phases A–D above were therefore measured at 128 MB. `crowdmap-api` was raised to 1024 MB (`aws lambda update-function-configuration --memory-size 1024`) and phase A was re-run with the same command (`--only-steady`), the same endpoint and the same 10 clients.

| Phase A, 10 clients, 60 s | Requests | Throughput | 5xx | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| Before, 128 MB (18:20) | 364 | 5.9 req/s | 0 | 1,582 ms | 1,700 ms | 5,799 ms | 6,167 ms |
| After, 1024 MB, run 1 (19:13) | 2,814 | 46.8 req/s | 0 | 206 ms | 220 ms | 229 ms | 2,953 ms (cold start) |
| After, 1024 MB, run 2 (19:15) | 2,931 | 48.7 req/s | 0 | 206 ms | 218 ms | 229 ms | 492 ms |

- Median latency fell **7.7×** (1,582 → 206 ms) and throughput rose **8.3×** (5.9 → 48.7 req/s) with the same clients, confirming the diagnosis: the bottleneck was CPU per request, and Lambda allocates CPU in proportion to memory.
- Tail latency became flat (p99 229 ms vs 5.8 s).
- Throughput is now just below the 50 req/s stage throttle, so the gateway limit, not the backend, is the next ceiling.
- Cost: Lambda bills GB-seconds. Each request now uses about 8× the memory for about 1/8 of the time, so the cost per request is roughly the same, and still well inside the free allowance.
- Raw output: `evidence/steady-1024mb.txt`. Configuration after the change: `evidence/aws-deployment-check.txt`.

## Artefact path

- `evidence/resilience-run.txt` (phases A–C), `evidence/persistence-run.txt` (phase D, run 3), `tests/load_test.py` (test code)
- `evidence/alarm-notifications.txt`, `evidence/alarms-config.txt`, `evidence/screenshots/2026-10-08-cloudwatch-alarms-after-load-test.png`, `evidence/screenshots/2026-10-08-cloudwatch-dashboard-load-test.png`
- `evidence/steady-1024mb.txt` (before/after memory change), `evidence/aws-deployment-check.txt`
- `evidence/throttling-config.txt`, `evidence/version-check.txt`
