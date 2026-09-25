# Source (`src/`)

Application code will reside here. This folder currently holds the **database schema** and **HTTP contract** so frontend, backend, and data/ML work can proceed in parallel.

| Path | Owner | What it is |
|---|---|---|
| `api-contract.md` | Zul implements, Zi Qian consumes, Lideon owns prediction JSON | REST surface |
| `db/schema.sql` | Lideon (kickoff) / Zul (RDS later) | App tables + views |
| `db/init_app_db.py` | Lideon / Zul | Rebuild local SQLite from `data/sample/` |

## Local database

```
python src/db/init_app_db.py
```

Creates `data/occuscope.db`. Deletes and recreates the file each run so schema changes apply cleanly.

Backend local start (generated occupancy if `data/sample/occupancy_generated.csv` exists):

```
python src/db/init_app_db.py
```

`location_id` values follow Room Booking System catalogue form (`E2-03-07-DR209`). Occupancy `source` is `generated` after `analytics/05_generate_sit.py`; `dummy` is only the fallback from `01_eda.py`.

- Foreign keys on. Crowd bands are views, not columns.
- NUS ROBOD / Wi-Fi files are **never** imported by this script.
- Same table names should move to RDS Postgres later (`AUTOINCREMENT` → identity / serial; `TEXT` timestamps → `TIMESTAMPTZ` if desired).

## API (v0)

See `api-contract.md`. Backend should prefer:

- `GET /occupancy/current` → `v_occupancy_current`
- `GET /floors/{building_id}/{floor}/summary` → `v_floor_type_summary`

Frontend folder and server entrypoint: to be added by Zi Qian / Zul.
