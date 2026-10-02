# Objective

Demonstrate that identified NUS occupancy data can be cleaned, that a leakage-safe forecast can be trained and compared with a baseline, and that Quiet / Moderate / Crowded bands for SIT locations can be generated from that model. SIT values are not labelled.

# Setup

Python 3.11+, `pip install -r analytics/requirements.txt`. Training recorded on Python 3.11.9. The ZIP **does not include** `data/raw/` (ROBOD CSVs and the Wi-Fi workbook). A marker can replay `04_train.py` and `06_holdout_diagnostics.py` from committed `data/processed/robod_clean.csv` plus the metrics tables. Rebuilding that clean file, or the C5 floor-Wi-Fi join, needs the Figshare/Zenodo downloads locally (`data/README.md`). `occupancy_v0.joblib` is gitignored; re-run `04_train.py` if generate must be rebuilt.

# Command / steps

```
python analytics/02_clean_robod.py
python analytics/03_eda_robod.py
python analytics/04_train.py
python analytics/06_holdout_diagnostics.py
python analytics/05_generate_sit.py
python tests/test_crowd_and_seed.py
python src/db/init_app_db.py
```

# Expected result

Cleaned ROBOD table, exploratory figures, hold-out MAE/RMSE, generated SIT occupancy for AY2026/27 Trimester 1, and two-hour predictions. Recess week 7 and MOM public holidays should reduce utilisation. East-block (IT) discussion rooms quieter than W3/W5. Demo campus events apply mixed turnout on overlapping hours.

# Actual result

## Command logs (1 October 2026, Lideon)

Re-ran from the repository root on Python 3.11.9. `data/raw/` is gitignored. Markers can replay hold-out metrics from `data/processed/robod_clean.csv`. Generate still needs `occupancy_v0.joblib` or a local `04_train.py` run.

| Command | Log |
|---|---|
| `python analytics/04_train.py` | `evidence/train-holdout-local.txt` |
| `python analytics/05_generate_sit.py` | `evidence/generate-sit-local.txt` |
| `python analytics/06_holdout_diagnostics.py` | `evidence/holdout-diagnostics-local.txt` |
| `python tests/test_crowd_and_seed.py` | `evidence/crowd-and-seed-local.txt` |

Frontend **Follow Singapore time** snaps `?at=` to the Singapore clock inside the seeded window. Occupancy rows remain `source=generated`. That control is not live Punggol sensors.

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

## Hold-out diagnostics (1 October 2026, Lideon)

`python analytics/06_holdout_diagnostics.py` → `analytics/metrics_mae_by_type_hour.csv`, `metrics_holdout_window.csv`, `metrics_persist_vs_v0.csv`, `metrics_nus_crowd_bands.csv`. Log: `evidence/holdout-diagnostics-local.txt`. NUS only; not SIT accuracy.

**MAE by room type (v0, 14-day hold-out):** lecture 2.04, library 1.60, office 1.56. **By hour:** overnight MAE is near 0 (empty rooms); 15:00 MAE is 4.93 (peak is harder).

**7 vs 14-day window (v0 refit):** 14-day MAE 1.74 (15 Nov–23 Dec 2021); 7-day MAE 1.73 (15–23 Dec). MAE is stable; R² stays slightly negative.

**Next 1h / 2h:** copying the same room’s count from 1 hour earlier (persist) MAE 0.83 / 0.89. v0 MAE ~1.76 / 1.78 on those rows. Persist wins on NUS because occupancy is smooth at 5-minute resolution. SIT has **no last reading**, so the map still uses generated v0+calendar hours, not persist. That is a limitation, not a reason to claim live tracking.

