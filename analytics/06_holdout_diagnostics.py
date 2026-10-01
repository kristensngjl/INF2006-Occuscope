"""NUS hold-out extras: MAE slices, 7 vs 14-day window, persist vs v0, crowd-band counts.

Does not write SIT occupancy. Needs data/processed/robod_clean.csv (not data/raw/).

    python analytics/06_holdout_diagnostics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

_ANALYTICS = Path(__file__).resolve().parent
sys.path.insert(0, str(_ANALYTICS))
from occupancy_model import FEATURES, HourRoomTypeMean, TARGET

ROOT = _ANALYTICS.parent
CLEAN = ROOT / "data" / "processed" / "robod_clean.csv"
OUT = _ANALYTICS

QUIET_MAX = 0.30
MODERATE_MAX = 0.70


def load() -> pd.DataFrame:
    if not CLEAN.exists():
        raise SystemExit("Missing data/processed/robod_clean.csv. Rebuild with 02_clean_robod.py if you have data/raw/.")
    df = pd.read_csv(CLEAN, parse_dates=["timestamp"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["hour"] = df["hour"].astype(int)
    return df.dropna(subset=FEATURES + [TARGET, "room_id"])


def split_last_days(df: pd.DataFrame, n_days: int) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    dates = sorted(df["date"].unique())
    holdout = dates[-n_days:]
    train = df[~df["date"].isin(holdout)].copy()
    test = df[df["date"].isin(holdout)].copy()
    return train, test, holdout


def fit_v0(train: pd.DataFrame) -> HourRoomTypeMean:
    means = train.groupby(["hour", "room_type"], observed=True)[TARGET].mean()
    return HourRoomTypeMean(means, float(train[TARGET].mean()))


def score(y_true, y_pred) -> dict:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(mean_squared_error(y_true, y_pred) ** 0.5), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "n": int(len(y_true)),
    }


def band(ratio: float) -> str:
    if ratio <= QUIET_MAX:
        return "quiet"
    if ratio <= MODERATE_MAX:
        return "moderate"
    return "crowded"


def persist_join(df: pd.DataFrame, test: pd.DataFrame, hours: int) -> pd.DataFrame:
    lag = df[["room_id", "timestamp", TARGET]].rename(columns={TARGET: "persist"})
    lag = lag.copy()
    lag["timestamp"] = lag["timestamp"] + pd.Timedelta(hours=hours)
    return test.merge(lag, on=["room_id", "timestamp"], how="inner")


def main() -> None:
    df = load()
    train14, test14, hold14 = split_last_days(df, 14)
    v0 = fit_v0(train14)
    pred14 = v0.predict(test14[FEATURES])
    y14 = test14[TARGET]

    type_rows = []
    for room_type, part in test14.groupby("room_type"):
        hat = v0.predict(part[FEATURES])
        type_rows.append({"slice": "room_type", "key": room_type, **score(part[TARGET], hat)})
    hour_rows = []
    for hour, part in test14.groupby("hour"):
        hat = v0.predict(part[FEATURES])
        hour_rows.append({"slice": "hour", "key": str(int(hour)), **score(part[TARGET], hat)})
    by_slice = pd.DataFrame(type_rows + hour_rows)
    by_slice.to_csv(OUT / "metrics_mae_by_type_hour.csv", index=False)
    print("MAE by room type / hour (14-day hold-out, v0)")
    print(by_slice.to_string(index=False))

    window_rows = []
    for n in (14, 7):
        train, test, hold = split_last_days(df, n)
        model = fit_v0(train)
        hat = model.predict(test[FEATURES])
        window_rows.append(
            {
                "holdout_days": n,
                "holdout_start": str(hold[0]),
                "holdout_end": str(hold[-1]),
                "train_rows": len(train),
                "test_rows": len(test),
                **score(test[TARGET], hat),
            }
        )
    windows = pd.DataFrame(window_rows)
    windows.to_csv(OUT / "metrics_holdout_window.csv", index=False)
    print("\nHold-out window sensitivity (v0 refit)")
    print(windows.to_string(index=False))

    persist_rows = []
    for hours in (1, 2):
        joined = persist_join(df, test14, hours)
        hat = v0.predict(joined[FEATURES])
        persist_rows.append({"horizon_hours": hours, "model": "persist_last_count", **score(joined[TARGET], joined["persist"])})
        persist_rows.append({"horizon_hours": hours, "model": "v0_hour_type_mean", **score(joined[TARGET], hat)})
    persist = pd.DataFrame(persist_rows)
    persist.to_csv(OUT / "metrics_persist_vs_v0.csv", index=False)
    print("\nNext 1h / 2h on NUS hold-out (same rows)")
    print(persist.to_string(index=False))

    cap = train14.groupby("room_id")[TARGET].quantile(0.95).replace(0, pd.NA)
    test_b = test14.merge(cap.rename("capacity"), on="room_id", how="left")
    test_b = test_b.dropna(subset=["capacity"])
    test_b["ratio"] = (test_b[TARGET] / test_b["capacity"]).clip(lower=0)
    test_b["crowd_level"] = test_b["ratio"].map(band)
    band_rows = []
    for hour in (8, 15):
        part = test_b[test_b["hour"] == hour]
        counts = part["crowd_level"].value_counts()
        n = int(len(part))
        for label in ("quiet", "moderate", "crowded"):
            c = int(counts.get(label, 0))
            band_rows.append(
                {
                    "hour": hour,
                    "crowd_level": label,
                    "count": c,
                    "share": round(c / n, 4) if n else 0.0,
                    "n": n,
                }
            )
    bands = pd.DataFrame(band_rows)
    bands.to_csv(OUT / "metrics_nus_crowd_bands.csv", index=False)
    print("\nNUS hold-out crowd bands (room 95th pct as capacity; not SIT accuracy)")
    print(bands.to_string(index=False))
    print(f"14-day hold-out {hold14[0]} -> {hold14[-1]}; overall v0 MAE {score(y14, pred14)['mae']}")


if __name__ == "__main__":
    main()
