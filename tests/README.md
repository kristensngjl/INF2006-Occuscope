# Tests

Repeatable checks the marker can run without a cloud login.

```
python tests/test_gitignore_secrets.py
python tests/test_data_store_hygiene.py
python tests/test_crowd_and_seed.py
python tests/test_api_security.py
python tests/test_no_secrets_in_tracked_files.py
python tests/test_submission_preflight.py
python tests/test_frontend_server_security.py
```

Stdlib unittest (no extra packages) for the first five.

- `test_gitignore_secrets.py` — `.env`, `data/raw/`, `CLOUDPROJ.md`, the brief PDF, joblib models, and `liddy.md` are gitignored; `.env.example` has no AWS secret value.
- `test_data_store_hygiene.py` — init does not read `data/raw/`; schema is SIT-only; forbidden paths are not tracked; local `occuscope.db` occupancy `source` is dummy/generated/model only.
- `test_crowd_and_seed.py` — Quiet ≤0.30 / Moderate ≤0.70 matches schema; every catalogue id has a full generated series, prediction rows, and event foreign keys.
- `test_api_security.py` — named threat (`crowd_level` forgery) plus occupancy fail-closed, occupancy has no write verbs, login/booking session + header, cookie flags, login throttle. Needs API/test deps and `data/occuscope.db`.
- `test_no_secrets_in_tracked_files.py` — scans tracked and uncommitted text files for credential, private-key, deployed API URL, and token-in-URL patterns (Appendix A hygiene).
- `test_submission_preflight.py` — manifest paths, required headings on the four test markdown files, and a completeness report (prints open TODO counts; fails only if `PREFLIGHT_STRICT=1`).
- `test_frontend_server_security.py` — starts a local Node dev server on a free port, checks allowlist, rejects writes on static/occupancy proxy paths, proxy 503 hygiene, and prints absent security headers without failing on them.

- Data/AI: `python analytics/04_train.py` (see `evidence/test-data-ai.md`).
- Record dated output under `evidence/` as well as any automated tests here.
