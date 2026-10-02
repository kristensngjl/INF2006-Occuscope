# Analytics

Occupancy modelling for Occuscope (data / ML).

The pipeline trains on **NUS ROBOD** room-level `occupant_count` (optional NUS Wi-Fi floor series remain available, sheet `5min`). Models are compared on held-out **NUS** dates (MAE, RMSE, R²). Predicted utilisation is then mapped onto SIT `location.capacity` and written as generated application rows. There are **no SIT labels**; Punggol accuracy is not reported.

## Reproduce

Training files in `data/raw/` are **not in the ZIP**. Download them only if you need to rebuild `robod_clean.csv` (`02_clean_robod.py`) or the C5 Wi-Fi table. This workspace trained v0 on Python 3.11.9. Package pins are in `requirements.txt` (`random_state=42` in train and EDA sample). Markers can run `04_train.py` / `06_holdout_diagnostics.py` from committed `data/processed/robod_clean.csv`.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r analytics/requirements.txt
python analytics/02_clean_robod.py
python analytics/03_eda_robod.py
python analytics/04_train.py
python analytics/06_holdout_diagnostics.py
python analytics/05_generate_sit.py
python src/db/init_app_db.py
```

| Script | Role |
|---|---|
| `01_eda.py` | Dummy SIT occupancy fallback (`source = dummy`) |
| `02_clean_robod.py` | HVAC-stripped ROBOD table → `data/processed/robod_clean.csv` |
| `03_eda_robod.py` | Figures in `analytics/figures/` |
| `04_train.py` | Date hold-out; `metrics_holdout.csv`; `metrics_wifi_ablation.csv`; `models/occupancy_v0.joblib` |
| `05_generate_sit.py` | SIT occupancy and two-hour forecasts using v0 and `sit_calendar.json` |
| `06_holdout_diagnostics.py` | NUS extras: MAE by type/hour, 7 vs 14-day window, persist vs v0, crowd-band counts |
| `occupancy_model.py` | Shared v0 predictor and SIT→ROBOD type map (required to unpickle) |

Academic overlay (generate time only): AY2026/27 Trimester 1 dates from the SIT academic calendar; East blocks = IT courses; W3/W5 = other courses; W1 library shared.

## Marker outputs

| Artefact | Status |
|---|---|
| Inspected columns in `data/DATA_DICTIONARY.md` | Done |
| Cleaned ROBOD table and EDA figures | Done |
| Baseline versus Ridge versus Random Forest on NUS hold-out | Done (`metrics_holdout.csv`; hour × type mean wins MAE) |
| Wi-Fi ablation (room Wi-Fi vs floor `5min`; not in app DB) | Done (`metrics_wifi_ablation.csv`; room Wi-Fi helps NUS MAE; v0 still no Wi-Fi) |
| Generated `occupancy` and sample `occupancy_prediction` for all 64 SIT location ids | `occupancy_generated.csv`, `occupancy_prediction.csv` |
| MAE slices, 7 vs 14-day window, persist vs v0, NUS band counts | Done (`metrics_mae_by_type_hour.csv`, `metrics_holdout_window.csv`, `metrics_persist_vs_v0.csv`, `metrics_nus_crowd_bands.csv`) |

Model files belong in `analytics/models/` (gitignored until a small evaluated artefact is chosen for the submission ZIP).
