# Data

Two stores are kept separate. NUS training files are never loaded into the application database.

| Kind | Location | In `occuscope.db`? |
|---|---|---|
| NUS training files (ROBOD CSVs, Wi-Fi workbook) | `raw/` (gitignored) | No — `analytics/` only |
| Cleaned ROBOD | `processed/robod_clean.csv` | No |
| SIT seed and generated occupancy | `sample/` | Yes — `python src/db/init_app_db.py` |
| Local application database | `occuscope.db` (gitignored) | This file is the database |

Field names, licences, and application tables: **`DATA_DICTIONARY.md`**.

## Obtaining training files

**ROBOD** — from [ideas-lab-nus/robod](https://github.com/ideas-lab-nus/robod), download the repository ZIP and copy `Data/combined_Room1.csv` … `combined_Room5.csv` into `data/raw/`.

**NUS Wi-Fi floors** — [zenodo.org/records/17578240](https://zenodo.org/records/17578240) (CC BY 4.0). Place `raw_data.xlsx` in `data/raw/`. Training, if used, is restricted to sheet `5min`.

Do not `git add` `data/raw/`. The ZIP the marker unpacks will not contain it. Rebuild `processed/robod_clean.csv` only if you have the Figshare/Zenodo files. Committed `processed/robod_clean.csv` is enough to re-run hold-out metrics.

## Sample files (committed)

SIT room catalogue uses Room Booking System **display names only** (screenshots; not a live scrape) for discussion/meeting rooms. Open **study spaces** follow public Campus Wayfinder labels (E2/E6 “Study Space”) and [library facilities](https://libguides.singaporetech.edu.sg/library/facilities) / [LibHelp W1 study spaces](https://libhelp.singaporetech.edu.sg/faq/277332) (Learning Commons, amphitheatre, Project Hubs, L4–L6 open study). Capacity for named study spaces is estimated (~28) unless RBS furniture is known. ACE seminar rooms (SR204, …) are taught classrooms and are **not** seeded as open study.

| File | Role |
|---|---|
| `sample/buildings.csv` | E2, E4 (Campus Court / Foodgle), E6, W1 (library), W3, W5 |
| `sample/locations.csv` | 64 spaces: RBS discussion/meeting rooms; E2/E6 wayfinder study spaces; W1 library open study / commons / hubs; Foodgle Hub (E4 L1) and Wholesome by Food Canopy (W3 L2) |
| `sample/events.csv` | Demo campus `event` rows (`location_id` must exist). Titles are original; not copied official listings. |
| `sample/occupancy_preview.csv` | Dummy fallback (`source = dummy`) for **all** catalogue ids, 29 Sep 08:00–20:00 |
| `sample/occupancy_generated.csv` | AY2026/27 Trimester 1 hourly occupancy, 31 Aug–27 Dec 2026, 08:00–20:00 `+08:00` (`source = generated`; 1,547 hours × 64 locations) |
| `sample/occupancy_prediction.csv` | Sample two hours after `predict_as_of` (29 Sep 16:00–17:00), one row per location, `model_version = v0`. Map forecast uses `GET /occupancy/{id}/prediction?at=` on the generated series. |
| `sample/sit_calendar.json` | AY2026/27 Trimester 1 overlay; E = IT courses; W3/W5 = other courses; W1 library shared |

`init_app_db.py` prefers generated occupancy over the dummy preview and loads the **full Trimester 1 series** (for timeline / date filters). Rebuild with `python src/db/init_app_db.py`. Open CSVs in a text editor or the API — Excel often shows `00:00` and drops the hour. Heatmap should request a teaching instant (`?at=`), not the last row in the file.
