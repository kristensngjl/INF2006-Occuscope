# Analytics

Occupancy forecast for Occuscope (Lideon).

Train on **NUS ROBOD** (room-level `occupant_count`) plus **NUS Wi-Fi** floor series (`raw_data.xlsx` sheet `5min`). Evaluate on held-out **NUS** timestamps (MAE / RMSE). Map predicted occupancy **ratios** onto SIT `location.capacity` and write generated rows into the app DB.

There are no SIT labels. Do not report “accuracy on Punggol”.

## Reproduce

Training files must already be in `data/raw/` (see `data/README.md`). Do not commit them.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r analytics/requirements.txt
python analytics/01_eda.py
python analytics/02_clean_robod.py
python analytics/03_eda_robod.py
python src/db/init_app_db.py
```

- `01_eda.py` — dummy SIT occupancy for Zul (`source = dummy`).
- `02_clean_robod.py` — HVAC-stripped ROBOD table → `data/processed/robod_clean.csv`.
- `03_eda_robod.py` — figures in `analytics/figures/`.
- Training, Wi-Fi features, and generated SIT occupancy are still TODO.

## Marker outputs

| Artefact | Status |
|---|---|
| Inspected columns in `data/DATA_DICTIONARY.md` | Done |
| Cleaned ROBOD table + EDA figures | Done |
| Baseline vs model on NUS hold-out | **TODO** |
| Generated `occupancy` / `occupancy_prediction` for SIT IDs | Dummy preview only |
| Limitations (NUS ≠ SIT, no ROBOD weekends, Wi-Fi ≠ heads) | Written |

Trained model files belong in `analytics/models/` (gitignored until a small evaluated artefact is chosen for the ZIP).
