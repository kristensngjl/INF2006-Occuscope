# Tests

Repeatable checks the marker can run without a cloud login.

```
python tests/test_gitignore_secrets.py
```

Stdlib unittest (no extra packages). Confirms `.env`, `data/raw/`, `CLOUDPROJ.md`, the brief PDF, joblib models, and `liddy.md` are gitignored, and that `.env.example` does not contain an `AWS_SECRET_ACCESS_KEY` value.

- API / workflow tests: to be added with the backend (Zul / Zi Qian).
- Data/AI: `python analytics/04_train.py` (see `evidence/test-data-ai.md`).
- Record dated output under `evidence/` as well as any automated tests here.
