# AI use declaration

Update this table whenever a tool is used on a submission artefact. Team members verify before the ZIP is frozen.

| Tool | Where used | What it produced | Team verification | Licence / source |
|---|---|---|---|---|
| Cursor (Grok) | Repo kickoff, 23 September 2026 | Manifest skeleton, folder layout, sample SIT CSVs, SQLite schema/init, EDA stub, README / data dictionary / API contract | Lideon reviewed against the INF2006 brief and inspected ROBOD / Zenodo columns locally | N/A (AI-assisted authoring) |
| Cursor (Grok) | Occupancy v0 and SIT generate, 26 September 2026 | Training script, hold-out metrics, generation overlay from the public SIT calendar, README / dictionary / data-AI evidence updates | Lideon compared models on NUS hold-out, checked generated ratios against the academic calendar, and retained the hour×type mean as v0 | N/A (AI-assisted authoring) |

## Datasets and baselines (must cite)

- ROBOD — Tekler et al., *Building Simulation* 2022; Figshare DOI 10.6084/m9.figshare.19234530; GitHub `ideas-lab-nus/robod`
- NUS Wi-Fi floor counts — Wang / DeST Lab, Zenodo DOI 10.5281/zenodo.17578240, **CC BY 4.0**
- Visual map reference only (not copied as product code): SIT Campus Wayfinder

No production credentials, personal data, or proprietary SIT sensor feeds are used.
