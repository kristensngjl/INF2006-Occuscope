# Team contributions

One row per member. Fill student IDs, commit hashes, and reflections before the ZIP is submitted.

| Name | Role | Artefacts / commits (so far) | Test / evidence ownership | Reflection |
|---|---|---|---|---|
| Zi Qian | Frontend / Map | Campus map UI in `src/` (not started) | Functional test (map workflow) | |
| Zul | Backend / Database | REST APIs against `src/api-contract.md` (not started); RDS later | Functional test (API), schema evidence | |
| Lideon | Data / ML | `analytics/` (clean, EDA, train, generate); `data/` dictionary and SIT seeds including Tri 1 occupancy; `src/db/schema.sql` and `init_app_db.py`; `evidence/test-data-ai.md` | Data / AI test (`evidence/test-data-ai.md`) | Compared a leakage-safe hold-out and shipped the hour×type mean when it beat Ridge/RF, rather than a more complex model. SIT map values are generated and labelled as such. |
| Kristen | Cloud / Scalability | `evidence/architecture.png`, deploy/scale | `evidence/test-resilience.md` | |
| Ryan | Security / Monitoring / Testing | Intended controls in `evidence/threat-control-map.md`; named-threat security test in `evidence/test-security.md`; CloudWatch wishlist in `evidence/monitoring.md`; `tests/test_gitignore_secrets.py`; files Lideon’s `evidence/test-data-ai.md` in the test pack. IAM / CloudWatch actuals after deploy. | `evidence/test-security.md`, `evidence/monitoring.md`; coordinates all four tests (`test-data-ai.md` already written) | |
