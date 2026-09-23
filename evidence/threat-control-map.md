# Threat–control map

| Threat | Control | Where it lives | Evidence |
|---|---|---|---|
| Secrets in git | `.env` gitignored; `.env.example` placeholders only | repo root | this table, `.gitignore` |
| Unauthenticated write to occupancy/events | Auth on mutating routes (if used); public read of crowd map TBD | backend | security test |
| Over-privileged cloud IAM | Least-privilege roles for EC2/RDS/CloudWatch | AWS config (redacted) | exported policy |
| Injection via API input | Validation on IDs, timestamps, query params | backend | security test |
| Treating synthetic SIT counts as real people | Limitations in README + report | docs | data/AI test |

Ryan owns filling this as controls are implemented.
