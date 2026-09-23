"""Rebuild the local Occuscope SQLite database from schema.sql + data/sample CSVs.

Does not import NUS ROBOD or Wi-Fi files. Run from the repo root:

    python src/db/init_app_db.py

Deletes data/occuscope.db if it already exists so schema changes apply cleanly.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "occuscope.db"
SCHEMA = Path(__file__).resolve().parent / "schema.sql"
SAMPLE = ROOT / "data" / "sample"


def connect() -> sqlite3.Connection:
    """Open SQLite with foreign keys enforced for this connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def read_csv(path: Path) -> list[dict[str, str]]:
    """Load a seed CSV as a list of dicts keyed by header names."""
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def seed(conn: sqlite3.Connection) -> None:
    """Insert buildings, locations, events, and occupancy preview (if present)."""
    conn.executemany(
        """
        INSERT INTO building (building_id, name, campus, map_x, map_y)
        VALUES (:building_id, :name, :campus, :map_x, :map_y)
        """,
        read_csv(SAMPLE / "buildings.csv"),
    )
    conn.executemany(
        """
        INSERT INTO location
            (location_id, building_id, floor, name, type, capacity, map_x, map_y)
        VALUES
            (:location_id, :building_id, :floor, :name, :type, :capacity, :map_x, :map_y)
        """,
        read_csv(SAMPLE / "locations.csv"),
    )
    conn.executemany(
        """
        INSERT INTO event
            (event_id, location_id, title, description, start_time, end_time)
        VALUES
            (:event_id, :location_id, :title, :description, :start_time, :end_time)
        """,
        read_csv(SAMPLE / "events.csv"),
    )

    preview = SAMPLE / "occupancy_preview.csv"
    if preview.exists():
        conn.executemany(
            """
            INSERT INTO occupancy
                (location_id, timestamp, occupancy_count, source)
            VALUES (:location_id, :timestamp, :occupancy_count, :source)
            """,
            read_csv(preview),
        )


def summarize(conn: sqlite3.Connection) -> None:
    """Print row counts and the derived crowd band for each location."""
    for table in (
        "building",
        "location",
        "event",
        "occupancy",
        "occupancy_prediction",
        "app_user",
    ):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {n} rows")
    current = conn.execute(
        "SELECT location_id, crowd_level, occupancy_ratio FROM v_occupancy_current"
    ).fetchall()
    print("  v_occupancy_current:")
    for row in current:
        print(f"    {row[0]}  crowd={row[1]}  ratio={row[2]}")


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    with connect() as conn:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        seed(conn)
        conn.commit()
        print(f"App DB ready: {DB_PATH.relative_to(ROOT)}")
        summarize(conn)
        print("NUS ROBOD / Wi-Fi stay in data/raw/ — not in this database.")


if __name__ == "__main__":
    main()
