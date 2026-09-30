# AI use declaration

Update this table whenever a tool is used on a submission artefact. Team members verify before the ZIP is frozen.

| Tool | Where used | What it produced | Team verification | Licence / source |
|---|---|---|---|---|
| Cursor (Grok) | Repo kickoff, 23 September 2026 | Manifest skeleton, folder layout, sample SIT CSVs, SQLite schema/init, EDA stub, README / data dictionary / API contract | Lideon reviewed against the INF2006 brief and inspected ROBOD / Zenodo columns locally | N/A (AI-assisted authoring) |
| Cursor (Grok) | Occupancy v0 and SIT generate, 26 September 2026 | Training script, hold-out metrics, generation overlay from the public SIT calendar, README / dictionary / data-AI evidence updates | Lideon compared models on NUS hold-out, checked generated ratios against the academic calendar, and retained the hour×type mean as v0 | N/A (AI-assisted authoring) |
| Cursor (Grok) | Security evidence, 26 September 2026 | `evidence/threat-control-map.md`, `evidence/test-security.md`, `evidence/monitoring.md`; gitignore unittest; network intended control | Ryan checked against the INF2006 brief (threat-map path, test headings, secrets handling, no live-sensor claim) | N/A (AI-assisted authoring) |
| Cursor (Grok) | Tri 1 seed + store hygiene, 29 September 2026 | Full-trimester generate, MOM holidays, API `?at=` notes, `tests/test_data_store_hygiene.py` | Lideon checked timestamps (`+08:00`), generated sources in SQLite, and that NUS raw stays out of git and the app DB | N/A (AI-assisted authoring) |
| Cursor (Grok) | RBS rooms + Wi-Fi ablation, 30 September 2026 | Catalogue locations; `metrics_wifi_ablation.csv`; crowd/seed tests; pinned `analytics/requirements.txt` | Lideon matched room ids to RBS screenshots and kept v0 without Wi-Fi after NUS MAE improved with room Wi-Fi | N/A (AI-assisted authoring) |
| Codex | Frontend and original model, 29–30 September 2026 | `src/frontend/`: UI, data adapter, development proxy, tests and documentation | Agent ran five data/API tests and checked room/floor selection in-browser; human team review pending. Original procedural campus model; catalogue-driven floors and markers. | AI-assisted UI and original illustrative geometry; SIT wayfinder used as reference |
| Cursor | Security evidence, 30 September 2026 | `tests/test_api_security.py`, evidence updates | Ryan ran the tests and reviewed outputs against `src/api-contract.md` | N/A |
| Cursor | Functional evidence, 30 September 2026 | `evidence/test-functional.md`, `evidence/functional-run-local.txt`, manifest run section | Ryan ran the commands and checked outputs against `src/api-contract.md` and `src/frontend/README.md` | N/A |
| Cursor | Preflight and secret scan, 30 September 2026 | `tests/test_no_secrets_in_tracked_files.py`, `tests/test_submission_preflight.py`, monitoring export commands, report draft (local) | Ryan ran the tests and reviewed the outputs; report draft to be checked against evidence | N/A |

## Datasets and baselines (must cite)

- ROBOD — Tekler et al., *Building Simulation* 2022; Figshare DOI 10.6084/m9.figshare.19234530; GitHub `ideas-lab-nus/robod`
- NUS Wi-Fi floor counts — Wang / DeST Lab, Zenodo DOI 10.5281/zenodo.17578240, **CC BY 4.0**
- SIT Campus Wayfinder: https://www.singaporetech.edu.sg/campus-wayfinder — embeds https://pcmap-sit-visitor.netlify.app/. Occuscope links this as a reference; the frontend renders its own illustrative model, with no embedded provider map or copied map assets.

No production credentials, personal data, or proprietary SIT sensor feeds are used.
