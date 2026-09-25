# Objective

Demonstrate that identified NUS occupancy data can be cleaned, that a leakage-safe forecast can be trained and compared with a baseline, and that Quiet / Moderate / Crowded bands for SIT locations can be generated from that model. SIT values are not labelled.

# Setup

Python 3.11+, `pip install -r analytics/requirements.txt`, ROBOD CSVs under `data/raw/`. Training recorded on Python 3.11.9.

# Command / steps

```
python analytics/02_clean_robod.py
python analytics/03_eda_robod.py
python analytics/04_train.py
python analytics/05_generate_sit.py
python src/db/init_app_db.py
```

# Expected result

Cleaned ROBOD table, exploratory figures, hold-out MAE/RMSE, generated SIT occupancy (`source = generated`), and two-hour predictions. Recess week 7 (12–18 October 2026) should reduce discussion-room utilisation. East-block (IT course) discussion rooms should be quieter than W3/W5 (other courses). W1 library should remain a shared pattern. The selected model is written to `analytics/models/occupancy_v0.joblib`.

# Actual result

## Exploratory analysis (24 September 2026, Lideon)

- 52,128 rows, 7 September 2021 to 23 December 2021, 5-minute ticks, Singapore time.
- Rooms: R1–R2 lecture, R3–R4 office, R5 library. HVAC and weather columns dropped.
- No weekend rows (Monday–Friday only).
- Means are low because overnight hours are empty. Peak around 15:00 SGT.
- Correlation of Wi-Fi connected devices with `occupant_count` ≈ 0.69 (not used in v0; SIT has no corresponding feed).

## Training / hold-out (26 September 2026, Lideon)

- Features: `hour`, `day_of_week`, `room_type` (transferable to SIT).
- Split: last 14 days (15 November 2021 – 23 December 2021) held out by **date**, not by shuffled rows.
- Training: 34,560 rows; test: 17,568 rows.

| Model | MAE | RMSE | R² |
|---|---|---|---|
| Baseline (mean by hour × room type) | 1.74 | 2.92 | −0.04 |
| Ridge | 1.83 | 2.86 | 0.01 |
| Random Forest | 1.84 | 3.06 | −0.14 |

**Selected model (lowest MAE): hour × room-type mean.** Ridge and Random Forest did not improve MAE. Negative R² indicates that the hold-out period is a different occupancy regime from training (late term / examinations). Version v0 is therefore that lookup table. It remains usable to generate SIT utilisation ratios.

SIT map occupancy is generated (`source = generated`) as of 26 September 2026.

## Generation / academic overlay (26 September 2026, Lideon)

- Type map: discussion_room → office; library → library (`occupancy_model.py`).
- Ratio = v0 count / ROBOD type 95th percentile × calendar factors × SIT capacity.
- Calendar: [SIT AY2026/27 Trimester 1](https://www.singaporetech.edu.sg/admissions/undergraduate/academic-calendar-sit-and-joint-programmes). East blocks = IT courses; W3/W5 = other courses; W1 library shared. OIP window disabled (2026 dates not published).

**Example (Wednesday 23 September 2026, 15:00, study week 4):**

| Location | Count | Capacity | Ratio | Band |
|---|---|---|---|---|
| `W1-04-OPEN` (library, shared) | 56 | 80 | 0.70 | moderate |
| `E2-03-07-DR209` (IT courses, East) | 3 | 8 | 0.375 | moderate |
| `W3-03-07-DR02` (other courses, W3) | 5 | 8 | 0.625 | moderate |

**Recess week 7** (Wednesday 14 October 2026, 15:00): library 11/80 (quiet); discussion rooms round to 0. After recess (Wednesday 21 October 2026, 15:00) the week-4 pattern returns. **Final assessment** (Wednesday 2 December 2026, 15:00): library 48/80 moderate; discussion rooms 1/8 quiet.

# Artefact path

- `data/processed/robod_clean.csv`
- `analytics/figures/robod_*.png`
- `analytics/04_train.py`, `analytics/05_generate_sit.py`, `analytics/occupancy_model.py`
- `analytics/metrics_holdout.csv`
- `analytics/models/occupancy_v0.joblib` (local; gitignored)
- `data/sample/sit_calendar.json`
- `data/sample/occupancy_generated.csv`
- `data/sample/occupancy_prediction.csv`
- `analytics/02_clean_robod.py`, `analytics/03_eda_robod.py`

# Limitations

NUS ROBOD is not SIT Punggol; this ROBOD extract is weekdays only; Wi-Fi counts are not people; map occupancy is generated; recess and examination dates follow the public SIT calendar (subject to change); IWSP is a programme mix rather than a room roster; OIP dates for 2026 are not public.
