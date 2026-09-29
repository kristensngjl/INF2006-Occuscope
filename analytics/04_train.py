"""Train occupancy models on cleaned ROBOD; evaluate on a time hold-out.

Shuffling 5-minute rows would leak the next tick into training, so the last
14 distinct dates are held out. v0 features are hour, weekday, and room type
so the same inputs can be computed for SIT without NUS sensors.

C5 ablation (NUS hold-out only; never written to the app database):
Ridge / Random Forest with vs without ROBOD `wifi_connected_devices`, and with
a weekday×hour mean from Zenodo `5min` floors L2–L6 (2018, different building
and year — joined only on hour and weekday).

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
from sklearn.preprocessing import OneHotEncoder, StandardScaler

_ANALYTICS = Path(__file__).resolve().parent
sys.path.insert(0, str(_ANALYTICS))
from occupancy_model import FEATURES, HourRoomTypeMean, SIT_TYPE_MAP, TARGET

ROOT = _ANALYTICS.parent
CLEAN = ROOT / "data" / "processed" / "robod_clean.csv"
WIFI_XLSX = ROOT / "data" / "raw" / "raw_data.xlsx"
MODEL_DIR = ROOT / "analytics" / "models"
METRICS = ROOT / "analytics" / "metrics_holdout.csv"
ABLATION = ROOT / "analytics" / "metrics_wifi_ablation.csv"
MODEL_PATH = MODEL_DIR / "occupancy_v0.joblib"

RANDOM_STATE = 42
HOLD_OUT_DAYS = 14
WIFI_COL = "wifi_connected_devices"
FLOOR_COL = "nus_floor_wifi_hod"


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


def metrics(y_true, y_pred, name: str, features: str) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    return {
        "model": name,
        "features": features,
        "mae": round(float(mae), 4),
        "rmse": round(float(rmse), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "n_test": int(len(y_true)),
    }


def baseline_fit(train: pd.DataFrame) -> HourRoomTypeMean:
    means = train.groupby(["hour", "room_type"], observed=True)[TARGET].mean()
    return HourRoomTypeMean(means, float(train[TARGET].mean()))


def make_pipeline(estimator, extra_num: list[str] | None = None) -> Pipeline:
    transformers: list = [
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            FEATURES,
        )
    ]
    if extra_num:
        transformers.append(("num", StandardScaler(), extra_num))
    pre = ColumnTransformer(transformers, remainder="drop")
    return Pipeline([("pre", pre), ("est", estimator)])


def forest() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=20,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def fit_ridge_rf(train: pd.DataFrame, extra_num: list[str] | None) -> tuple[Pipeline, Pipeline]:
    cols = FEATURES + (extra_num or [])
    ridge = make_pipeline(Ridge(alpha=1.0), extra_num)
    ridge.fit(train[cols], train[TARGET])
    rf = make_pipeline(forest(), extra_num)
    rf.fit(train[cols], train[TARGET])
    return ridge, rf


def floor_hour_weekday_profile() -> pd.DataFrame | None:
    """Mean L2–L6 count by hour and weekday from Zenodo 5min (2018). Not room-level."""
    if not WIFI_XLSX.exists():
        return None
    raw = pd.read_excel(WIFI_XLSX, sheet_name="5min")
    time_col = "time" if "time" in raw.columns else raw.columns[0]
    floors = [c for c in ("L2", "L3", "L4", "L5", "L6") if c in raw.columns]
    if not floors:
        return None
    ts = pd.to_datetime(raw[time_col], errors="coerce")
    out = pd.DataFrame(
        {
            "hour": ts.dt.hour,
            "day_of_week": ts.dt.dayofweek,
            FLOOR_COL: raw[floors].mean(axis=1),
        }
    ).dropna()
    return (
        out.groupby(["hour", "day_of_week"], as_index=False)[FLOOR_COL]
        .mean()
    )


def eval_ridge_rf(
    train: pd.DataFrame,
    test: pd.DataFrame,
    extra_num: list[str] | None,
    feat_label: str,
) -> list[dict]:
    cols = FEATURES + (extra_num or [])
    ridge, rf = fit_ridge_rf(train, extra_num)
    y = test[TARGET]
    return [
        metrics(y, ridge.predict(test[cols]).clip(min=0), "ridge", feat_label),
        metrics(y, rf.predict(test[cols]).clip(min=0), "random_forest", feat_label),
    ]


def ablation(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Same hold-out dates; extra sensors stay out of v0 and out of occuscope.db."""
    rows: list[dict] = []
    feat0 = "hour+dow+type"
    wifi_train = train.dropna(subset=[WIFI_COL])
    wifi_test = test.dropna(subset=[WIFI_COL])
    if len(wifi_test) == 0 or len(wifi_train) == 0:
        print("C5 skip: no wifi_connected_devices on hold-out rows")
        return pd.DataFrame(rows)

    base = baseline_fit(wifi_train)
    rows.append(
        metrics(
            wifi_test[TARGET],
            base.predict(wifi_test[FEATURES]),
            "baseline_hour_roomtype_mean",
            feat0,
        )
    )
    rows.extend(eval_ridge_rf(wifi_train, wifi_test, None, feat0))
    rows.extend(
        eval_ridge_rf(wifi_train, wifi_test, [WIFI_COL], feat0 + "+robod_wifi")
    )

    profile = floor_hour_weekday_profile()
    if profile is None:
        print("C5: Zenodo 5min not found or has no L2–L6; skipped floor-wifi join")
        return pd.DataFrame(rows)

    tr = wifi_train.merge(profile, on=["hour", "day_of_week"], how="left")
    te = wifi_test.merge(profile, on=["hour", "day_of_week"], how="left")
    tr = tr.dropna(subset=[FLOOR_COL])
    te = te.dropna(subset=[FLOOR_COL])
    if len(te) == 0:
        print("C5: floor-wifi profile did not match hold-out hours")
        return pd.DataFrame(rows)
    rows.extend(
        eval_ridge_rf(tr, te, [FLOOR_COL], feat0 + "+zenodo_5min_hod")
    )
    rows.extend(
        eval_ridge_rf(
            tr, te, [WIFI_COL, FLOOR_COL], feat0 + "+robod_wifi+zenodo_5min_hod"
        )
    )
    return pd.DataFrame(rows)


