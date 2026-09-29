# Run the local API

Python 3.11+, from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r src/backend/requirements.txt
.venv\Scripts\python src/db/init_app_db.py
.venv\Scripts\python -m uvicorn src.backend.api:app --reload
```

The initialiser **deletes and rebuilds** `data/occuscope.db`; skip it if you have a populated database you want to keep. The API opens SQLite read-only and preserves the existing schema. Export `DATABASE_URL=sqlite:///path/to/file.db` to override the default. Relative paths resolve from the repository root; `.env` is not automatically loaded. RDS integration is future work.

Open http://127.0.0.1:8000/docs to test the endpoints interactively.

## Connect the future map

Assign each map marker or room polygon its catalogue `location_id`. Join by this key, not name or array position. `/buildings` and `/locations?building_id=E2&floor=3` provide the hierarchy, capacities and normalised coordinates. Match coordinates to the eventual artwork; list rooms with null coordinates until pinned.

```javascript
const query = new URLSearchParams({ at: '2026-09-30T15:00:00+08:00' });
const response = await fetch(`/occupancy/current?${query}`);
if (!response.ok) throw new Error(`Occupancy request failed: ${response.status}`);
const rooms = await response.json();
const occupancyByRoom = new Map(rooms.map(room => [room.location_id, room]));
// Look up occupancyByRoom.get(shape.location_id) for each map shape.
// Use crowd_level for colour; null means unknown. Show source and timestamp.
```

Serve the frontend on the same origin or use a development proxy forwarding API routes to port 8000. Cross-origin requests are not enabled by default.

Fetch the chart when a room is selected:

```javascript
const query = new URLSearchParams({
  from: '2026-09-28T00:00:00+08:00',
  to: '2026-10-05T00:00:00+08:00',
});
const response = await fetch(`/occupancy/${encodeURIComponent(locationId)}?${query}`);
if (!response.ok) throw new Error(`Timeline request failed: ${response.status}`);
const history = await response.json();
```

The API enforces a seven-day maximum, inclusive start and exclusive end. Missing observations are not zero. Label occupancy as generated, not live sensors. A map is not required to test the endpoints.

Inspect occupancy CSVs using a text editor, API or database, **not Excel**, to preserve times. See [api-contract.md](../api-contract.md) for the contract.

