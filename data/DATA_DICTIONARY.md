# Data dictionary

Column names as inspected from files in `data/raw/` (23 September 2026). How to obtain those files, and which CSVs seed the application database, is described in `data/README.md`.

Occuscope trains on two identified NUS datasets. Neither is a live SIT Punggol sensor feed. Occupancy shown on the map is generated; that limitation is also stated in the root README.

## Source 1: ROBOD (Room-level Occupancy and Building Operation Dataset)

- Local files: `data/raw/combined_Room1.csv` … `combined_Room5.csv`
- Provenance: Figshare DOI 10.6084/m9.figshare.19234530; GitHub https://github.com/ideas-lab-nus/robod
- Coverage: NUS SDE4, five rooms. Rooms 1–2 lecture (8,352 rows each); Room 3 office (8,352); Room 4 office (13,536); Room 5 library (13,536)
- Interval: 5 minutes. `timestamp` format `YYYY-MM-DD HH:MM +08:00` (Singapore)
- Room identity is the **filename**, not a column
- Citation: Tekler et al., *Building Simulation* 2022, https://doi.org/10.1007/s12273-022-0925-9

Inspected columns used for modelling (same names in every room file):

| Field | Type | Description |
|---|---|---|
| timestamp | datetime | Reading time, 5-minute interval, UTC+8 |
| occupant_count | int | Ground-truth occupant count (training target) |
| occupant_presence | int | Occupied indicator (0/1) |
| wifi_connected_devices | float | Wi-Fi associated devices in the room |
| indoor_co2 | float | Indoor carbon dioxide |
| air_temperature | float | Indoor air temperature |
| indoor_relative_humidity | float | Indoor relative humidity |

Also present (HVAC and weather; rooms 1–2 use FCU fields, rooms 3–5 use AHU fields): `voc`, `sound_pressure_level`, `illuminance`, `pm2.5`, energy columns, setpoints, outdoor weather. These are omitted from the occupancy model.

Occupancy ranges in the extract: Room 1 maximum 38; Room 2, 22; Room 3, 13; Room 4, 18; Room 5, 16. Means are low because overnight hours are empty. Cleaned table: `data/processed/robod_clean.csv` (52,128 rows). This dump contains **weekdays only**.

## Source 2: NUS Wi-Fi floor counts

- Local files: `data/raw/raw_data.xlsx`, `perturbed_data.xlsx`, `ordinary_data.xlsx`
- Provenance: Zenodo https://zenodo.org/records/17578240, DOI 10.5281/zenodo.17578240
- Coverage: one NUS academic building, floors **L2–L6**, 8 January 2018 – 30 December 2018
- Licence: **CC BY 4.0** (credit Wang / DeST Lab)
- Use **`raw_data.xlsx` sheet `5min`** as the observed series. Other sheets are the same data resampled. `perturbed_data.xlsx` is noise-added. `ordinary_data.xlsx` is a synthetic toy series and is not used for training.

| Field | Type | Description |
|---|---|---|
| time | datetime | Reading time |
| L2 … L6 | int | Floor-level count (Wi-Fi derived) |

Sheet `5min`: 102,816 rows. These are floor totals, not rooms, and are not ROBOD camera ground truth. Unused in occupancy v0.

## Two stores

1. **Training files** — `data/raw/` (ROBOD and NUS Wi-Fi). Analytics only. Never copied into the application database.
2. **Application database** — `data/occuscope.db` locally (`src/db/schema.sql`), later RDS. SIT buildings, locations, generated occupancy, events, predictions.

`python src/db/init_app_db.py` rebuilds (2) from `data/sample/`. Occupancy prefers `occupancy_generated.csv` over the dummy preview.

**SIT type → ROBOD type** (`analytics/occupancy_model.py`): discussion_room → office; library → library; lecture_theatre → lecture; food_court → library; office → office.

**Academic calendar overlay** (`data/sample/sit_calendar.json`): applied only when generating SIT rows. Teaching, recess (week 7), final assessment, and trimester break follow [SIT AY2026/27 Trimester 1](https://www.singaporetech.edu.sg/admissions/undergraduate/academic-calendar-sit-and-joint-programmes). Campus assignment used for IWSP mix: East blocks (E2, E6) = IT courses; W3 and W5 = other courses; **W1 library is shared** (open study and meeting rooms are not placed on the course split). OIP duration (three weeks) is published for Computing Science; 2026 dates are not, so that window is disabled. `init_app_db.py` seeds occupancy up to `map_as_of`.

## Application schema (`src/db/schema.sql`)

Campus is a field on `building` (`SIT Punggol`). Floor is an integer on `location`. Crowd bands are computed in **views**, not stored columns.

**building** — `building_id` (PK), `name`, `campus`, `map_x`, `map_y`

**location** — `location_id` (PK), `building_id` (FK), `floor`, `name`, `type` (`library` | `discussion_room` | `lecture_theatre` | `food_court` | `office` | `other`), `capacity`, `map_x`, `map_y`. Unique `(building_id, floor, name)`.

**occupancy** — `reading_id` (PK), `location_id` (FK), `timestamp` (ISO-8601), `occupancy_count` (≥ 0; may exceed capacity), `source` (`dummy` | `generated` | `model`). Unique `(location_id, timestamp)`.

**occupancy_prediction** — `prediction_id` (PK), `location_id` (FK), `predicted_for`, `occupancy_count`, `model_version`, `created_at`

**event** — `event_id` (PK), `location_id` (FK), `title`, `description`, `start_time`, `end_time` (`end_time > start_time`)

**app_user** — `user_id` (PK), `email` (unique), `role` (`student` | `staff` | `admin`) — unused until authentication is added

**v_occupancy_current** — latest reading, `occupancy_ratio`, `crowd_level` (quiet ≤ 0.30, moderate ≤ 0.70, otherwise crowded)

**v_floor_type_summary** — quiet / moderate / crowded counts per building, floor, and type

## Limitations

- ROBOD and NUS Wi-Fi counts describe NUS buildings. They are used for temporal and type shape, not as ground truth for SIT Punggol.
- Occupancy shown on the map is generated because no live campus sensor feed is available.
- Recess and examination effects follow the published SIT calendar (subject to change). IWSP reductions are a programme mix overlay, not live bookings. OIP dates for 2026 are not public.
