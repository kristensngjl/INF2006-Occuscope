# Data dictionary

Column names as inspected from files in `data/raw/` (2026-09-23). How to obtain those files, and which CSVs seed the app DB: `data/README.md`.

Occuscope trains on two real NUS datasets. Neither is a live SIT Punggol sensor feed. “Current” occupancy on the map is generated; that limitation is also in the root README.

## Source 1: ROBOD (Room-level Occupancy and Building Operation Dataset)

- Local files: `data/raw/combined_Room1.csv` … `combined_Room5.csv`
- Provenance: Figshare DOI 10.6084/m9.figshare.19234530; GitHub https://github.com/ideas-lab-nus/robod
- Coverage: NUS SDE4, 5 rooms. Room 1–2 lecture (8,352 rows each), Room 3 office (8,352), Room 4 office (13,536), Room 5 library (13,536)
- Interval: 5 minutes. `timestamp` format `YYYY-MM-DD HH:MM +08:00` (Singapore)
- Room is **the filename**, not a column
- Cite: Tekler et al., Building Simulation 2022, https://doi.org/10.1007/s12273-022-0925-9

Inspected columns used for ML (same names in every room file):

| Field | Type | Description |
|---|---|---|
| timestamp | datetime | Reading time, 5-min, UTC+8 |
| occupant_count | int | Ground-truth occupant count (target) |
| occupant_presence | int | 0/1 occupied |
| wifi_connected_devices | float | Wi-Fi devices in the room |
| indoor_co2 | float | Indoor CO2 |
| air_temperature | float | Indoor air temperature |
| indoor_relative_humidity | float | Indoor RH |

Also present (HVAC/weather; rooms 1–2 use FCU fields, rooms 3–5 use AHU fields): `voc`, `sound_pressure_level`, `illuminance`, `pm2.5`, energy columns, setpoints, outdoor weather. Not required for a first occupancy model.

Quick occupancy check: Room1 max 38, Room2 22, Room3 13, Room4 18, Room5 16. Means are low because nights are empty. Cleaned extract: `data/processed/robod_clean.csv` (52,128 rows). ROBOD in this dump is **weekdays only**.

## Source 2: NUS Wi-Fi floor counts

- Local files: `data/raw/raw_data.xlsx`, `perturbed_data.xlsx`, `ordinary_data.xlsx`
- Provenance: Zenodo https://zenodo.org/records/17578240 DOI 10.5281/zenodo.17578240
- Coverage: one NUS academic building, floors **L2–L6**, 8 Jan 2018 – 30 Dec 2018
- Licence: **CC BY 4.0** (credit Wang / DeST Lab)
- Use **`raw_data.xlsx` sheet `5min`** as the real series. Other sheets are the same data resampled (10min … 24h). `perturbed_data.xlsx` is noise-added (their paper). `ordinary_data.xlsx` is a tiny synthetic toy (Constant/Linear/Sine) — skip for training.

| Field | Type | Description |
|---|---|---|
| time | datetime | Reading time |
| L2 | int | Occupant/Wi-Fi count, floor 2 |
| L3 | int | Floor 3 |
| L4 | int | Floor 4 |
| L5 | int | Floor 5 |
| L6 | int | Floor 6 |

`5min` sheet: 102,816 rows. These are floor totals, not rooms, and Wi-Fi-derived (not ROBOD camera/ground-truth).

## Two stores (do not mix)

1. **Training files** — `data/raw/` ROBOD + NUS Wi-Fi. Pandas/notebooks only. Never copied into the app DB.
2. **App database** — `data/occuscope.db` locally (`src/db/schema.sql`), later RDS. SIT buildings/locations, generated occupancy, events, predictions.

`python src/db/init_app_db.py` rebuilds (2) from `data/sample/`. After the model exists, replace dummy occupancy with generated SIT series.

## App schema (`src/db/schema.sql`)

Campus is a field on `building` (always `SIT Punggol` for now). Floor is an integer on `location`, not its own table. Crowd bands are **views**, not columns.

**building** — `building_id` (PK), `name`, `campus`, `map_x`, `map_y`

**location** — `location_id` (PK), `building_id` (FK), `floor`, `name`, `type` (`library` | `discussion_room` | `lecture_theatre` | `food_court` | `office` | `other`), `capacity`, `map_x`, `map_y`. Unique `(building_id, floor, name)`.

**occupancy** — `reading_id` (PK), `location_id` (FK), `timestamp` (ISO-8601), `occupancy_count` (≥ 0, may exceed capacity), `source` (`dummy` | `generated` | `model`). Unique `(location_id, timestamp)`.

**occupancy_prediction** — `prediction_id` (PK), `location_id` (FK), `predicted_for`, `occupancy_count`, `model_version`, `created_at`

**event** — `event_id` (PK), `location_id` (FK), `title`, `description`, `start_time`, `end_time` (`end_time > start_time`)

**app_user** — `user_id` (PK), `email` (unique), `role` (`student` | `staff` | `admin`) — empty until Ryan adds auth

**v_occupancy_current** — latest reading + `occupancy_ratio` + `crowd_level` (`quiet` ≤30%, `moderate` ≤70%, else `crowded`)

**v_floor_type_summary** — counts of quiet/moderate/crowded per building + floor + type (discussion rooms on a floor)

## Limitations

- ROBOD and the NUS Wi-Fi floor counts reflect real NUS buildings' patterns, not SIT Punggol's absolute numbers or layout — used to train the prediction model's time-of-day / day-of-week / floor-load shape, not as ground truth for our campus.
- Live "current" occupancy shown on the Occuscope map for SIT locations is synthetic (generated) data, since no real live sensor feed exists for our campus — stated plainly in the report.
