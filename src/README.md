# Source (`src/`)

Runnable application will live here. Right now this folder holds the **database schema** and the **HTTP contract** so frontend, backend, and ML can proceed in parallel.

| Path | Owner | What it is |
|---|---|---|
| `api-contract.md` | Zul implements, Zi Qian consumes, Lideon owns prediction JSON | REST surface |
| `db/schema.sql` | Lideon (kickoff) / Zul (RDS later) | App tables + views |
| `db/init_app_db.py` | Lideon / Zul | Rebuild local SQLite from `data/sample/` |

## Local database

```
python src/db/init_app_db.py
```

Creates `data/occuscope.db`. Deletes and recreates the file each run while the schema is still settling.

- Foreign keys on. Crowd bands are views, not columns.
- NUS ROBOD / Wi-Fi files are **never** imported by this script.
- Same table names should move to RDS Postgres later (`AUTOINCREMENT` → identity / serial; `TEXT` timestamps → `TIMESTAMPTZ` if desired).

## API (v0)

See `api-contract.md`. Backend should prefer:

- `GET /occupancy/current` → `v_occupancy_current`
- `GET /floors/{building_id}/{floor}/summary` → `v_floor_type_summary`

Frontend folder and server entrypoint: to be added by Zi Qian / Zul.
