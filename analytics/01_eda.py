"""Inspect NUS files under data/raw/ and write a dummy SIT occupancy preview.

This is not the trained model. `source` is always `dummy` so the app DB and
API can be wired before transfer learning exists.

Run from the repo root:

    python analytics/01_eda.py
    python src/db/init_app_db.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SAMPLE = ROOT / "data" / "sample"
OUT = SAMPLE / "occupancy_preview.csv"


def list_raw_files() -> list[Path]:
    return [p for p in RAW.rglob("*") if p.is_file() and p.name != ".gitkeep"]


def load_locations() -> pd.DataFrame:
    path = SAMPLE / "locations.csv"
    if not path.exists():
        raise SystemExit(f"Missing {path}")
    return pd.read_csv(path)


def dummy_sit_occupancy(locations: pd.DataFrame) -> pd.DataFrame:
    """Weekday-shaped stub occupancy (08:00–20:00) scaled to each room capacity."""
    hours = list(range(8, 21))
    rows = []
    for _, loc in locations.iterrows():
        cap = int(loc["capacity"])
        for hour in hours:
            base = 0.25 if loc["type"] == "discussion_room" else 0.45
            if 12 <= hour <= 13:
                base += 0.2
            if 16 <= hour <= 18:
                base += 0.15
            if loc["type"] == "library":
                base += 0.1
            count = min(cap, max(0, int(round(cap * base))))
            rows.append(
                {
                    "location_id": loc["location_id"],
                    "timestamp": f"2026-09-23T{hour:02d}:00:00",
                    "occupancy_count": count,
                    "source": "dummy",
                }
            )
    return pd.DataFrame(rows)


def inspect_raw(files: list[Path]) -> None:
    """Print path, columns, and first row so DATA_DICTIONARY.md can stay accurate."""
    print(f"Found {len(files)} file(s) under data/raw:")
    for path in files:
        print(f"  - {path.relative_to(ROOT)}")
        if path.suffix.lower() in {".csv", ".tsv"}:
            df = pd.read_csv(path, nrows=5)
            print(f"    columns: {list(df.columns)}")
            print(f"    first row: {df.iloc[0].to_dict() if len(df) else '{}'}")
        else:
            print("    (xlsx/other — see data/DATA_DICTIONARY.md; use raw_data.xlsx sheet 5min)")


def main() -> None:
    SAMPLE.mkdir(parents=True, exist_ok=True)
    files = list_raw_files()
    if files:
        inspect_raw(files)
        print(
            "\nRaw files present. Next analytics step: train/evaluate on NUS, "
            "then write generated SIT occupancy (source=generated) instead of dummy."
        )
    else:
        print(
            "data/raw is empty. Download ROBOD CSVs and NUS Wi-Fi xlsx "
            "(see data/README.md). Writing dummy occupancy so the app DB can still seed."
        )

    locations = load_locations()
    preview = dummy_sit_occupancy(locations)
    preview.to_csv(OUT, index=False)
    print(f"Wrote {len(preview)} rows -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
