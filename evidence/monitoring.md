# Monitoring evidence

Owner: Ryan (Security / Monitoring / Testing). Source of metrics: Kristen’s CloudWatch / SNS artefacts from the 8 October 2026 load test. Account IDs, API IDs, hostnames and emails are not copied here.

Pointer (do not re-export unless the lab is re-run): `evidence/alarms-config.txt`, `evidence/alarm-notifications.txt`, `evidence/screenshots/2026-10-08-cloudwatch-dashboard-load-test.png`, `evidence/screenshots/2026-10-08-cloudwatch-alarms-after-load-test.png`, `evidence/test-resilience.md`.

# What is instrumented

Seven CloudWatch alarms on SNS topic `crowdmap-alerts` (email on ALARM and OK), period 5 minutes, created with `src/infra/setup_alarms.sh`:

- Lambda `Errors` ≥ 1 on `crowdmap-api`, `crowdmap-bookings`, `crowdmap-web`
- `crowdmap-bookings` `Throttles` ≥ 1 (single-writer saturation)
- API Gateway 5xx ≥ 5, 4xx ≥ 50, p95 latency ≥ 3 s

Dashboard `crowdmap`: requests, 4xx/5xx, latency p50/p95, Lambda invocations/errors/throttles/concurrency, alarm state.

# Date

8 October 2026 (load test window ~10:17–10:22 UTC / 18:17–18:22 SGT). Interpretation written 10 October 2026 from those redacted files (lab was not re-queried).

# Interpretation

During the spike, `crowdmap-http-4xx` saw **2,962** 4xx in five minutes (mostly HTTP 429 from the 50 req/s stage throttle) and entered ALARM; that is the gateway doing its job, not a map outage. `crowdmap-http-5xx` (**7**) and `crowdmap-bookings-throttled` (**7**) fired together: overlapping auth/booking calls hit reserved concurrency 1 and API Gateway surfaced Lambda throttles as 503. Emails arrived within about five minutes; 4xx and 5xx returned to **OK** without manual action once load stopped. We would page on 5xx and booking throttles, and treat a 4xx alarm as “throttle absorbed a spike” unless 5xx rises with it.

# Limitations

RDS / ALB metrics from the old wishlist do not apply (serverless; SQLite on S3). Live CloudWatch was not re-exported on 10 October. Confirm Groq key rotation and `crowdmap-bookings` memory after the lab is back (Kristen freeze TODOs); those are operations follow-ups, not substitutes for the 8 October alarm evidence.
