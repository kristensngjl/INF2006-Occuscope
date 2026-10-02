"""Seed hour-aligned discussion-room bookings that match occupancy generate.

Run after student accounts exist. Demo login 2500001 is left with a free weekly quota.
"""
from __future__ import annotations

import csv
import hashlib
import sqlite3
import sys
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analytics"))
from occupancy_model import demo_slot_booked  # noqa: E402

SAMPLE = ROOT / "data" / "sample"
SGT = "+08:00"
# Keep 2500001–2500199 free so the usual demo login can still book.
BOOKING_USERS = [f"trial-2600{n:03d}" for n in range(1, 1000)] + [
    f"trial-2500{n:03d}" for n in range(200, 1000)
]


def iso_sgt(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S") + SGT


def parse_instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")[:19])


def event_index() -> dict[str, list[tuple[datetime, datetime]]]:
    path = SAMPLE / "events.csv"
    grouped: dict[str, list[tuple[datetime, datetime]]] = {}
    if not path.is_file():
        return grouped
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            grouped.setdefault(row["location_id"], []).append(
                (parse_instant(row["start_time"]), parse_instant(row["end_time"]))
            )
    return grouped


def event_blocks(location_id: str, start: datetime, end: datetime, events: dict) -> bool:
    for a, b in events.get(location_id, ()):
        if a < end and b > start:
            return True
    return False


def discussion_rooms() -> list[str]:
    with (SAMPLE / "locations.csv").open(encoding="utf-8", newline="") as f:
        return [row["location_id"] for row in csv.DictReader(f) if row["type"] == "discussion_room"]


def iter_demo_bookings(start: date, end: date):
    events = event_index()
    rooms = discussion_rooms()
    created = iso_sgt(datetime(2026, 8, 20, 9, 0, 0))
    day = start
    while day <= end:
        for location_id in rooms:
            for hour in range(8, 20):
                ts = datetime(day.year, day.month, day.day, hour, 0, 0)
                finish = ts + timedelta(hours=1)
                if event_blocks(location_id, ts, finish, events):
                    continue
                if not demo_slot_booked(location_id, ts):
                    continue
                who = int(
                    hashlib.sha256(f"who|{location_id}|{day.isoformat()}|{hour}".encode()).hexdigest()[:8],
                    16,
                ) % len(BOOKING_USERS)
                user_id = BOOKING_USERS[who]
                key = f"demo|{location_id}|{iso_sgt(ts)}"
                booking_id = hashlib.sha256(key.encode()).hexdigest()[:32]
                yield {
                    "booking_id": booking_id,
                    "user_id": user_id,
                    "location_id": location_id,
                    "start_time": iso_sgt(ts),
                    "end_time": iso_sgt(finish),
                    "created_at": created,
                }
        day += timedelta(days=1)


def insert_demo_bookings(path: Path, start: date | None = None, end: date | None = None) -> int:
    start = start or date(2026, 8, 31)
    end = end or date(2026, 12, 27)
    rows = list(iter_demo_bookings(start, end))
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        existing = {row[0] for row in conn.execute("SELECT booking_id FROM room_booking")}
        inserted = 0
        with conn:
            for row in rows:
                if row["booking_id"] in existing:
                    continue
                conn.execute(
                    """INSERT INTO room_booking
                       (booking_id, user_id, location_id, start_time, end_time, status, created_at)
                       VALUES (:booking_id, :user_id, :location_id, :start_time, :end_time, 'confirmed', :created_at)""",
                    row,
                )
                inserted += 1
        return inserted
