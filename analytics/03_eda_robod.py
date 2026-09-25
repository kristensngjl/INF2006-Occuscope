"""Exploratory figures on cleaned ROBOD for the report and data/AI test.

Does not write to the application database.

Run from the repository root (after 02_clean_robod.py):

    python analytics/03_eda_robod.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "processed" / "robod_clean.csv"
FIG = ROOT / "analytics" / "figures"

ROOM_TYPE_ORDER = ["lecture", "office", "library"]


def load() -> pd.DataFrame:
    if not CLEAN.exists():
        raise SystemExit("Run python analytics/02_clean_robod.py first.")
    df = pd.read_csv(CLEAN, parse_dates=["timestamp"])
    df["room_type"] = pd.Categorical(df["room_type"], ROOM_TYPE_ORDER, ordered=True)
    return df


def save(fig: plt.Figure, name: str) -> Path:
    FIG.mkdir(parents=True, exist_ok=True)
    path = FIG / name
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    print(f"  {path.relative_to(ROOT)}")
    return path


def plot_hourly(df: pd.DataFrame) -> None:
    hourly = df.groupby(["room_type", "hour"], observed=True)["occupant_count"].mean().unstack(0)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    hourly.plot(ax=ax)
    ax.set_title("Mean occupant count by hour of day (ROBOD)")
    ax.set_xlabel("Hour (SGT)")
    ax.set_ylabel("Mean occupants")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(title="Room type")
    ax.grid(True, alpha=0.3)
    save(fig, "robod_occupancy_by_hour.png")


def plot_by_weekday(df: pd.DataFrame) -> None:
    labels = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    g = df.groupby(["room_type", "day_of_week"], observed=True)["occupant_count"].mean().unstack(0)
    g.index = [labels.get(i, i) for i in g.index]
    fig, ax = plt.subplots(figsize=(7, 4))
    g.plot(kind="bar", ax=ax)
    ax.set_title("Mean occupant count by weekday (ROBOD has no Sat/Sun rows)")
    ax.set_xlabel("Day")
    ax.set_ylabel("Mean occupants")
    ax.legend(title="Room type")
    ax.grid(True, axis="y", alpha=0.3)
    save(fig, "robod_by_weekday.png")


def plot_lecture_vs_library(df: pd.DataFrame) -> None:
    sub = df[df["room_type"].isin(["lecture", "library"])]
    hourly = sub.groupby(["room_type", "hour"], observed=True)["occupant_count"].mean().unstack(0)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    hourly.plot(ax=ax)
    ax.set_title("Lecture vs library — mean occupants by hour (ROBOD)")
    ax.set_xlabel("Hour (SGT)")
    ax.set_ylabel("Mean occupants")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(title="Room type")
    ax.grid(True, alpha=0.3)
    save(fig, "robod_lecture_vs_library.png")


def plot_wifi_vs_occupancy(df: pd.DataFrame) -> None:
    sample = df.dropna(subset=["wifi_connected_devices"]).sample(
        n=min(8000, len(df)), random_state=0
    )
    fig, ax = plt.subplots(figsize=(6, 4.5))
    for room_type, part in sample.groupby("room_type", observed=True):
        ax.scatter(
            part["wifi_connected_devices"],
            part["occupant_count"],
            s=8,
            alpha=0.25,
            label=str(room_type),
        )
    ax.set_title("Wi-Fi devices vs occupant count (ROBOD sample)")
    ax.set_xlabel("wifi_connected_devices")
    ax.set_ylabel("occupant_count")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "robod_wifi_vs_occupancy.png")


def print_stats(df: pd.DataFrame) -> dict:
    stats = {
        "n_rows": int(len(df)),
        "date_min": str(df["date"].min()),
        "date_max": str(df["date"].max()),
        "mean_by_type": df.groupby("room_type", observed=True)["occupant_count"]
        .mean()
        .round(2)
        .to_dict(),
        "max_by_type": df.groupby("room_type", observed=True)["occupant_count"].max().to_dict(),
        "weekday_mean": round(df.loc[df["is_weekend"] == 0, "occupant_count"].mean(), 2),
        "weekend_rows": int((df["is_weekend"] == 1).sum()),
        "wifi_corr": round(
            df[["wifi_connected_devices", "occupant_count"]].corr().iloc[0, 1], 3
        ),
        "peak_hour_by_type": df.groupby(["room_type", "hour"], observed=True)["occupant_count"]
        .mean()
        .groupby(level=0)
        .idxmax()
        .apply(lambda x: int(x[1]))
        .to_dict(),
    }
    print("n_rows", stats["n_rows"], stats["date_min"], "->", stats["date_max"])
    print("mean_by_type", stats["mean_by_type"])
    print("weekday_mean", stats["weekday_mean"], "weekend_rows", stats["weekend_rows"])
    print("wifi_vs_count corr", stats["wifi_corr"])
    print("peak_hour_by_type", stats["peak_hour_by_type"])
    return stats


def main() -> None:
    df = load()
    print("Figures:")
    plot_hourly(df)
    plot_by_weekday(df)
    plot_lecture_vs_library(df)
    plot_wifi_vs_occupancy(df)
    print_stats(df)


if __name__ == "__main__":
    main()
