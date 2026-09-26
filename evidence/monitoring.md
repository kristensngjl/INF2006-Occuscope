# Monitoring evidence

Ryan: CloudWatch dashboard / log query goes here after Kristen deploys. Redact account IDs, IPs, and secrets before paste.

# Wishlist (implement on AWS; not running today)

Kristen should expose at least:

- API 4xx and 5xx counts (by route if possible)
- API latency (p50 / p99)
- RDS connection count / failed connections
- Failed auth count (only if mutating routes exist; skip if API is public read-only)
- Deploy / instance health (ALB target or Lambda errors)

Logs should not contain `.env` values, access keys, or full connection strings.

# Date

TODO (blocked on deploy)

# Interpretation

TODO after the first redacted export: whether error rate and latency are acceptable for the demo, and what we would page on.
