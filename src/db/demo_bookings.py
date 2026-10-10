"""Seed hour-aligned discussion-room bookings that match occupancy generate.

Run after student accounts exist. Demo login 2500001 is left with a free weekly quota.
Each student is capped at 240 minutes per Monday–Sunday week across all discussion
rooms (including W1 library meeting rooms), with no overlapping hours.
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
WEEK_LIMIT_MINUTES = 240
SLOT_MINUTES = 60
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


def week_monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def pick_student(location_id: str, ts: datetime, used: dict, busy: dict) -> str | None:
    """Same 240 min/week and no-overlap rules as the booking API (all discussion rooms share one quota)."""
    monday = week_monday(ts.date())
    stamp = (ts.date(), ts.hour)
    start = int(
        hashlib.sha256(f"who|{location_id}|{ts.date().isoformat()}|{ts.hour}".encode()).hexdigest()[:8],
        16,
    ) % len(BOOKING_USERS)
    for step in range(len(BOOKING_USERS)):
        user_id = BOOKING_USERS[(start + step) % len(BOOKING_USERS)]
        if stamp in busy.get(user_id, ()):
            continue
        if used.get((user_id, monday), 0) + SLOT_MINUTES > WEEK_LIMIT_MINUTES:
            continue
        return user_id
    return None


def iter_demo_bookings(start: date, end: date):
    events = event_index()
    rooms = discussion_rooms()
    created = iso_sgt(datetime(2026, 8, 20, 9, 0, 0))
    used: dict[tuple[str, date], int] = {}
    busy: dict[str, set[tuple[date, int]]] = {}
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
                user_id = pick_student(location_id, ts, used, busy)
                if user_id is None:
                    continue
                monday = week_monday(day)
                used[(user_id, monday)] = used.get((user_id, monday), 0) + SLOT_MINUTES
                busy.setdefault(user_id, set()).add((day, hour))
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