**Crowd bands on NUS hold-out** (people ÷ that room’s train 95th percentile; Quiet ≤30% / Moderate ≤70%): at 08:00, 99% Quiet and 0% Crowded; at 15:00, Quiet 52% / Moderate 20% / Crowded 28%. The cut-offs match empty morning vs mixed afternoon. Not an F1 on SIT.

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
- Ratio = v0 count / ROBOD type 95th percentile × calendar × event overlap × SIT capacity × per-room mix (1 Oct 2026: same-type rooms are no longer identical at peak hour).
- Calendar: [SIT AY2026/27 Trimester 1](https://www.singaporetech.edu.sg/admissions/undergraduate/academic-calendar-sit-and-joint-programmes). East = IT courses; W3/W5 = other courses; W1 library shared. Demo campus events (not official listings). OIP disabled. Timestamps include `+08:00`.

**Example (Wednesday 30 September 2026, 15:00 SGT):**

| Location | Count | Capacity | Ratio | Band |
|---|---|---|---|---|
| `W3-03-07-DR02` | 2 | 8 | 0.25 | quiet |
| `E2-03-07-DR209` (IT / East) | 3 | 8 | 0.375 | moderate |
| `W3-03-10-DR03` | 6 | 8 | 0.75 | crowded |
| `W1-04-OPEN` (library) | 15 | 80 | 0.188 | quiet |

## Overlay checks (1 October 2026, Lideon)

Same generated CSV as `05_generate_sit.py` (99,008 rows, 64 locations). Quiet ≤30% / Moderate ≤70% / Crowded otherwise. After `python src/db/init_app_db.py`, `GET /occupancy/current?at=` reads these counts (not `MAX(timestamp)`). `booked` is joined from demo `room_booking` and is mixed with occupancy (booked+people, no-shows, walk-ins, empty available).

| Check | Instant | Where | Expected | Actual | Artefact |
|---|---|---|---|---|---|
| Peak-hour mix | `2026-09-30T15:00:00+08:00` | 45 discussion rooms | At least 3 distinct counts and 2 crowd bands (v0 alone would clone hour×type) | 6 distinct counts; quiet 9 / moderate 28 / crowded 8 | `data/sample/occupancy_generated.csv`; `tests/test_crowd_and_seed.py`; `evidence/generate-sit-local.txt`; `evidence/crowd-and-seed-local.txt` |
| Creative Trail overlap | Wed 2 Sep 15:00 vs Wed 9 Sep 15:00 (trail overlaps `W1-04-OPEN` 4 Sep–16 Oct) | `W1-04-OPEN` | Event turnout is mixed (not a flat 1.25 bump) | Counts still differ by day via mix/jitter/turnout | `data/sample/events.csv` `E-001`; `occupancy_generated.csv` |
| Public holiday | Mon 9 Nov 15:00 (Deepavali in lieu) vs Mon 16 Nov 15:00 teaching | `W3-03-07-DR02`; `W1-04-OPEN` | Holiday multiplier 0.18 → lower counts | DR02: 0 vs 3; library: 2 vs 14 | `data/sample/sit_calendar.json`; `occupancy_generated.csv` |

API join example after seed: `GET /occupancy/current?at=2026-09-30T15:00:00+08:00` (`src/api-contract.md`).

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
- `evidence/train-holdout-local.txt`
- `evidence/generate-sit-local.txt`
- `analytics/06_holdout_diagnostics.py`
- `analytics/metrics_mae_by_type_hour.csv`
- `analytics/metrics_holdout_window.csv`
- `analytics/metrics_persist_vs_v0.csv`
- `analytics/metrics_nus_crowd_bands.csv`
- `evidence/holdout-diagnostics-local.txt`
- `evidence/crowd-and-seed-local.txt`

# Limitations

NUS ROBOD is not SIT Punggol; this ROBOD extract is weekdays only; Wi-Fi counts are not people; map occupancy is generated; following the Singapore clock only chooses a generated hour; last-hour persist beats v0 on NUS short horizons but SIT has no live last reading; per-room mix at generate time is not live RBS; recess and examination dates follow the public SIT calendar (subject to change); IWSP is a programme mix rather than a room roster; OIP dates for 2026 are not public.
