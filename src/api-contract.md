# Occuscope HTTP contract (v0)

Zul implements this against `src/db/schema.sql`. Zi Qian consumes it. Lideon owns the prediction payload.

- All timestamps: ISO-8601 **with Singapore offset** (`2026-09-29T15:00:00+08:00`). Do not drop the time to midnight; Excel often does if the file is opened as a spreadsheet — use the API or a text editor.
- Crowd band is **derived on the server** from `occupancy_count / capacity` (`v_occupancy_current.crowd_level`). Clients must not send Quiet/Moderate/Crowded (or a colour) as an input. If an endpoint writes occupancy, it still must not accept `crowd_level`.
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

Heatmap payload: `map_x`, `map_y`, `occupancy_ratio`, `crowd_level` derived from count / capacity. Clients must not send a crowd colour. Do not display “live sensors”.

The sample seed is **AY2026/27 Trimester 1** (31 August–27 December 2026, hourly 08:00–20:00 SGT). `v_occupancy_current` uses the **latest timestamp in the table**, which is the end of the seed (trimester break) — too empty for a demo heatmap.

**Required for the map:** `GET /occupancy/current?at={ISO-8601}` (Singapore offset). Return, per location, the occupancy row at that instant, or the latest row at or before `at`. Example: `?at=2026-09-30T15:00:00+08:00` (teaching Wednesday). Optional alias: `GET /heatmap?at=`.

Implemented in `src/backend/api.py`. `at` is required; encode the plus sign as `%2B` or use `URLSearchParams`. Timestamps must include hours, minutes, seconds and `+08:00`. Responses are arrays with the fields of `v_occupancy_current`, including `location_id`, hierarchy, capacity, coordinates, source, the actual reading timestamp, and **`booked`** (`1` only for discussion rooms when a confirmed Occuscope booking overlaps `at` **and** `at` is in 08:00–20:00 SGT, else `0`). Study spaces and food courts stay occupancy-only. Seeded discussion-room bookings usually coincide with people in the room, with some no-shows and some walk-ins when `booked=0`. Rooms without an earlier reading have null occupancy fields, not zero. Null coordinates remain null. Display the reading timestamp because an as-of result can be old. The optional `/heatmap` alias is not implemented.

### `GET /occupancy/{location_id}`

Timeline history: hourly `timestamp`, `occupancy_count`, `source`. **Filter** with `?from=` and `?to=` (ISO-8601). Do not plot the whole trimester in one chart; a week is enough on screen.

Both bounds are required. The range is `[from, to)` (inclusive start, exclusive end), with `to > from`, and cannot exceed seven days. Results are sorted by time. Invalid/missing parameters return HTTP 422; unknown locations return 404; known locations without readings return `[]`. Database unavailability returns 503.

The floor summary endpoint uses the latest-reading view independently of heatmap time. For a summary at the selected time, group `/occupancy/current?at=` results on the client.

### `GET /occupancy/{location_id}/prediction`

**Required:** `?at={ISO-8601+08:00}` (same instant as the heatmap). Returns up to two later **generated** occupancy hours for that location (`predicted_for`, `occupancy_count`, `model_version` = `v0`). This is lookahead in the seeded series, not a live sensor or a model loaded in Lambda.

The CSV `occupancy_prediction.csv` is still a sample artefact (two hours after `predict_as_of` in `sit_calendar.json`). The API does not depend on that table for the map.

## Events

### `GET /events/today`

Events whose `[start_time, end_time]` overlaps the Singapore calendar day, including `location_id`.
