"""Shared v0 occupancy predictor (mean occupant count by hour and room type).

Imported by the training and generation scripts so joblib unpickles against this
module rather than `__main__`.
"""

from __future__ import annotations

import pandas as pd

FEATURES = ["hour", "day_of_week", "room_type"]
TARGET = "occupant_count"

SIT_TYPE_MAP = {
    # SIT location.type → ROBOD room_type used by v0.
    "discussion_room": "office",
    "library": "library",
    "lecture_theatre": "lecture",
    "food_court": "library",
    "office": "office",
    "other": "office",
}


class HourRoomTypeMean:
    """Mean occupant_count in training data for each (hour, room_type) pair."""

    def __init__(self, means: pd.Series, global_mean: float):
        self.means = means
        self.global_mean = float(global_mean)

    def predict(self, X: pd.DataFrame):
        key = list(zip(X["hour"].astype(int), X["room_type"].astype(str)))
        vals = [self.means.get(k, self.global_mean) for k in key]
        return pd.Series(vals, index=X.index).clip(lower=0).to_numpy()
