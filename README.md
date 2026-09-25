# Occuscope

**INF2006 Team Project 1 — Cloud Computing and Big Data**

Occuscope is a hierarchical campus map for SIT Punggol (**campus → building → floor → location**). It shows crowd level at mapped spaces and the events scheduled for the day.

## Problem statement

Students cannot tell whether the library is crowded, whether discussion rooms on a given floor are free, or what is on around campus without walking the building. Occuscope answers those three questions on one map.

Crowd bands are **Quiet** (occupancy ratio ≤ 0.30), **Moderate** (≤ 0.70), and **Crowded** (otherwise). They are derived from an occupancy model trained on identified NUS datasets and transferred onto SIT location types and capacities. There is no live Punggol sensor feed; occupancy shown in the application is **generated**, not measured on site.

The visual map is modelled on SIT’s [Campus Wayfinder](https://www.singaporetech.edu.sg/campus-wayfinder) as a **map layout reference only** (not routing). The frontend comprises two separate features: a **crowd heatmap** (colour from occupancy ratio) and a **wayfinder-style stacked / 3D campus view** (browse buildings and floors). Neither is turn-by-turn navigation.

## Team

| Name | Student ID | Role |
|---|---|---|
| Zi Qian | | Frontend / Map (heatmap UI and wayfinder UI) |
| Zul | | Backend / Database |
| Lideon | | Data / Machine Learning |
| Kristen | | Cloud / Scalability |
| Ryan | | Security / Monitoring / Testing |

Fill `student_id` and `group_id` in `project_manifest.yaml` before packaging. Submission deadline: **Sunday 11 October 2026, 11:59 PM**.

## Method (data and occupancy)

1. **Train on NUS labels only.** ROBOD provides ground-truth `occupant_count` at five-minute resolution. Features used in v0 are transferable to SIT without campus sensors: hour of day, day of week, and room type. Evaluation is a **date hold-out** (last 14 days), not a shuffled split, so adjacent 5-minute ticks cannot leak from test into train.
2. **Select the model on NUS hold-out MAE.** An hour × room-type mean lookup outperformed Ridge and Random Forest (MAE 1.74 versus approximately 1.83). That lookup is saved as `occupancy_v0`. Negative R² on the hold-out is reported: the test window is a different occupancy regime (late term).
3. **Generate SIT occupancy.** Predicted NUS count is converted to a utilisation ratio (count / type 95th percentile), scaled by SIT `location.capacity`, then adjusted by an explicit academic calendar overlay (`data/sample/sit_calendar.json`).
4. **Calendar overlay (generate time only).** Teaching, recess (week 7: 12–18 October 2026), final assessment, and trimester break follow the published [SIT AY2026/27 Trimester 1 calendar](https://www.singaporetech.edu.sg/admissions/undergraduate/academic-calendar-sit-and-joint-programmes). Integrated Work Study Programme (IWSP) effects are a **programme mix**, not live booking data: East blocks (E2, E6) represent IT courses; West teaching blocks (W3, W5) represent other courses; **W1 library is shared** and is not placed on that split. Overseas Immersion Programme (OIP) dates for 2026 are not published; that window is disabled.

Crowd bands are **not stored as columns**. View `v_occupancy_current` computes `occupancy_ratio` and `crowd_level` from `occupancy_count / capacity`.

Full column notes and licences: `data/DATA_DICTIONARY.md`. Replayable test: `evidence/test-data-ai.md`.

## Quick start

Python 3.11+. Training in this repository was run on **Python 3.11.9** (scikit-learn 1.9.1, joblib 1.6.0). From the repository root (Windows):

```
python -m venv .venv
.venv\Scripts\activate
pip install -r analytics/requirements.txt
copy .env.example .env
python analytics/02_clean_robod.py
python analytics/03_eda_robod.py
python analytics/04_train.py
python analytics/05_generate_sit.py
python src/db/init_app_db.py
```

Place ROBOD CSVs and the NUS Wi-Fi workbook in `data/raw/` first (`data/README.md`). Never commit `.env` or `data/raw/`.

| Command | Purpose |
|---|---|
| `02_clean_robod.py` | Clean ROBOD → `data/processed/robod_clean.csv` |
| `03_eda_robod.py` | Figures under `analytics/figures/` |
| `04_train.py` | Time hold-out; `analytics/metrics_holdout.csv` and `analytics/models/occupancy_v0.joblib` |
| `05_generate_sit.py` | SIT occupancy and two-hour forecasts (`source = generated`) |
| `init_app_db.py` | Rebuild `data/occuscope.db` from `src/db/schema.sql` and `data/sample/` |
| `01_eda.py` | Dummy occupancy fallback only (`source = dummy`) |

The web application is not runnable yet. Integration surface until then: `src/api-contract.md` and the local database. `init_app_db.py` loads generated occupancy up to `map_as_of` in `sit_calendar.json` so `v_occupancy_current` reflects a teaching weekday, not trimester break.

## Architecture

Two stores, one map:

1. **Offline analytics** — ROBOD (and optional NUS Wi-Fi) remain in `data/raw/` and are never copied into the application database.
2. **Application database** — SIT `building`, `location`, `occupancy`, `event`, `occupancy_prediction` (SQLite locally; RDS later). The API reads the database; the frontend reads the API.

Heatmap payload: `GET /occupancy/current` (`map_x`, `map_y`, `occupancy_ratio`, `crowd_level`). Heatmap and wayfinder UIs: Zi Qian. Occupancy values: Lideon. HTTP: Zul.

Architecture diagram (Kristen): [`evidence/architecture.png`](evidence/architecture.png) — to be supplied.

## Technology

- Cloud: AWS (deployment topology to be confirmed with the cloud owner: EC2 + load balancer + RDS, or API Gateway + Lambda + S3)
- Local database: SQLite (`DATABASE_URL=sqlite:///data/occuscope.db`)
- Training data:
  - [ROBOD](https://github.com/ideas-lab-nus/robod) — NUS rooms, ground-truth occupant counts, 5-minute ticks (Tekler et al., *Building Simulation*, 2022)
  - [NUS Wi-Fi floor counts](https://zenodo.org/records/17578240) — floors L2–L6, 2018, CC BY 4.0 (not used in v0)

Schema: `src/db/schema.sql`. API: `src/api-contract.md`.

## Repository layout

| Path | Purpose |
|---|---|
| `src/` | API contract, database schema, local SQLite initialiser |
| `data/sample/` | SIT seed CSVs, generated occupancy, academic calendar overlay |
| `data/processed/` | Cleaned ROBOD table |
| `data/raw/` | NUS downloads (gitignored) |
| `analytics/` | Clean, exploratory analysis, train, generate |
| `evidence/` | Marker tests, architecture, monitoring |
| `tests/` | Repeatable tests |
| `project_manifest.yaml` | Required submission summary |

## Status

**Completed (data / ML):** identified datasets; ROBOD cleaned; exploratory figures; v0 occupancy model with baseline comparison; generated SIT occupancy and next-two-hour predictions; academic-calendar overlay as above.

**Outstanding:** confirm W5 Room Booking System codes; REST API and frontend; AWS deployment; report sections and remaining tests; pin runtime with the Lambda owner (trained on Python 3.11.9).

## Limitations

- ROBOD and the Wi-Fi series describe NUS buildings. They supply time-of-day and type shape, not SIT Punggol ground truth. SIT occupancy is not labelled; campus accuracy is not reported.
- This ROBOD extract contains **weekdays only**. Weekend map values use a Friday occupancy shape scaled by an explicit weekend factor.
- Map “current” occupancy is generated (v0 + calendar overlay). Recess and examination dates follow the public SIT calendar (subject to change). IWSP reductions are a documented programme mix, not official per-room bookings. OIP 2026 dates are not published.
- Sample locations are discussion-room identifiers from Room Booking System catalogue screenshots (not a live scrape), plus W1 library spaces. W5 identifiers follow the W3 layout with codes DR06–DR09 pending confirmation. Capacities are inferred from furniture in those photos.
- Wi-Fi connected-device counts are not the same as people (correlation with ROBOD `occupant_count` ≈ 0.69). They are unused in v0.
