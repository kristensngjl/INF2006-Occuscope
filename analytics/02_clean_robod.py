"""Clean ROBOD room CSVs into one training table.

HVAC and weather columns are dropped. Room identity and type are taken from
the source filename (they are not columns in ROBOD). Timestamps are converted
to Asia/Singapore. Occupant counts are coerced to non-negative integers.
This script does not write to the application database.

Run from the repository root:

    python analytics/02_clean_robod.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"
OUT = OUT_DIR / "robod_clean.csv"

# Room type is the filename, not a column in ROBOD.
ROOM_META = {
    1: ("R1", "lecture"),
    2: ("R2", "lecture"),
    3: ("R3", "office"),
    4: ("R4", "office"),
    5: ("R5", "library"),
}

KEEP = [
    "timestamp",
    "occupant_count",
    "occupant_presence",
    "wifi_connected_devices",
    "indoor_co2",
    "air_temperature",
    "indoor_relative_humidity",
]


def load_room(room_no: int) -> pd.DataFrame:
    path = RAW / f"combined_Room{room_no}.csv"
    if not path.exists():
        raise SystemExit(f"Missing {path}. See data/README.md.")
    df = pd.read_csv(path)
    missing = [c for c in KEEP if c not in df.columns]
    if missing:
        raise SystemExit(f"{path.name} missing columns: {missing}")
    room_id, room_type = ROOM_META[room_no]
    out = df.loc[:, KEEP].copy()
    out.insert(1, "room_id", room_id)
    out.insert(2, "room_type", room_type)
    return out


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Singapore")
    for col in (
        "occupant_count",
        "occupant_presence",
        "wifi_connected_devices",
        "indoor_co2",
        "air_temperature",
        "indoor_relative_humidity",
    ):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["timestamp", "occupant_count"])
    df["occupant_count"] = df["occupant_count"].clip(lower=0).round().astype(int)
    df["occupant_presence"] = df["occupant_presence"].fillna(0).clip(0, 1).astype(int)
    df = df.drop_duplicates(subset=["room_id", "timestamp"], keep="first")

    local = df["timestamp"].dt.tz_localize(None)
    df["hour"] = local.dt.hour
    df["day_of_week"] = local.dt.dayofweek  # Mon=0
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["date"] = local.dt.date.astype(str)

    df = df.sort_values(["room_id", "timestamp"]).reset_index(drop=True)
    return df


def main() -> None:
    frames = [load_room(n) for n in sorted(ROOM_META)]
    raw = pd.concat(frames, ignore_index=True)
    cleaned = clean(raw)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(OUT, index=False)
    print(f"Wrote {len(cleaned):,} rows -> {OUT.relative_to(ROOT)}")
    print(cleaned.groupby(["room_id", "room_type"]).size().to_string())
    print("occupant_count by room_type:")
    print(cleaned.groupby("room_type")["occupant_count"].agg(["mean", "median", "max"]).to_string())


if __name__ == "__main__":
    main()
