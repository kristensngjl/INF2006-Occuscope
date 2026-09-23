# Objective
Show that identified NUS occupancy data can be cleaned and understood well enough to later train a model whose outputs (Quiet / Moderate / Crowded) the API can serve for SIT locations.

# Setup
Python 3.11+, `pip install -r analytics/requirements.txt`, ROBOD CSVs under `data/raw/`.

# Command / steps
```
python analytics/02_clean_robod.py
python analytics/03_eda_robod.py
```

# Expected result
One cleaned table (`data/processed/robod_clean.csv`) and figures of occupancy vs hour, weekday, lecture vs library, and Wi-Fi vs count. Later: baseline vs model on held-out NUS timestamps (not done yet).

# Actual result
Ran 2026-09-24, Lideon.

- 52,128 rows, 2021-09-07 to 2021-12-23, 5-minute ticks, Singapore time.
- Rooms: R1–R2 lecture, R3–R4 office, R5 library. HVAC/weather columns dropped.
- **No weekend rows** (Mon–Fri only). Do not claim a weekend pattern from ROBOD.
- Mean occupant_count is low (lecture 1.41, library 1.87, office 2.65) because nights are empty. Peaks sit around 15:00 SGT (offices ~7 mean, library ~5.4, lecture ~5).
- `wifi_connected_devices` correlates with `occupant_count` at about 0.69 — usable as a feature, not as people.
- SIT “current” occupancy is still dummy until a model writes `source=generated`.

# Artefact path
- `data/processed/robod_clean.csv`
- `analytics/figures/robod_occupancy_by_hour.png`
- `analytics/figures/robod_by_weekday.png`
- `analytics/figures/robod_lecture_vs_library.png`
- `analytics/figures/robod_wifi_vs_occupancy.png`
- `analytics/02_clean_robod.py`, `analytics/03_eda_robod.py`
