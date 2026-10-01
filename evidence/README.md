# Evidence

Named artefacts cited by `project_manifest.yaml`. Fill these before submission; keep account IDs, IPs, and secrets redacted.

| File | Test / artefact | Owner |
|---|---|---|
| `architecture.png` | One labelled architecture diagram | Kristen |
| `test-functional.md` | Workflow test (map + API) | Zi Qian / Zul |
| `test-security.md` | Named threat vs control | Ryan |
| `test-data-ai.md` | Occupancy model validation | Lideon |
| `train-holdout-local.txt` | Raw `04_train.py` hold-out / C5 log | Lideon |
| `generate-sit-local.txt` | Raw `05_generate_sit.py` log | Lideon |
| `holdout-diagnostics-local.txt` | Raw `06_holdout_diagnostics.py` log | Lideon |
| `test-resilience.md` | Scale / failover / recovery | Kristen |
| `monitoring.md` | CloudWatch (or equivalent) export | Ryan |
| `threat-control-map.md` | Threat → control → evidence path | Ryan |
| `test-frontend-map.md` | Supporting map / browser evidence | Zi Qian |
| `functional-run-local.txt` | Raw local functional workflow run output | Ryan |
| `security-api-local.txt` | Raw local API security test output | Ryan |
| `security-offline-tests.txt` | Raw offline security / hygiene test output | Ryan |
| `secret-scan-local.txt` | Raw secret-pattern scan output | Ryan |
| `preflight-local.txt` | Raw submission preflight output | Ryan |
| `security-review.md` | Static security review (frontend, API, Lambda) | Ryan |
| `frontend-server-security-local.txt` | Raw frontend dev-server security test output | Ryan |

Each test file must include: objective, setup, command/steps, expected result, actual result (dated), artefact path.
