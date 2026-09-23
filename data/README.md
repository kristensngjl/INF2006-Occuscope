# Data

Two kinds of data live here. Do not mix them.

| Kind | Where | Goes in `occuscope.db`? |
|---|---|---|
| NUS training files (ROBOD CSVs, Wi-Fi xlsx) | `raw/` (gitignored) | No — pandas / `analytics/` only |
| Cleaned ROBOD | `processed/robod_clean.csv` (from `analytics/02_clean_robod.py`) | No |
| SIT seed + generated occupancy | `sample/` | Yes — `python src/db/init_app_db.py` |
| Local app database | `occuscope.db` (gitignored, generated) | This file is the DB |

Field-level names, licences, and app tables: **`DATA_DICTIONARY.md`**.

## Getting the training files

**ROBOD** — on [ideas-lab-nus/robod](https://github.com/ideas-lab-nus/robod) use **Code → Download ZIP**, then copy `Data/combined_Room1.csv` … `combined_Room5.csv` into `data/raw/`.

**NUS Wi-Fi floors** — [zenodo.org/records/17578240](https://zenodo.org/records/17578240) (CC BY 4.0). Put `raw_data.xlsx` (and the other two xlsx if downloaded) in `data/raw/`. Train on sheet `5min` only.

Do not `git add` `data/raw/`.

## Sample files (committed)

| File | Seeds |
|---|---|
| `sample/buildings.csv` | `building` |
| `sample/locations.csv` | `location` |
| `sample/events.csv` | `event` |
| `sample/occupancy_preview.csv` | `occupancy` (written by `analytics/01_eda.py`, `source = dummy`) |

After the occupancy model exists, replace the dummy preview with generated SIT series and re-run `init_app_db.py`.
