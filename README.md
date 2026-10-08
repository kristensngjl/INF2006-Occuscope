# Occuscope

**INF2006 Team Project 1 — Cloud Computing and Big Data**

Occuscope is a hierarchical campus map for SIT Punggol (**campus → building → floor → location**). Students can see Quiet / Moderate / Crowded at mapped rooms and what is on the calendar that day, without walking the building first.

There is **no live Punggol sensor feed**. Occupancy on the map is **model-generated** from NUS training data plus an academic-calendar overlay, not cameras or Room Booking System availability.

The visual layout follows SIT’s [Campus Wayfinder](https://www.singaporetech.edu.sg/campus-wayfinder) as a **map reference only** (not turn-by-turn routing). The frontend has two features: a **crowd heatmap** (colour from occupancy ratio) and a **wayfinder-style 3D campus view**.

Architecture diagram: [`evidence/architecture.png`](evidence/architecture.png) (Kristen). Data/AI evidence: [`evidence/test-data-ai.md`](evidence/test-data-ai.md). Manifest: [`project_manifest.yaml`](project_manifest.yaml). Deadline: **Sunday 11 October 2026, 11:59 PM**. Group: **G007**.

## Team

| Name | Student ID | Role |
|---|---|---|
| Zi Qian | 2501958 | Frontend / Map (heatmap UI and wayfinder UI) |
| Zul | 2500993 | Backend / Database |
| Lideon | 2501098 | Data / Machine Learning |
| Kristen | 2501481 | Cloud / Scalability |
| Ryan | 2501205 | Security / Monitoring / Testing |

## Quick start — run the site

Python 3.11+ and Node.js 18+. From the repository root, **two terminals**:

```powershell
python src/db/init_app_db.py
python -m pip install -r src/backend/requirements.txt
python -m uvicorn src.backend.api:app --host 127.0.0.1 --port 8000
```

```powershell
node src/frontend/server.mjs
```

Open **http://127.0.0.1:5173**. The frontend proxies `/api` to port 8000. `init_app_db.py` **deletes and rebuilds** `data/occuscope.db` from `data/sample/` (64 locations, Trimester 1 generated occupancy, demo student accounts, and discussion-room demo bookings). Skip it if you already have a seed you want to keep.

**Follow Singapore time** (default on) snaps the map to now SGT, clamped to 31 August–27 December 2026, 08:00–20:00. Uncheck it to pick a date/hour for a demo. Occupancy stays generated either way.

Copy `.env.example` to `.env` only if you run the optional campus chat (Groq). Never commit `.env`. Chat is not the occupancy model.

## Student demo login

Login uses pre-created fictional student accounts, with email and password only. Seed accounts without rebuilding or wiping campus data:

```powershell
python -m src.db.seed_students
```

This adds exactly 1,998 students: **2500001–2500999** and **2600001–2600999**. Email format: `studentid@sit.singaporetech.edu.sg`. Each profile has a generated name; the shared demo password is **OccuscopeDemo26!**. Passwords are salted and hashed in SQLite. Re-running the command preserves existing accounts and passwords. IDs 2500000 and 2600000 are excluded. These accounts do not authenticate against SIT or send any emails.

`init_app_db.py` already creates these accounts. Use `seed_students` only when the campus database exists and logins are missing. Restart the backend and Node server, then **Student login** with the full email and password. Self-registration is disabled. [Booking implementation notes](src/backend/BOOKING_SETUP.md).

## Quick start — reproduce occupancy (data / ML)

Training in this repo used **Python 3.11.9**. `data/raw/` (ROBOD CSVs, Wi-Fi xlsx) is **gitignored and not in the ZIP**. Markers can re-run hold-out metrics from committed `data/processed/robod_clean.csv`. Rebuild that file, or the C5 Wi-Fi ablation, only if you have downloaded Figshare/Zenodo locally (`data/README.md`). `occupancy_v0.joblib` is gitignored; run `04_train.py` before `05_generate_sit.py` if you need a new generate.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r analytics/requirements.txt
python analytics/02_clean_robod.py
python analytics/03_eda_robod.py
python analytics/04_train.py
python analytics/06_holdout_diagnostics.py
python analytics/05_generate_sit.py
python src/db/init_app_db.py
```

| Command | Purpose |
|---|---|
| `02_clean_robod.py` | Clean ROBOD → `data/processed/robod_clean.csv` |
| `03_eda_robod.py` | Figures under `analytics/figures/` |
| `04_train.py` | Date hold-out; `metrics_holdout.csv`; `occupancy_v0.joblib` |
| `06_holdout_diagnostics.py` | MAE by type/hour; 7 vs 14-day window; persist vs v0; NUS crowd-band counts |
| `05_generate_sit.py` | SIT occupancy (`source = generated`) |
| `init_app_db.py` | Rebuild SQLite from schema + `data/sample/`, including demo logins and DR bookings |
| `01_eda.py` | Dummy occupancy fallback (`source = dummy`) |

Map API: `GET /occupancy/current?at=` (ISO-8601 with `+08:00`; do not use `MAX(timestamp)` — that is trimester break). Timeline: `GET /occupancy/{id}?from=&to=` (max seven days). Next two hours: `GET /occupancy/{id}/prediction?at=` (lookahead in the generated series). Contract: [`src/api-contract.md`](src/api-contract.md).

## Method (data and occupancy)

Crowd bands: **Quiet** ≤ 0.30, **Moderate** ≤ 0.70, otherwise **Crowded**. They are computed in SQL views from `occupancy_count / capacity`, not stored columns.

1. **Train on NUS labels only.** ROBOD `occupant_count`, 5-minute ticks. v0 features: hour, weekday, room type (transferable to SIT without campus sensors). **Date hold-out** (last 14 days), not shuffled rows.
2. **Select on NUS MAE.** Hour × room-type mean beat Ridge and Random Forest (MAE **1.74** vs ~1.83). Negative R² on the hold-out is reported (late-term regime). Lecture MAE is higher than office/library; 15:00 is harder than overnight. A 7-day hold-out MAE is ~1.73 (same order). Copying last hour’s NUS count beats v0 for 1–2 hour MAE; SIT has **no last reading**, so the map does not use persist.
3. **Generate SIT rows.** Ratio = v0 count / ROBOD type 95th percentile × SIT capacity × calendar × mixed event turnout × per-room mix (without mix, every discussion room would match at 15:00). Event titles such as lunch do not force high or low occupancy. Weeks 12–13 (swot) and week 14 (exams) raise discussion-room bookings and study-space occupancy. Available DRs stay a mix of walk-in and empty. 64 locations, 31 August–27 December 2026, 08:00–20:00 SGT. Foodgle Hub (E4 L1) stays open on weekends and public holidays; Wholesome (W3 L2) is Saturday until 15:00 and closed Sunday/PH ([SIT Punggol Campus](https://www.singaporetech.edu.sg/about/punggol-campus)). They are occupancy-only, not discussion-room bookings.
4. **Calendar overlay (generate only).** [SIT AY2026/27 Trimester 1](https://www.singaporetech.edu.sg/admissions/undergraduate/academic-calendar-sit-and-joint-programmes); [MOM 2026 holidays](https://www.mom.gov.sg/newsroom/press-releases/2025/0616-public-holidays-for-2026). East (E2, E6) = IT IWSP mix; W3/W5 = other courses; **W1 library is shared**. OIP 2026 dates are unpublished (window off).

Same Quiet/Moderate/Crowded cut-offs on NUS hold-out: 08:00 is almost all Quiet; 15:00 is mixed. That is a band sanity check, not SIT accuracy.

## Architecture

1. **Offline analytics** — ROBOD / NUS Wi-Fi in `data/raw/` (gitignored). Never loaded into the app database.
2. **Application database** — SIT buildings, 64 locations, generated occupancy, events (`data/occuscope.db` locally; on AWS the same SQLite file is stored in a private S3 bucket and loaded by Lambda). API reads SQLite; the browser reads the API only.

| Piece | Owner |
|---|---|
| Occupancy values, generate, metrics | Lideon |
| REST API, schema | Zul |
| Heatmap + 3D wayfinder UI | Zi Qian |
| AWS deploy / scale | Kristen |
| Security tests / evidence pack | Ryan |

## Technology

- App: HTML/CSS/JS frontend (`src/frontend/`), FastAPI (`src/backend/`), SQLite (`src/db/schema.sql`)
- Cloud: AWS serverless, `us-east-1`: API Gateway HTTP API `crowdmap-http` → 3 Lambdas (`crowdmap-web`, `crowdmap-api`, `crowdmap-bookings`, Python 3.11) → private S3 (`crowdmap-web-<group>`, `crowdmap-lake-<group>`); CloudWatch alarms + SNS; AWS Budgets. Deployment record and redeploy steps: [`evidence/deploy-log.md`](evidence/deploy-log.md). Diagram: [`evidence/architecture.png`](evidence/architecture.png)
- Training: Python 3.11.9, pandas / scikit-learn; [ROBOD](https://github.com/ideas-lab-nus/robod) (Tekler et al., *Building Simulation*, 2022); [NUS Wi-Fi floors](https://zenodo.org/records/17578240) CC BY 4.0 (ablation only; unused in v0)

## Repository layout

| Path | Purpose |
|---|---|
| `src/frontend/` | Map UI and local static server |
| `src/backend/` | FastAPI + Lambda handler |
| `src/db/` | Schema and SQLite seed |
| `src/api-contract.md` | HTTP contract |
| `data/sample/` | SIT seed CSVs (generated occupancy, calendar) |
| `data/processed/` | Cleaned ROBOD (committed) |
| `data/raw/` | NUS downloads (gitignored) |
| `analytics/` | Clean, EDA, train, generate, hold-out diagnostics |
| `evidence/` | Marker tests and logs |
| `tests/` | Repeatable tests |
| `project_manifest.yaml` | Submission summary |

## Limitations

- ROBOD and Wi-Fi describe **NUS**, not SIT Punggol. SIT occupancy is not labelled; campus accuracy is not reported.
- This ROBOD extract is **weekdays only**. Weekend map hours use Friday’s hour shape × an explicit weekend factor.
- Follow Singapore time only chooses which **generated** hour to show. Discussion rooms show Booked/Available for 08:00–20:00 SGT (`booked=1` when a seeded or student booking overlaps). Occupancy is a mix: booked with people, booked but empty, walk-in, and empty available. Study spaces and food courts show occupancy only.
- Per-room mix and IWSP factors are not live RBS. Campus calendar pins are a demo overlay inspired by typical SIT student life, not copied official listings.
- Study-space capacities are estimates. Catalogue: RBS discussion rooms (screenshots, not a scrape); E2/E6 Wayfinder study spaces; W1 from [LibHelp](https://libhelp.singaporetech.edu.sg/faq/277332) / [library facilities](https://libguides.singaporetech.edu.sg/library/facilities); Foodgle Hub and Wholesome hours from [SIT Punggol Campus](https://www.singaporetech.edu.sg/about/punggol-campus) (Foodgle open Sat/Sun/PH; Wholesome Saturday until 15:00, closed Sunday/PH). Occupancy is generated; seating is not booked in Occuscope. W5 has DR18–DR20 and DR23–DR26 (**not** DR21/DR22). ACE seminar rooms are not seeded as open study.
- Wi-Fi device counts are not people (corr ≈ 0.69 with ROBOD occupants). Room Wi-Fi helps NUS MAE but is unused in v0 (SIT has no matching feed).
- Cloud: bookings use a **single writer** (`crowdmap-bookings`, reserved concurrency 1) over a SQLite file in S3, so concurrent booking requests are rejected with 503 and must be retried; readers see new bookings up to about 60 s later. A shared database (RDS) is the production fix ([`evidence/test-resilience.md`](evidence/test-resilience.md)).
- Cloud: AWS Academy Learner Lab blocks CloudFront and custom IAM roles, so there is no CDN/WAF and all Lambdas share `LabRole` (intended least-privilege policy in [`evidence/deploy-log.md`](evidence/deploy-log.md)). The live service stops when the lab session ends; evidence is captured as dated, redacted files.
