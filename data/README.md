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

Do not `git add` `data/raw/`.

## Sample files (committed)

SIT room catalogue uses Room Booking System **display names only** (screenshots; not a live scrape). Discussion-room identifiers follow `{block}-{floor}-{unit}-DR{n}` (for example `E2-03-07-DR209`). Library meeting rooms use `{block}-{floor}-{unit}-MR{n}` in W1. Capacity is inferred from furniture in the photographs (four-seat round tables = 4; long tables = 8) unless confirmed. Catalogue captured: E2 L3/L4 (DR209–210, 215–216, 223–224); E6 L4 (DR303–307); W3 L3/L4/L6–L8 (DR02–DR17); W5 L3/L5/L7/L8 (DR18–DR20, DR23–DR26). RBS had no DR21/DR22 cards in that screenshot — those ids are not invented.

| File | Role |
|---|---|
| `sample/buildings.csv` | E2, E6, W1 (library), W3, W5 |
| `sample/locations.csv` | Block discussion rooms, library meeting rooms, L4 open study, media studio |
| `sample/events.csv` | `event` rows (`location_id` must exist) |
| `sample/occupancy_preview.csv` | Dummy fallback (`source = dummy`) |
| `sample/occupancy_generated.csv` | AY2026/27 Trimester 1 hourly occupancy, 31 Aug–27 Dec 2026, `+08:00` (`source = generated`) |
| `sample/occupancy_prediction.csv` | Next two hours per location, `model_version = v0` |
| `sample/sit_calendar.json` | AY2026/27 Trimester 1 overlay; E = IT courses; W3/W5 = other courses; W1 library shared |

`init_app_db.py` prefers generated occupancy over the dummy preview and loads the **full Trimester 1 series** (for timeline / date filters). Rebuild with `python src/db/init_app_db.py`. Open CSVs in a text editor or the API — Excel often shows `00:00` and drops the hour. Heatmap should request a teaching instant (`?at=`), not the last row in the file.
