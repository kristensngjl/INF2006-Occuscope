# Occuscope HTTP contract (v0)

Zul implements this against `src/db/schema.sql`. Zi Qian consumes it. Lideon owns the prediction payload.

- All timestamps: ISO-8601.
- Crowd band is **derived** (`v_occupancy_current.crowd_level`), never written by the client.
  - Quiet: occupancy_ratio ≤ 0.30
  - Moderate: ≤ 0.70
  - Crowded: otherwise
- JSON field names match the SQL column names below unless noted.

## Buildings and locations

### `GET /buildings`

List `building_id`, `name`, `campus`, `map_x`, `map_y`.

### `GET /locations`

Join `location` + `building`. Optional filters: `?building_id=` `?floor=` `?type=`.

### `GET /locations/{id}`

One location: `location_id`, `building_id`, `building_name`, `floor`, `name`, `type`, `capacity`, `map_x`, `map_y`.

### `GET /floors/{building_id}/{floor}/summary`

Rows from `v_floor_type_summary` for that building and floor (discussion-room availability).

## Occupancy

### `GET /occupancy/current`

`SELECT * FROM v_occupancy_current`.

This is also the **heatmap** payload: each row is a point (`map_x`, `map_y`) with `occupancy_ratio` and `crowd_level`. Filter `?building_id=` `?floor=` for one floor plate. No extra table — colour is derived from count / capacity.

Optional alias: `GET /heatmap` returning the same rows if the frontend prefers that path.

### `GET /occupancy/{location_id}`

History: `timestamp`, `occupancy_count`, `source`, ordered by time.

### `GET /occupancy/{location_id}/prediction`

Rows from `occupancy_prediction` for that id. Until a model is trained, the backend may omit this table and/or keep serving dummy history with `"source": "dummy"`.

## Events

### `GET /events/today`

Events whose `[start_time, end_time]` overlaps the Singapore calendar day, including `location_id`.
