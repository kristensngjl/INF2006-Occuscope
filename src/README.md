# Source (`src/`)

The FastAPI backend is in `backend/api.py`. See [backend/README.md](backend/README.md) for installation, startup and room-to-map integration. The database schema remains unchanged.

| Path | Owner | What it is |
|---|---|---|
| `backend/` | Zul | API implementation, dependencies and setup instructions |
| `api-contract.md` | Zul implements, Zi Qian consumes, Lideon owns prediction JSON | REST surface |
| `db/schema.sql` | Lideon (kickoff) / Zul (RDS later) | App tables + views |
| `db/init_app_db.py` | Lideon / Zul | Rebuild local SQLite from `data/sample/` |

## Local database

```
python src/db/init_app_db.py
```

Creates `data/occuscope.db`. Deletes and recreates the file each run so schema changes apply cleanly.

Backend local start (after installing `backend/requirements.txt`):

```
python -m uvicorn src.backend.api:app --reload
```

`location_id` values follow Room Booking System catalogue form (`E2-03-07-DR209`). Occupancy `source` is `generated` after `analytics/05_generate_sit.py`; `dummy` is only the fallback from `01_eda.py`.

- Foreign keys on. Crowd bands are views, not columns.
- NUS ROBOD / Wi-Fi files are **never** imported by this script.
- Same table names should move to RDS Postgres later (`AUTOINCREMENT` → identity / serial; `TEXT` timestamps → `TIMESTAMPTZ` if desired).

## API (v0)

See `api-contract.md`. The backend implements:

- `GET /occupancy/current?at=` → latest reading at or before the selected time per room
- `GET /floors/{building_id}/{floor}/summary` → `v_floor_type_summary`

Server entrypoint: `python -m uvicorn src.backend.api:app --reload`. Frontend: to be added by Zi Qian.
