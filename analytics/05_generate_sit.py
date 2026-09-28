"""Generate SIT occupancy from occupancy v0 and the academic calendar overlay.

ROBOD contains no SIT trimesters. Recess, examinations, weekends, and IWSP
mix factors are applied after prediction using data/sample/sit_calendar.json.
Teaching / recess / examination dates follow the published SIT AY2026/27
Trimester 1 calendar. IWSP is a programme mix (East = IT courses; W3/W5 =
other courses; W1 library shared). OIP dates for 2026 are not published.

Run from the repository root (after 04_train.py):

    python analytics/05_generate_sit.py
    python src/db/init_app_db.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import joblib
import pandas as pd

_ANALYTICS = Path(__file__).resolve().parent
sys.path.insert(0, str(_ANALYTICS))
from occupancy_model import SIT_TYPE_MAP  # noqa: E402

ROOT = _ANALYTICS.parent
SAMPLE = ROOT / "data" / "sample"
MODEL_PATH = ROOT / "analytics" / "models" / "occupancy_v0.joblib"
CALENDAR = SAMPLE / "sit_calendar.json"
OCC_OUT = SAMPLE / "occupancy_generated.csv"
PRED_OUT = SAMPLE / "occupancy_prediction.csv"

AS_OF = datetime(2026, 9, 29, 15, 0, 0)
SGT = "+08:00"


def iso_sgt(ts: datetime) -> str:
    """ISO-8601 with explicit Singapore offset so clients do not treat the time as UTC midnight."""
    return ts.strftime("%Y-%m-%dT%H:%M:%S") + SGT


def load_calendar() -> dict:
    return json.loads(CALENDAR.read_text(encoding="utf-8"))


def parse_d(s: str) -> date:
    return date.fromisoformat(s)


def parse_instant(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")[:19])


def event_factor(location_id: str, ts: datetime, events: pd.DataFrame) -> float:
    """Raise occupancy when a seeded event overlaps this location and hour (sample ArtFest, etc.)."""
    if events.empty:
        return 1.0
    end = ts + timedelta(hours=1)
    hits = events[events["location_id"] == location_id]
    for _, ev in hits.iterrows():
        a = parse_instant(str(ev["start_time"]))
        b = parse_instant(str(ev["end_time"]))
        if a < end and b > ts:
            return 1.25
    return 1.0


def phase_for(d: date, cal: dict) -> dict | None:
    for p in cal["phases"]:
        if parse_d(p["start"]) <= d <= parse_d(p["end"]):
            return p
    return None


def away_multiplier(sit_type: str, building_id: str, d: date, cal: dict) -> float:
    m = 1.0
    for w in cal.get("away_windows", []):
        if not w.get("enabled", True):
            continue
        if parse_d(w["start"]) <= d <= parse_d(w["end"]):
            buildings = w.get("building_ids") or []
            types = w.get("types") or []
            if buildings and building_id not in buildings:
                continue
            if types and sit_type not in types:
                continue
            m *= float(w["multiplier"])
    return m


def holiday_dates(cal: dict) -> set[str]:
    dates = set(cal.get("holiday_dates") or [])
    for h in cal.get("holidays") or []:
        dates.add(str(h["date"]))
    return dates


def calendar_multiplier(sit_type: str, building_id: str, ts: datetime, cal: dict) -> float:
    """Scale utilisation by academic phase, weekend, Singapore public holiday, and IWSP mix."""
    d = ts.date()
    phase = phase_for(d, cal)
    if phase is None:
        return 0.15
    m = float(phase.get("multiplier", 1.0))
    type_m = phase.get("type_multipliers") or {}
    m *= float(type_m.get(sit_type, 1.0))
    if ts.weekday() >= 5:
        m *= float(cal.get("weekend_multiplier", 0.28))
    if d.isoformat() in holiday_dates(cal):
        m *= float(cal.get("holiday_multiplier", 0.18))
    m *= away_multiplier(sit_type, building_id, d, cal)
    return m


def main() -> None:
    if not MODEL_PATH.exists():
        raise SystemExit("Run python analytics/04_train.py first.")
    bundle = joblib.load(MODEL_PATH)
    model = bundle["pipeline"]
    p95 = bundle["room_type_p95"]
    type_map = bundle.get("sit_type_map", SIT_TYPE_MAP)
    version = bundle.get("model_version", "v0")
    cal = load_calendar()
    hours = [int(h) for h in cal.get("hours", list(range(8, 21)))]
    history_start = parse_d(cal.get("generate_start", "2026-08-31"))
    history_end = parse_d(cal.get("generate_end", "2026-12-27"))
    as_of = parse_instant(str(cal.get("predict_as_of") or cal.get("map_as_of") or "2026-09-29T15:00:00"))
    events = pd.read_csv(SAMPLE / "events.csv") if (SAMPLE / "events.csv").exists() else pd.DataFrame()

    locations = pd.read_csv(SAMPLE / "locations.csv")
    stamps = []
    d = history_start
    while d <= history_end:
        for h in hours:
            stamps.append(datetime(d.year, d.month, d.day, h, 0, 0))
        d += timedelta(days=1)

    rows = []
    for _, loc in locations.iterrows():
        robod_type = type_map.get(str(loc["type"]), "office")
        cap_hat = float(p95.get(robod_type, 10.0)) or 10.0
        sit_cap = int(loc["capacity"])
        X = pd.DataFrame(
            {
                "hour": [t.hour for t in stamps],
                "day_of_week": [min(t.weekday(), 4) for t in stamps],
                "room_type": robod_type,
            }
        )
        # ROBOD has no Saturday/Sunday rows: use Friday's hour profile, then apply weekend_multiplier.
        pred_count = model.predict(X)
        for ts, nus_count in zip(stamps, pred_count):
            ratio = max(0.0, float(nus_count) / cap_hat)
            ratio *= calendar_multiplier(str(loc["type"]), str(loc["building_id"]), ts, cal)
            ratio *= event_factor(str(loc["location_id"]), ts, events)
            ratio = min(ratio, 1.05)
            count = int(round(ratio * sit_cap))
            count = max(0, min(count, int(sit_cap * 1.05)))
            rows.append(
                {
                    "location_id": loc["location_id"],
                    "timestamp": iso_sgt(ts),
                    "occupancy_count": count,
                    "source": "generated",
                }
            )

    occ = pd.DataFrame(rows)
    occ.to_csv(OCC_OUT, index=False)
    print(f"Wrote {len(occ):,} occupancy rows -> {OCC_OUT.relative_to(ROOT)}")

    pred_hours = [as_of + timedelta(hours=1), as_of + timedelta(hours=2)]
    pred_rows = []
    for _, loc in locations.iterrows():
        robod_type = type_map.get(str(loc["type"]), "office")
        cap_hat = float(p95.get(robod_type, 10.0)) or 10.0
        sit_cap = int(loc["capacity"])
        X = pd.DataFrame(
            {
                "hour": [t.hour for t in pred_hours],
                "day_of_week": [min(t.weekday(), 4) for t in pred_hours],
                "room_type": robod_type,
            }
        )
        pred_count = model.predict(X)
        for ts, nus_count in zip(pred_hours, pred_count):
            ratio = max(0.0, float(nus_count) / cap_hat)
            ratio *= calendar_multiplier(str(loc["type"]), str(loc["building_id"]), ts, cal)
            ratio *= event_factor(str(loc["location_id"]), ts, events)
            ratio = min(ratio, 1.05)
            count = max(0, min(int(round(ratio * sit_cap)), int(sit_cap * 1.05)))
            pred_rows.append(
                {
                    "location_id": loc["location_id"],
                    "predicted_for": iso_sgt(ts),
                    "occupancy_count": count,
                    "model_version": version,
                }
            )
    pred = pd.DataFrame(pred_rows)
    pred.to_csv(PRED_OUT, index=False)
    print(f"Wrote {len(pred):,} prediction rows -> {PRED_OUT.relative_to(ROOT)}")
    print(
        f"{cal.get('academic_year')} Trimester {cal.get('trimester')}: "
        "AY2026/27 Trimester 1 series 31 Aug–27 Dec 2026 (teaching, recess, Deepavali, Christmas); "
        "IT-course IWSP mix on East discussion rooms; other courses on W3/W5; "
        "W1 library shared; OIP window disabled."
    )


if __name__ == "__main__":
    main()
