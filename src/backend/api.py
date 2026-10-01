"""Read-only local API over the frozen SIT application schema."""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from .chat import ChatInput, answer

ROOT = Path(__file__).resolve().parents[2]
SGT = timezone(timedelta(hours=8))


def parse_time(value: str, name: str) -> datetime:
    # Require the contract's explicit Singapore offset and a real time of day.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+08:00", value):
        raise HTTPException(422, f"{name} must be ISO-8601 with +08:00, e.g. 2026-09-30T15:00:00+08:00; URL-encode + as %2B")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(422, f"{name} is not a valid date/time") from None


def create_app(db_path: str | Path | None = None) -> FastAPI:
    if db_path is None:
        url = os.getenv("DATABASE_URL", "sqlite:///data/occuscope.db")
        if not url.startswith("sqlite:///"):
            raise ValueError("This local API currently supports SQLite DATABASE_URL only")
        db_path = url.removeprefix("sqlite:///")
    path = Path(db_path)
    if not path.is_absolute():
        path = ROOT / path

    app = FastAPI(title="Occuscope API", version="0.1.0", description="Generated SIT occupancy, not live sensor readings.")

    def rows(sql: str, params: tuple = ()) -> list[dict]:
        try:
            # Read-only mode avoids accidentally creating an empty database.
            with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
                conn.row_factory = sqlite3.Row
                return [dict(row) for row in conn.execute(sql, params).fetchall()]
        except sqlite3.Error:
            raise HTTPException(503, "Application database unavailable; initialise it with python src/db/init_app_db.py") from None

    location_sql = """SELECT l.*, b.name AS building_name, b.campus
                      FROM location l JOIN building b ON b.building_id = l.building_id"""

    def require_location(location_id: str) -> dict:
        found = rows(location_sql + " WHERE l.location_id = ?", (location_id,))
        if not found:
            raise HTTPException(404, "Location not found")
        return found[0]

    @app.get("/buildings")
    def buildings():
        return rows("SELECT * FROM building ORDER BY building_id")

    @app.get("/locations")
    def locations(building_id: str | None = None, floor: int | None = None, type: str | None = None):
        filters, params = [], []
        for column, value in (("building_id", building_id), ("floor", floor), ("type", type)):
            if value is not None:
                filters.append(f"l.{column} = ?")
                params.append(value)
        where = " WHERE " + " AND ".join(filters) if filters else ""
        return rows(location_sql + where + " ORDER BY l.location_id", tuple(params))

    @app.get("/locations/{location_id}")
    def location(location_id: str):
        return require_location(location_id)

    @app.get("/occupancy/current")
    def current(at: str = Query(...)):
        instant = parse_time(at, "at").isoformat()
        return rows("""
            SELECT l.location_id, l.building_id, b.name AS building_name,
                   b.campus, l.floor, l.name, l.type, l.capacity, l.map_x, l.map_y,
                   o.timestamp, o.occupancy_count, o.source,
                   ROUND(1.0 * o.occupancy_count / l.capacity, 4) AS occupancy_ratio,
                   CASE WHEN o.occupancy_count IS NULL THEN NULL
                        WHEN 1.0 * o.occupancy_count / l.capacity <= 0.30 THEN 'quiet'
                        WHEN 1.0 * o.occupancy_count / l.capacity <= 0.70 THEN 'moderate'
                        ELSE 'crowded' END AS crowd_level
            FROM location l JOIN building b ON b.building_id = l.building_id
            LEFT JOIN occupancy o ON o.reading_id = (
                SELECT o2.reading_id FROM occupancy o2
                WHERE o2.location_id = l.location_id
                  AND julianday(o2.timestamp) <= julianday(?)
                ORDER BY julianday(o2.timestamp) DESC, o2.reading_id DESC LIMIT 1
            ) ORDER BY l.location_id
        """, (instant,))

    @app.get("/floors/{building_id}/{floor}/summary")
    def floor_summary(building_id: str, floor: int):
        return rows("SELECT * FROM v_floor_type_summary WHERE building_id = ? AND floor = ? ORDER BY type", (building_id, floor))

    @app.get("/occupancy/{location_id}/prediction")
    def prediction(location_id: str):
        require_location(location_id)
        return rows("""SELECT predicted_for, occupancy_count, model_version
                       FROM occupancy_prediction WHERE location_id = ?
                       ORDER BY julianday(predicted_for), model_version""", (location_id,))

    @app.get("/occupancy/{location_id}")
    def timeline(location_id: str, from_: str = Query(..., alias="from"), to: str = Query(...)):
        start, end = parse_time(from_, "from"), parse_time(to, "to")
        if end <= start or end - start > timedelta(days=7):
            raise HTTPException(422, "to must be after from, with a maximum range of 7 days")
        require_location(location_id)
        return rows("""SELECT timestamp, occupancy_count, source FROM occupancy
                       WHERE location_id = ? AND julianday(timestamp) >= julianday(?)
                         AND julianday(timestamp) < julianday(?)
                       ORDER BY julianday(timestamp)""", (location_id, start.isoformat(), end.isoformat()))

    @app.get("/events/today")
    def events_today():
        start = datetime.now(SGT).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return rows("""SELECT * FROM event WHERE julianday(start_time) < julianday(?)
                       AND julianday(end_time) > julianday(?) ORDER BY julianday(start_time), event_id""",
                    (end.isoformat(), start.isoformat()))

    @app.post("/chat")
    def chat(body: ChatInput):
        if not body.message.strip():
            raise HTTPException(422, "Enter a question")
        instant = parse_time(body.at, "at").isoformat()
        return answer(body.message.strip(), instant, current(instant))

    return app


app = create_app()
