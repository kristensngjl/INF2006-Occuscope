"""Train occupancy models on cleaned ROBOD; evaluate on a time hold-out.

Shuffling 5-minute rows would leak the next tick into training, so the last
14 distinct dates are held out. Features are restricted to hour, weekday, and
room type so the same inputs can be computed for SIT without NUS sensors.
Wi-Fi and CO2 are omitted from v0 (optional later ablation).

Run from the repository root:

    python analytics/04_train.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

_ANALYTICS = Path(__file__).resolve().parent
sys.path.insert(0, str(_ANALYTICS))
from occupancy_model import FEATURES, HourRoomTypeMean, SIT_TYPE_MAP, TARGET

ROOT = _ANALYTICS.parent
CLEAN = ROOT / "data" / "processed" / "robod_clean.csv"
MODEL_DIR = ROOT / "analytics" / "models"
METRICS = ROOT / "analytics" / "metrics_holdout.csv"
MODEL_PATH = MODEL_DIR / "occupancy_v0.joblib"

RANDOM_STATE = 42
HOLD_OUT_DAYS = 14


def load() -> pd.DataFrame:
    if not CLEAN.exists():
        raise SystemExit("Run python analytics/02_clean_robod.py first.")
    df = pd.read_csv(CLEAN, parse_dates=["timestamp"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["hour"] = df["hour"].astype(int)
    df["day_of_week"] = df["day_of_week"].astype(int)
    return df.dropna(subset=FEATURES + [TARGET])


def time_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    dates = sorted(df["date"].unique())
    if len(dates) <= HOLD_OUT_DAYS + 5:
        raise SystemExit(f"Not enough distinct days ({len(dates)}) for a {HOLD_OUT_DAYS}-day hold-out.")
    holdout = dates[-HOLD_OUT_DAYS:]
    train = df[~df["date"].isin(holdout)].copy()
    test = df[df["date"].isin(holdout)].copy()
    return train, test, holdout


def metrics(y_true, y_pred, name: str) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    return {
        "model": name,
        "mae": round(float(mae), 4),
        "rmse": round(float(rmse), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def baseline_fit(train: pd.DataFrame) -> HourRoomTypeMean:
    means = train.groupby(["hour", "room_type"], observed=True)[TARGET].mean()
    return HourRoomTypeMean(means, float(train[TARGET].mean()))


def make_pipeline(estimator) -> Pipeline:
    pre = ColumnTransformer(
        [
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                FEATURES,
            )
        ]
    )
    return Pipeline([("pre", pre), ("est", estimator)])


def main() -> None:
    df = load()
    train, test, holdout = time_split(df)
    y_test = test[TARGET]
    print(f"train rows={len(train):,}  test rows={len(test):,}")
    print(f"hold-out dates {holdout[0]} -> {holdout[-1]} ({len(holdout)} days)")

    baseline = baseline_fit(train)
    rows = [metrics(y_test, baseline.predict(test[FEATURES]), "baseline_hour_roomtype_mean")]

    ridge = make_pipeline(Ridge(alpha=1.0))
    ridge.fit(train[FEATURES], train[TARGET])
    rows.append(metrics(y_test, ridge.predict(test[FEATURES]).clip(min=0), "ridge"))

    forest = make_pipeline(
        RandomForestRegressor(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=20,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
    )
    forest.fit(train[FEATURES], train[TARGET])
    rows.append(metrics(y_test, forest.predict(test[FEATURES]).clip(min=0), "random_forest"))

    table = pd.DataFrame(rows).sort_values("mae")
    print(table.to_string(index=False))
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(METRICS, index=False)
    print(f"Wrote {METRICS.relative_to(ROOT)}")

    winner_name = str(table.iloc[0]["model"])
    pipelines = {
        "baseline_hour_roomtype_mean": baseline,
        "ridge": ridge,
        "random_forest": forest,
    }
    winner = pipelines[winner_name]

    cap = train.groupby("room_type")[TARGET].quantile(0.95).round(2).to_dict()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model_version": "v0",
            "pipeline": winner,
            "features": FEATURES,
            "target": TARGET,
            "winner": winner_name,
            "room_type_p95": cap,
            "holdout_days": HOLD_OUT_DAYS,
            "random_state": RANDOM_STATE,
            "sit_type_map": SIT_TYPE_MAP,
        },
        MODEL_PATH,
    )
    print(f"Saved winner={winner_name} -> {MODEL_PATH.relative_to(ROOT)}")
    print("room_type 95th pct (train, for later SIT scaling):", cap)


if __name__ == "__main__":
    main()
