# Data Dictionary

Occuscope trains its prediction model on two real NUS datasets. Neither is a live SIT Punggol sensor feed — both feed offline training; live "current" occupancy for SIT locations is synthetic (generated) data, stated as a limitation in the report.

## Source 1: ROBOD (Room-level Occupancy and Building Operation Dataset)

- Provenance: published open via Figshare, DOI 10.6084/m9.figshare.19234530; repo: https://github.com/ideas-lab-nus/robod
- Coverage: 5 spaces (2 lecture rooms, 2 offices, 1 library) in one NUS building
- Interval: 5 minutes, 181 days
- Licence: open / CC — confirm exact terms from the Figshare page before submission

| Field | Type | Description |
|---|---|---|
| timestamp | datetime | Reading time, 5-min resolution |
| space_id | string | Which of the 5 monitored spaces |
| occupant_count | int | Ground-truth occupant count |
| wifi_device_count | int | Wi-Fi devices detected in the space |
| temperature | float | Indoor temperature |
| humidity | float | Indoor humidity |
| co2 | float | CO2 level |
| energy_hvac | float | HVAC energy use |
| energy_lighting | float | Lighting energy use |

TODO: replace with the exact column names once the raw file is downloaded and inspected.

## Source 2: NUS Wi-Fi floor counts

- Provenance: Zenodo, https://zenodo.org/records/17578240
- Coverage: 5 floors, NUS building
- Interval: 5 minutes, full year (2018)
- Licence: confirm exact terms from the Zenodo record before submission

| Field | Type | Description |
|---|---|---|
| timestamp | datetime | Reading time, 5-min resolution |
| floor_id | string | Which of the 5 monitored floors |
| wifi_device_count | int | Wi-Fi devices detected on the floor |

TODO: replace with the exact column names once the raw file is downloaded and inspected.

## Derived schema (Occuscope database)

The prediction model is trained on the two sources above; the live app database holds these tables (see also `project_manifest.yaml` → `architecture.components`):

**LOCATION** — `location_id` (PK), `building`, `floor`, `name`, `type`, `capacity`, `map_position`

**OCCUPANCY** — `reading_id` (PK), `location_id` (FK), `timestamp`, `occupancy_count`

**EVENT** — `event_id` (PK), `location_id` (FK), `title`, `description`, `start_time`, `end_time`

**USER** (if login is added) — `user_id` (PK), `email`, `role`

## Limitations

- ROBOD and the NUS Wi-Fi floor counts reflect real NUS buildings' patterns, not SIT Punggol's absolute numbers or layout — used to train the prediction model's time-of-day / day-of-week / floor-load shape, not as ground truth for our campus.
- Live "current" occupancy shown on the Occuscope map for SIT locations is synthetic (generated) data, since no real live sensor feed exists for our campus — stated plainly in the report.
