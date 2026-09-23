# Occuscope

**INF2006 Team Project 1 — Cloud Computing & Big Data**

A cloud-hosted campus map for SIT Punggol: **campus → building → floor → location**, with crowd level and today’s events.

## Problem statement

Students cannot tell whether the library is crowded, whether discussion rooms on a floor are free, or what is on around campus without walking the building. Occuscope answers those three questions on one map. Crowd bands (Quiet 0–30% / Moderate 31–70% / Crowded 71%+) come from an occupancy model trained on identified NUS datasets and transferred onto SIT location types. There is no live Punggol sensor feed; occupancy shown in the app is generated.

The visual map is modelled on SIT’s [Campus Wayfinder](https://www.singaporetech.edu.sg/campus-wayfinder) (map model only — not routing). The frontend has two separate map features: a **crowd heatmap** (colour from occupancy ratio) and a **wayfinder-style 3D/stacked campus view** (browse buildings and floors). Neither is turn-by-turn navigation.

## Team

| Name | Student ID | Role |
|---|---|---|
| Zi Qian | | Frontend / Map (heatmap UI + wayfinder UI) |
| Zul | | Backend / Database |
| Lideon | | Data / Machine Learning |
| Kristen | | Cloud / Scalability |
| Ryan | | Security / Monitoring / Testing |

Fill `student_id` and `group_id` in `project_manifest.yaml` before packaging. Deadline: **Sunday 11 October 2026, 11:59 PM**.

## Quick start

Python 3.11+. From the repo root (Windows):

```
python -m venv .venv
.venv\Scripts\activate
pip install -r analytics/requirements.txt
copy .env.example .env
python analytics/01_eda.py
python analytics/02_clean_robod.py
python analytics/03_eda_robod.py
python src/db/init_app_db.py
```

| Command | What it does |
|---|---|
| `01_eda.py` | Dummy SIT occupancy CSV for the app DB (`source = dummy`) |
| `02_clean_robod.py` | Cleans ROBOD → `data/processed/robod_clean.csv` (needs `data/raw/`) |
| `03_eda_robod.py` | Figures under `analytics/figures/` |
| `init_app_db.py` | Rebuilds `data/occuscope.db` from `src/db/schema.sql` + `data/sample/` |

`02` / `03` skip cleanly if you only need the SQLite seed: run `01` then `init_app_db.py`. Never commit `.env` or `data/raw/`.

The web app is not runnable yet. Integration surface until then: `src/api-contract.md` and the local database.

## Architecture

Two pipelines, one map:

1. **Offline ML** — ROBOD (+ optional NUS Wi-Fi) in `data/raw/` → `analytics/` → generated SIT occupancy and forecasts.
2. **App database** — SIT `building` / `location` / `occupancy` / `event` (SQLite now, RDS later). API reads the DB; frontend reads the API.

Crowd bands are **not stored**. View `v_occupancy_current` computes `occupancy_ratio` and `crowd_level` from `occupancy_count / capacity`. Heatmap data is `GET /occupancy/current` (`map_x`, `map_y`, `occupancy_ratio`). Heatmap and wayfinder UIs are Zi Qian’s; occupancy numbers are Lideon’s; HTTP is Zul’s.

Diagram (Kristen): [`evidence/architecture.png`](evidence/architecture.png) — not drawn yet.

## Technology

- Cloud: AWS (EC2 behind a load balancer, managed relational DB e.g. RDS — to be confirmed)
- Local DB: SQLite (`DATABASE_URL=sqlite:///data/occuscope.db`)
- Training data:
  - [ROBOD](https://github.com/ideas-lab-nus/robod) — NUS rooms, ground-truth occupant counts, 5-minute ticks
  - [NUS Wi-Fi floor counts](https://zenodo.org/records/17578240) — floors L2–L6, 2018, CC BY 4.0

Schema: `src/db/schema.sql`. API: `src/api-contract.md`. Columns: `data/DATA_DICTIONARY.md`. How to get raw files: `data/README.md`.

## Repository layout

| Path | Purpose |
|---|---|
| `src/` | API contract, database schema, (later) app code |
| `data/sample/` | SIT seed CSVs |
| `data/processed/` | Cleaned ROBOD table |
| `data/raw/` | NUS downloads (gitignored) |
| `analytics/` | Clean / EDA / (later) training |
| `evidence/` | Marker tests, architecture, monitoring |
| `tests/` | Repeatable tests |
| `project_manifest.yaml` | Required submission summary |

## Status

**Done:** schema and sample SIT locations; dummy occupancy seed; ROBOD cleaned (52k rows); EDA figures; data-AI test notes for EDA.

**Not done:** occupancy model; generated SIT occupancy (`source = generated`); REST API and frontend; AWS deploy, auth, monitoring; architecture diagram; four required tests (except the EDA half of data/AI).

## Known limitations

- ROBOD and the Wi-Fi series are NUS buildings, not SIT Punggol sensors.
- ROBOD in this dump is **weekdays only** (no Sat/Sun rows).
- Map “current” occupancy is generated (dummy weekday shape until the model writes `source = generated`).
- Sample map is a starter set (library, two discussion rooms, one LT, food court), not a full campus inventory.
- Wi-Fi device counts are not the same as people (ROBOD corr. ≈ 0.69 with occupant_count).
