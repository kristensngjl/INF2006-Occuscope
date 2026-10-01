"""Shared v0 occupancy predictor (mean occupant count by hour and room type).

Imported by the training and generation scripts so joblib unpickles against this
module rather than `__main__`.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

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


def type_vacancy(sit_type: str) -> float:
    """ROBOD peak-hour mean / type p95 is often high. Real campuses still have empty
    discussion rooms at 15:00. Apply at generate time only — not a live booking feed."""
    if sit_type == "discussion_room":
        return 0.95
    if sit_type == "library":
        return 0.78
    return 0.62
