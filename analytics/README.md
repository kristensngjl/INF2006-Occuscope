# Analytics

Occupancy modelling for Occuscope (data / ML).

The pipeline trains on **NUS ROBOD** room-level `occupant_count` (optional NUS Wi-Fi floor series remain available, sheet `5min`). Models are compared on held-out **NUS** dates (MAE, RMSE, R²). Predicted utilisation is then mapped onto SIT `location.capacity` and written as generated application rows. There are **no SIT labels**; Punggol accuracy is not reported.

## Reproduce

Training files must already be in `data/raw/` (see `data/README.md`). Do not commit them. This workspace trained v0 on Python 3.11.9.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r analytics/requirements.txt
python analytics/02_clean_robod.py
python analytics/03_eda_robod.py
python analytics/04_train.py
python analytics/05_generate_sit.py
python src/db/init_app_db.py
```

| Script | Role |
|---|---|
| `01_eda.py` | Dummy SIT occupancy fallback (`source = dummy`) |
| `02_clean_robod.py` | HVAC-stripped ROBOD table → `data/processed/robod_clean.csv` |
| `03_eda_robod.py` | Figures in `analytics/figures/` |
| `04_train.py` | Date hold-out; `metrics_holdout.csv`; `models/occupancy_v0.joblib` |
| `05_generate_sit.py` | SIT occupancy and two-hour forecasts using v0 and `sit_calendar.json` |
| `occupancy_model.py` | Shared v0 predictor and SIT→ROBOD type map (required to unpickle) |

Academic overlay (generate time only): AY2026/27 Trimester 1 dates from the SIT academic calendar; East blocks = IT courses; W3/W5 = other courses; W1 library shared.

## Marker outputs

| Artefact | Status |
|---|---|
| Inspected columns in `data/DATA_DICTIONARY.md` | Done |
| Cleaned ROBOD table and EDA figures | Done |
| Baseline versus Ridge versus Random Forest on NUS hold-out | Done (`metrics_holdout.csv`; hour × type mean wins MAE) |
| Generated `occupancy` and `occupancy_prediction` for SIT identifiers | `occupancy_generated.csv`, `occupancy_prediction.csv` |
| Limitations (NUS ≠ SIT; no ROBOD weekends; Wi-Fi ≠ headcount; generated current) | Written in README and `evidence/test-data-ai.md` |

Model files belong in `analytics/models/` (gitignored until a small evaluated artefact is chosen for the submission ZIP).
