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

SIT room catalogue uses Room Booking System **display names only** (screenshots; not a live scrape). Discussion-room identifiers follow `{block}-{floor}-{unit}-DR{n}` (for example `E2-03-07-DR209`). Library meeting rooms use `{block}-{floor}-{unit}-MR{n}` in W1. Capacity is inferred from furniture in the photographs (four-seat round tables = 4; long tables = 8) unless confirmed. **W5 discussion rooms copy the W3 floor/unit layout; identifiers continue DR06–DR09** (`W5-03-07-DR06` … `W5-04-04-DR09`) and were not taken from an RBS screenshot.

| File | Role |
|---|---|
| `sample/buildings.csv` | E2, E6, W1 (library), W3, W5 |
| `sample/locations.csv` | Block discussion rooms, library meeting rooms, L4 open study, media studio |
| `sample/events.csv` | `event` rows (`location_id` must exist) |
| `sample/occupancy_preview.csv` | Dummy fallback (`source = dummy`) |
| `sample/occupancy_generated.csv` | Generated occupancy (`source = generated`) |
| `sample/occupancy_prediction.csv` | Next two hours per location, `model_version = v0` |
| `sample/sit_calendar.json` | AY2026/27 Trimester 1 overlay; E = IT courses; W3/W5 = other courses; W1 library shared |

`init_app_db.py` prefers generated occupancy over the dummy preview, and seeds readings only up to `map_as_of` so the current-occupancy view is a teaching weekday. Rebuild with `python src/db/init_app_db.py`, then read `building`, `location`, `v_occupancy_current`, and `occupancy_prediction`.
