# Objective

Demonstrate that identified NUS occupancy data can be cleaned, that a leakage-safe forecast can be trained and compared with a baseline, and that Quiet / Moderate / Crowded bands for SIT locations can be generated from that model. SIT values are not labelled.

# Setup

Python 3.11+, `pip install -r analytics/requirements.txt`, ROBOD CSVs under `data/raw/`. Training recorded on Python 3.11.9. `04_train.py` also writes the Wi-Fi ablation table when `raw_data.xlsx` sheet `5min` is present.

# Command / steps

```
python analytics/02_clean_robod.py
python analytics/03_eda_robod.py
python analytics/04_train.py
python analytics/05_generate_sit.py
python src/db/init_app_db.py
```

# Expected result

Cleaned ROBOD table, exploratory figures, hold-out MAE/RMSE, generated SIT occupancy for AY2026/27 Trimester 1, and two-hour predictions. Recess week 7 and MOM public holidays should reduce utilisation. East-block (IT) discussion rooms quieter than W3/W5. ArtFest sample events raise overlapping library hours.

# Actual result

## Exploratory analysis (24 September 2026, Lideon)

- 52,128 rows, 7 September 2021 to 23 December 2021, 5-minute ticks, Singapore time.
- Rooms: R1–R2 lecture, R3–R4 office, R5 library. HVAC and weather columns dropped.
- No weekend rows (Monday–Friday only).
- Means are low because overnight hours are empty. Peak around 15:00 SGT.
- Correlation of Wi-Fi connected devices with `occupant_count` ≈ 0.69. Ablation (30 Sep 2026): room Wi-Fi lowers NUS MAE (~1.31 vs 1.74) but is unused in v0; SIT has no corresponding feed.

## Training / hold-out (26 September 2026, Lideon)

- Features: `hour`, `day_of_week`, `room_type` (transferable to SIT).
- Split: last 14 days (15 November 2021 – 23 December 2021) held out by **date**, not by shuffled rows.
- Training: 34,560 rows; test: 17,568 rows.

| Model | MAE | RMSE | R² |
|---|---|---|---|
| Baseline (mean by hour × room type) | 1.74 | 2.92 | −0.04 |
| Ridge | 1.83 | 2.86 | 0.01 |
| Random Forest | 1.84 | 3.06 | −0.14 |

**Selected model (lowest MAE on transferable features): hour × room-type mean.** Ridge and Random Forest did not improve MAE without Wi-Fi. Negative R² indicates that the hold-out period is a different occupancy regime from training (late term / examinations). Version v0 is therefore that lookup table. It remains usable to generate SIT utilisation ratios.

## Wi-Fi ablation (30 September 2026, Lideon)

Same date hold-out. Extra features are **not** in v0 and **not** loaded into `occuscope.db` (SIT has no matching feed).

| Features | Best MAE |
|---|---|
| hour + weekday + type (v0) | 1.74 (mean lookup) |
| + ROBOD `wifi_connected_devices` | 1.31 (Ridge) |
| + Zenodo `5min` L2–L6 mean by hour×weekday (2018, different building) | 1.77 (RF) — does **not** beat v0 |
| + room Wi-Fi and floor profile | 1.28 (RF) |

Room-level Wi-Fi **does** help on NUS. The 2018 floor series by itself does not. v0 stays the hour×type mean so SIT generate does not invent a Wi-Fi sensor.

SIT map occupancy is generated (`source = generated`). Series: 31 August–27 December 2026 (Trimester 1).

## Generation / academic overlay (29 September 2026, Lideon)

- Type map: discussion_room → office; library → library (`occupancy_model.py`).
- Ratio = v0 count / ROBOD type 95th percentile × calendar × event overlap × SIT capacity.
- Calendar: [SIT AY2026/27 Trimester 1](https://www.singaporetech.edu.sg/admissions/undergraduate/academic-calendar-sit-and-joint-programmes). East = IT courses; W3/W5 = other courses; W1 library shared. ArtFest sample events. OIP disabled. Timestamps include `+08:00`.

**Example (Wednesday 30 September 2026, 15:00 SGT):**

| Location | Count | Capacity | Ratio | Band |
|---|---|---|---|---|
| `W1-04-OPEN` (library + ArtFest sample) | 70 | 80 | 0.875 | crowded |
| `E2-03-07-DR209` (IT courses, East) | 3 | 8 | 0.375 | moderate |
| `W3-03-07-DR02` (other courses, W3) | 5 | 8 | 0.625 | moderate |

# Artefact path

- `data/processed/robod_clean.csv`
- `analytics/figures/robod_*.png`
- `analytics/04_train.py`, `analytics/05_generate_sit.py`, `analytics/occupancy_model.py`
- `analytics/metrics_holdout.csv`
- `analytics/metrics_wifi_ablation.csv`
- `analytics/models/occupancy_v0.joblib` (local; gitignored)
- `data/sample/sit_calendar.json`
- `data/sample/occupancy_generated.csv`
- `data/sample/occupancy_prediction.csv`
- `analytics/02_clean_robod.py`, `analytics/03_eda_robod.py`

# Limitations

NUS ROBOD is not SIT Punggol; this ROBOD extract is weekdays only; Wi-Fi counts are not people; map occupancy is generated; recess and examination dates follow the public SIT calendar (subject to change); IWSP is a programme mix rather than a room roster; OIP dates for 2026 are not public.
