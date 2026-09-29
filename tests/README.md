# Tests

Repeatable checks the marker can run without a cloud login.

```
python tests/test_gitignore_secrets.py
python tests/test_data_store_hygiene.py
python tests/test_crowd_and_seed.py
```

Stdlib unittest (no extra packages).

- `test_gitignore_secrets.py` — `.env`, `data/raw/`, `CLOUDPROJ.md`, the brief PDF, joblib models, and `liddy.md` are gitignored; `.env.example` has no AWS secret value.
- `test_data_store_hygiene.py` — init does not read `data/raw/`; schema is SIT-only; forbidden paths are not tracked; local `occuscope.db` occupancy `source` is dummy/generated/model only.
- `test_crowd_and_seed.py` — Quiet ≤0.30 / Moderate ≤0.70 matches schema; generated and prediction CSVs have the contracted columns.

- API / workflow tests: to be added with the backend (Zul / Zi Qian).
- Data/AI: `python analytics/04_train.py` (see `evidence/test-data-ai.md`).
- Record dated output under `evidence/` as well as any automated tests here.
