"""Shared v0 occupancy predictor (mean occupant count by hour and room type).

Imported by the training and generation scripts so joblib unpickles against this
module rather than `__main__`.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime

import pandas as pd

FEATURES = ["hour", "day_of_week", "room_type"]
TARGET = "occupant_count"

SIT_TYPE_MAP = {
    "discussion_room": "office",
    "library": "library",
    "lecture_theatre": "lecture",
    "food_court": "library",
    "office": "office",
    "other": "office",
}


class HourRoomTypeMean:
    def __init__(self, means: pd.Series, global_mean: float):
        self.means = means
        self.global_mean = float(global_mean)

    def predict(self, X: pd.DataFrame):
        key = list(zip(X["hour"].astype(int), X["room_type"].astype(str)))
        vals = [self.means.get(k, self.global_mean) for k in key]
        return pd.Series(vals, index=X.index).clip(lower=0).to_numpy()


def _unit01(key: str) -> float:
    n = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:2], "big")
    return n / 65535.0


def location_mix(location_id: str, low: float = 0.30, high: float = 1.22) -> float:
    """Stable per-room mix. v0 has no SIT room identity, so clones of the same type
    would otherwise be identical (every discussion room red at 15:00)."""
    return low + (high - low) * _unit01(f"mix|{location_id}")


def hour_jitter(location_id: str, ts: datetime, scale: float = 0.22) -> float:
    """Small day/hour wiggle so Tuesday 15:00 is not a copy of Wednesday 15:00."""
    u = _unit01(f"jit|{location_id}|{ts.date().isoformat()}|{ts.hour}")
    return 1.0 + scale * (2.0 * u - 1.0)


def event_turnout(event_id: str, ts: datetime) -> float:
    """Stable mixed turnout for one seeded event. Not derived from the title."""
    u = _unit01(f"evt|{event_id}")
    if u < 0.48:
        base = 0.55 + 0.38 * (u / 0.48)
    elif u < 0.82:
        base = 0.93 + 0.17 * ((u - 0.48) / 0.34)
    else:
        base = 1.10 + 0.28 * ((u - 0.82) / 0.18)
    wiggle = 0.10 * (2.0 * _unit01(f"evt-h|{event_id}|{ts.date().isoformat()}|{ts.hour}") - 1.0)
    return max(0.50, min(1.40, base + wiggle))


def booking_demand(ts: datetime) -> float:
    """How hard rooms are to get: recess quiet, swot/exams busy, break empty."""
    d = ts.date()
    if date(2026, 10, 12) <= d <= date(2026, 10, 18):
        return 0.55
    if date(2026, 11, 16) <= d <= date(2026, 11, 29):
        return 1.38
    if date(2026, 11, 30) <= d <= date(2026, 12, 6):
        return 1.52
    if d >= date(2026, 12, 7):
        return 0.35
    return 1.0


def demo_slot_booked(location_id: str, ts: datetime) -> bool:
    """Seeded discussion-room booking for this hour. Demand rises toward exams."""
    if ts.hour < 8 or ts.hour >= 20:
        return False
    weekday = ts.weekday()
    if weekday >= 5:
        chance = 0.14
    elif ts.hour < 10 or ts.hour >= 17:
        chance = 0.26
    elif ts.hour < 12:
        chance = 0.40
    else:
        chance = 0.50
    chance = min(0.86, chance * booking_demand(ts))
    return _unit01(f"book|{location_id}|{ts.date().isoformat()}|{ts.hour}") < chance


def booking_occupancy_count(
    location_id: str,
    ts: datetime,
    sit_type: str,
    sit_cap: int,
    count: int,
    event_blocks: bool,
) -> int:
    """SIT-style mix: booked+people, booked+empty, walk-in, and empty available rooms."""
    if sit_type != "discussion_room":
        return count
    cap = max(1, int(sit_cap))
    count = max(0, int(count))
    if event_blocks:
        return min(count, cap)
    demand = booking_demand(ts)
    if not demo_slot_booked(location_id, ts):
        weekday = ts.weekday()
        if weekday >= 5:
            empty_p = 0.62
        elif ts.hour < 10 or ts.hour >= 18:
            empty_p = 0.50
        else:
            empty_p = 0.40
        if demand > 1.2:
            empty_p *= 0.55
        if _unit01(f"emptyfree|{location_id}|{ts.date().isoformat()}|{ts.hour}") < empty_p:
            return 0
        if count > 0:
            return min(count, cap)
        if _unit01(f"walk|{location_id}|{ts.date().isoformat()}|{ts.hour}") < 0.16 * demand:
            extra = 1 + int(3 * _unit01(f"walkn|{location_id}|{ts.date().isoformat()}|{ts.hour}"))
            return min(cap, extra)
        return 0
    noshow_p = 0.14 if demand > 1.2 else 0.22
    if _unit01(f"noshow|{location_id}|{ts.date().isoformat()}|{ts.hour}") < noshow_p:
        return 1 if _unit01(f"left|{location_id}|{ts.date().isoformat()}|{ts.hour}") < 0.25 else 0
    used = _unit01(f"use|{location_id}|{ts.date().isoformat()}|{ts.hour}")
    people = max(2 if cap >= 2 else 1, int(round(cap * (0.30 + 0.55 * used))))
    if count >= 2:
        people = max(people, min(count, cap))
    return min(cap, people)


def type_vacancy(sit_type: str) -> float:
    """ROBOD peak-hour mean / type p95 is often high. Applied at generate time only."""
    if sit_type == "discussion_room":
        return 0.95
    if sit_type == "library":
        return 0.78
    if sit_type == "food_court":
        return 0.88
    return 0.62
