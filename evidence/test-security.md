# Named threat

Client cannot forge `crowd_level`. Quiet / Moderate / Crowded are derived only in `v_occupancy_current` (`occupancy_count / capacity`). The API must not persist a client-supplied band.

Supporting checks (not this named threat): injection on IDs, secrets/gitignore, occupancy not claimed as live SIT sensors.

# Objective

Demonstrate that `crowd_level` cannot be written by the client and that GET occupancy bands match the view. Supporting: unknown IDs fail closed; gitignore keeps secrets and the brief PDF out of git; docs do not claim live Punggol sensors.

# Setup

**Primary threat (blocked on backend):** expected results locked against `src/api-contract.md` and `src/db/schema.sql`. There is no HTTP server yet.

**Secrets supporting check (runnable now):** from the repository root, Python 3.11+:

```
python tests/test_gitignore_secrets.py
```

**When Zul’s API exists:** copy `.env.example` to `.env` (never commit `.env`), rebuild SQLite, then start the API:

```
python src/db/init_app_db.py
```

Use `data/occuscope.db` (gitignored). Do not import `data/raw/` into the database.

# Command / steps

Named threat (when the API is up; replace base URL if Kristen deploys):

1. `GET /occupancy/current` — each row has `occupancy_ratio` and `crowd_level`; band matches quiet ≤ 0.30 / moderate ≤ 0.70 / else crowded from count / capacity.
2. If any write route exists, send extra JSON including `crowd_level` — the stored/served band must still come from the view. If the API is read-only, record that mutating routes are absent (control = no writes).

Supporting:

3. `GET /occupancy/{location_id}/prediction` for a seeded id (for example `E2-03-07-DR209`).
4. Unknown `location_id` on occupancy and prediction paths — 4xx, not 500.
5. `python tests/test_gitignore_secrets.py` from the repository root.
6. Confirm responses and docs do not claim live Punggol sensors (`source` is `generated` after seed).

# Expected result

- Named threat: heatmap payload exposes derived `crowd_level` only; the client cannot persist a band.
- Unknown identifiers return 4xx, not an unhandled 500.
- `tests/test_gitignore_secrets.py` exits 0.
- Occupancy is labelled generated / not live SIT accuracy (`evidence/test-data-ai.md`).

# Date

- Secrets supporting check: 26 September 2026 (Ryan).
- Named threat (API): TODO.

# Actual result

- Named threat: TODO (blocked on Zul’s API).
- Secrets supporting check: `python tests/test_gitignore_secrets.py` — all tests passed, 26 September 2026, Ryan. Does not prove crowd-level forgery control.

# Artefact path

- `src/api-contract.md`
- `src/db/schema.sql` (`v_occupancy_current`, `app_user`)
- `tests/test_gitignore_secrets.py`
- `.gitignore`, `.env.example`
- `evidence/threat-control-map.md`
- `evidence/test-data-ai.md`
- Redacted request/response once the API exists (no keys, account IDs, or IPs)