def main() -> None:
    df = load()
    train, test, holdout = time_split(df)
    y_test = test[TARGET]
    print(f"train rows={len(train):,}  test rows={len(test):,}")
    print(f"hold-out dates {holdout[0]} -> {holdout[-1]} ({len(holdout)} days)")

    feat0 = "hour+dow+type"
    baseline = baseline_fit(train)
    rows = [
        metrics(y_test, baseline.predict(test[FEATURES]), "baseline_hour_roomtype_mean", feat0)
    ]
    rows.extend(eval_ridge_rf(train, test, None, feat0))

    table = pd.DataFrame(rows).sort_values("mae")
    print("\nv0 comparison (transferable features only):")
    print(table.to_string(index=False))
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(METRICS, index=False)
    print(f"Wrote {METRICS.relative_to(ROOT)}")

    winner_name = str(table.iloc[0]["model"])
    ridge, rf = fit_ridge_rf(train, None)
    pipelines = {
        "baseline_hour_roomtype_mean": baseline,
        "ridge": ridge,
        "random_forest": rf,
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

    print("\nC5 Wi-Fi ablation (not loaded into occuscope.db):")
    abl = ablation(train, test)
    if not abl.empty:
        abl = abl.sort_values("mae")
        print(abl.to_string(index=False))
        abl.to_csv(ABLATION, index=False)
        print(f"Wrote {ABLATION.relative_to(ROOT)}")
        best = abl.iloc[0]
        v0_mae = float(table.loc[table["model"] == "baseline_hour_roomtype_mean", "mae"].iloc[0])
        if best["model"] != "baseline_hour_roomtype_mean" and float(best["mae"]) < v0_mae:
            print(
                "NUS MAE improved with extra Wi-Fi features, but v0 stays hour×type "
                "because SIT has no matching Wi-Fi feed."
            )
        else:
            print("Extra Wi-Fi features did not beat the transferable hour×type mean on MAE.")


if __name__ == "__main__":
    main()
