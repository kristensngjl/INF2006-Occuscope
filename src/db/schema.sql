-- Occuscope application database (SIT Punggol map only).
--
-- Local: SQLite via `python src/db/init_app_db.py` → data/occuscope.db
-- Later: same table/view names on RDS Postgres
--        (AUTOINCREMENT → GENERATED/SERIAL; TEXT timestamps may become TIMESTAMPTZ).
--
-- Do not load ROBOD or NUS Wi-Fi into these tables. Those files stay in data/raw/.
--
-- Hierarchy: building.campus → building → location.floor → location
-- Crowd bands are derived in views (never stored), so Quiet/Moderate/Crowded
-- cannot drift from occupancy_count / capacity.

PRAGMA foreign_keys = ON;

-- One row per mapped building. campus is a column (single campus today).
CREATE TABLE IF NOT EXISTS building (
    building_id  TEXT PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    campus       TEXT NOT NULL DEFAULT 'SIT Punggol',
    -- Normalised 0–1 position on the campus map image (nullable until ZQ pins it).
    map_x        REAL CHECK (map_x IS NULL OR (map_x >= 0 AND map_x <= 1)),
    map_y        REAL CHECK (map_y IS NULL OR (map_y >= 0 AND map_y <= 1))
);

-- A bookable / visitable space (library floor, discussion room, LT, food court, …).
CREATE TABLE IF NOT EXISTS location (
    location_id  TEXT PRIMARY KEY,
    building_id  TEXT NOT NULL,
    floor        INTEGER NOT NULL CHECK (floor >= -2 AND floor <= 20),
    name         TEXT NOT NULL,
    type         TEXT NOT NULL CHECK (
                     type IN (
                         'library',
                         'discussion_room',
                         'lecture_theatre',
                         'food_court',
                         'office',
                         'other'
                     )
                 ),
    capacity     INTEGER NOT NULL CHECK (capacity > 0),
    map_x        REAL CHECK (map_x IS NULL OR (map_x >= 0 AND map_x <= 1)),
    map_y        REAL CHECK (map_y IS NULL OR (map_y >= 0 AND map_y <= 1)),
    FOREIGN KEY (building_id) REFERENCES building(building_id),
    UNIQUE (building_id, floor, name)
);

-- Point-in-time headcount for a SIT location (generated, not a live sensor).
-- occupancy_count may exceed capacity (overflow still maps to Crowded).
-- source: dummy = weekday stub; generated = model transfer; model = reserved.
CREATE TABLE IF NOT EXISTS occupancy (
    reading_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id      TEXT NOT NULL,
    timestamp        TEXT NOT NULL, -- ISO-8601
    occupancy_count  INTEGER NOT NULL CHECK (occupancy_count >= 0),
    source           TEXT NOT NULL DEFAULT 'generated' CHECK (
                         source IN ('dummy', 'generated', 'model')
                     ),
    FOREIGN KEY (location_id) REFERENCES location(location_id),
    UNIQUE (location_id, timestamp)
);

-- Forecast rows served by GET /occupancy/{id}/prediction.
CREATE TABLE IF NOT EXISTS occupancy_prediction (
    prediction_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id      TEXT NOT NULL,
    predicted_for    TEXT NOT NULL, -- ISO-8601 instant being forecast
    occupancy_count  INTEGER NOT NULL CHECK (occupancy_count >= 0),
    model_version    TEXT NOT NULL DEFAULT 'v0',
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (location_id) REFERENCES location(location_id),
    UNIQUE (location_id, predicted_for, model_version)
);

-- Event pin on a location. end_time must be after start_time.
CREATE TABLE IF NOT EXISTS event (
    event_id     TEXT PRIMARY KEY,
    location_id  TEXT NOT NULL,
    title        TEXT NOT NULL,
    description  TEXT,
    start_time   TEXT NOT NULL, -- ISO-8601
    end_time     TEXT NOT NULL,
    FOREIGN KEY (location_id) REFERENCES location(location_id),
    CHECK (end_time > start_time)
);

-- Optional login identities (Ryan). Empty until auth is added.
-- Named app_user because USER is reserved in some engines.
CREATE TABLE IF NOT EXISTS app_user (
    user_id     TEXT PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    role        TEXT NOT NULL CHECK (role IN ('student', 'staff', 'admin')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_location_building_floor
    ON location (building_id, floor);

CREATE INDEX IF NOT EXISTS idx_location_type
    ON location (type);

CREATE INDEX IF NOT EXISTS idx_occupancy_location_time
    ON occupancy (location_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_prediction_location_time
    ON occupancy_prediction (location_id, predicted_for);

CREATE INDEX IF NOT EXISTS idx_event_location
    ON event (location_id);

CREATE INDEX IF NOT EXISTS idx_event_time
    ON event (start_time, end_time);

-- Map payload: latest reading per location + derived crowd_level.
CREATE VIEW IF NOT EXISTS v_occupancy_current AS
SELECT
    l.location_id,
    l.building_id,
    b.name AS building_name,
    b.campus,
    l.floor,
    l.name,
    l.type,
    l.capacity,
    l.map_x,
    l.map_y,
    o.timestamp,
    o.occupancy_count,
    o.source,
    ROUND(1.0 * o.occupancy_count / l.capacity, 4) AS occupancy_ratio,
    CASE
        WHEN o.occupancy_count IS NULL THEN NULL
        WHEN 1.0 * o.occupancy_count / l.capacity <= 0.30 THEN 'quiet'
        WHEN 1.0 * o.occupancy_count / l.capacity <= 0.70 THEN 'moderate'
        ELSE 'crowded'
    END AS crowd_level
FROM location AS l
JOIN building AS b
    ON b.building_id = l.building_id
LEFT JOIN occupancy AS o
    ON o.location_id = l.location_id
   AND o.timestamp = (
        SELECT MAX(o2.timestamp)
        FROM occupancy AS o2
        WHERE o2.location_id = l.location_id
   );

-- Floor browser: how many spaces of each type are quiet / moderate / crowded.
CREATE VIEW IF NOT EXISTS v_floor_type_summary AS
SELECT
    building_id,
    building_name,
    campus,
    floor,
    type,
    COUNT(*) AS location_count,
    SUM(CASE WHEN crowd_level IS NOT NULL THEN 1 ELSE 0 END) AS with_reading,
    SUM(CASE WHEN crowd_level = 'quiet' THEN 1 ELSE 0 END) AS quiet_count,
    SUM(CASE WHEN crowd_level = 'moderate' THEN 1 ELSE 0 END) AS moderate_count,
    SUM(CASE WHEN crowd_level = 'crowded' THEN 1 ELSE 0 END) AS crowded_count
FROM v_occupancy_current
GROUP BY building_id, building_name, campus, floor, type;
