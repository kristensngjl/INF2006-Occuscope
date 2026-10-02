"""C8: crowd-band thresholds and generated seed columns (offline, stdlib)."""

from __future__ import annotations

import csv
import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analytics"))
from occupancy_model import demo_slot_booked, event_turnout  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "src" / "db" / "schema.sql").read_text(encoding="utf-8")
CONTRACT = (ROOT / "src" / "api-contract.md").read_text(encoding="utf-8")
GENERATED = ROOT / "data" / "sample" / "occupancy_generated.csv"
PREDICTION = ROOT / "data" / "sample" / "occupancy_prediction.csv"
LOCATIONS = ROOT / "data" / "sample" / "locations.csv"

QUIET_MAX = 0.30
MODERATE_MAX = 0.70


def crowd_level(ratio: float | None) -> str | None:
    if ratio is None:
        return None
    if ratio <= QUIET_MAX:
        return "quiet"
    if ratio <= MODERATE_MAX:
        return "moderate"
    return "crowded"


class CrowdBandTest(unittest.TestCase):
    def test_boundaries(self) -> None:
        self.assertEqual(crowd_level(0.0), "quiet")
        self.assertEqual(crowd_level(0.30), "quiet")
        self.assertEqual(crowd_level(0.31), "moderate")
        self.assertEqual(crowd_level(0.70), "moderate")
        self.assertEqual(crowd_level(0.71), "crowded")
        self.assertEqual(crowd_level(1.0), "crowded")

    def test_schema_and_contract_match(self) -> None:
        self.assertIn("<= 0.30 THEN 'quiet'", SCHEMA)
        self.assertIn("<= 0.70 THEN 'moderate'", SCHEMA)
        self.assertIn("≤ 0.30", CONTRACT)
        self.assertIn("≤ 0.70", CONTRACT)


class GeneratedSeedTest(unittest.TestCase):
    def test_location_ids_are_unique(self) -> None:
        with LOCATIONS.open(encoding="utf-8", newline="") as loc_f:
            ids = [row["location_id"] for row in csv.DictReader(loc_f)]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 64)
        self.assertIn("E4-01-FOODGLE", ids)
        self.assertIn("W3-02-WHOLESOME", ids)

    def test_occupancy_generated_columns_and_values(self) -> None:
        with GENERATED.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            self.assertEqual(
                reader.fieldnames,
                ["location_id", "timestamp", "occupancy_count", "source"],
            )
            with LOCATIONS.open(encoding="utf-8", newline="") as loc_f:
                ids = {row["location_id"] for row in csv.DictReader(loc_f)}
            n = 0
            for row in reader:
                n += 1
                self.assertIn(row["location_id"], ids)
                self.assertTrue(row["timestamp"].endswith("+08:00"))
                self.assertGreaterEqual(int(row["occupancy_count"]), 0)
                self.assertEqual(row["source"], "generated")
            self.assertGreater(n, 0)

    def test_every_location_has_full_generated_series(self) -> None:
        with LOCATIONS.open(encoding="utf-8", newline="") as loc_f:
            ids = {row["location_id"] for row in csv.DictReader(loc_f)}
        counts: dict[str, int] = {i: 0 for i in ids}
        extra = set()
        with GENERATED.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                lid = row["location_id"]
                if lid not in counts:
                    extra.add(lid)
                else:
                    counts[lid] += 1
        self.assertEqual(extra, set())
        missing = sorted(i for i, n in counts.items() if n == 0)
        self.assertEqual(missing, [])
        expected = next(iter(counts.values()))
        self.assertGreater(expected, 0)
        self.assertTrue(all(n == expected for n in counts.values()), "every location must have the same number of generated hours")

    def test_events_reference_seeded_locations(self) -> None:
        with LOCATIONS.open(encoding="utf-8", newline="") as loc_f:
            ids = {row["location_id"] for row in csv.DictReader(loc_f)}
        events = ROOT / "data" / "sample" / "events.csv"
        weeks = set()
        n = 0
        with events.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                n += 1
                self.assertIn(row["location_id"], ids, row["event_id"])
                self.assertNotIn("(sample)", row["title"].lower())
                self.assertTrue(row["end_time"] > row["start_time"], row["event_id"])
                weeks.add(row["start_time"][:10])
        self.assertGreaterEqual(n, 80)
        days = sorted(weeks)
        self.assertLessEqual(days[0], "2026-09-07")
        self.assertGreaterEqual(days[-1], "2026-12-01")

    def test_dummy_preview_covers_catalogue(self) -> None:
        preview = ROOT / "data" / "sample" / "occupancy_preview.csv"
        with LOCATIONS.open(encoding="utf-8", newline="") as loc_f:
            ids = {row["location_id"] for row in csv.DictReader(loc_f)}
        covered = set()
        with preview.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                self.assertEqual(row["source"], "dummy")
                covered.add(row["location_id"])
        self.assertEqual(ids - covered, set())
        self.assertEqual(covered - ids, set())

    def test_prediction_covers_every_location(self) -> None:
        with LOCATIONS.open(encoding="utf-8", newline="") as loc_f:
            ids = {row["location_id"] for row in csv.DictReader(loc_f)}
        covered = set()
        with PREDICTION.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                covered.add(row["location_id"])
        self.assertEqual(ids - covered, set())
        self.assertEqual(covered - ids, set())

    def test_prediction_columns(self) -> None:
        with PREDICTION.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            self.assertEqual(
                reader.fieldnames,
                ["location_id", "predicted_for", "occupancy_count", "model_version"],
            )
            row = next(reader)
            self.assertTrue(row["predicted_for"].endswith("+08:00"))
            self.assertEqual(row["model_version"], "v0")

    def test_peak_hour_discussion_rooms_are_not_identical(self) -> None:
        """v0 is hour×type; generate must still spread rooms so 15:00 is not all one band."""
        caps = {}
        types = {}
        with LOCATIONS.open(encoding="utf-8", newline="") as loc_f:
            for row in csv.DictReader(loc_f):
                caps[row["location_id"]] = int(row["capacity"])
                types[row["location_id"]] = row["type"]
        at = "2026-09-30T15:00:00+08:00"
        bands = set()
        counts = set()
        with GENERATED.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["timestamp"] != at:
                    continue
                if types.get(row["location_id"]) != "discussion_room":
                    continue
                n = int(row["occupancy_count"])
                cap = caps[row["location_id"]]
                ratio = n / cap
                counts.add(n)
                if ratio <= 0.30:
                    bands.add("quiet")
                elif ratio <= 0.70:
                    bands.add("moderate")
                else:
                    bands.add("crowded")
        self.assertGreaterEqual(len(counts), 3)
        self.assertGreaterEqual(len(bands), 2)

    def test_food_courts_follow_published_weekend_hours(self) -> None:
        """Foodgle stays open Sat/Sun; Wholesome Saturday lunch, closed Sunday (SIT Punggol hours)."""
        saturday_lunch = "2026-09-05T12:00:00+08:00"
        sunday_lunch = "2026-09-06T12:00:00+08:00"
        saturday_evening = "2026-09-05T16:00:00+08:00"
        found = {
            "foodgle_sat": None,
            "foodgle_sun": None,
            "wholesome_sat_lunch": None,
            "wholesome_sat_eve": None,
            "wholesome_sun": None,
        }
        with GENERATED.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                lid, ts, n = row["location_id"], row["timestamp"], int(row["occupancy_count"])
                if lid == "E4-01-FOODGLE" and ts == saturday_lunch:
                    found["foodgle_sat"] = n
                elif lid == "E4-01-FOODGLE" and ts == sunday_lunch:
                    found["foodgle_sun"] = n
                elif lid == "W3-02-WHOLESOME" and ts == saturday_lunch:
                    found["wholesome_sat_lunch"] = n
                elif lid == "W3-02-WHOLESOME" and ts == saturday_evening:
                    found["wholesome_sat_eve"] = n
                elif lid == "W3-02-WHOLESOME" and ts == sunday_lunch:
                    found["wholesome_sun"] = n
        self.assertTrue(all(v is not None for v in found.values()), found)
        self.assertGreater(found["foodgle_sat"], 20)
        self.assertGreater(found["foodgle_sun"], 20)
        self.assertGreater(found["wholesome_sat_lunch"], 15)
        self.assertLess(found["wholesome_sat_eve"], found["wholesome_sat_lunch"])
        self.assertLess(found["wholesome_sun"], 10)

    def test_event_turnout_is_mixed_and_not_read_from_titles(self) -> None:
        """Lunch on the calendar is not treated as crowded; hashed event_id decides turnout."""
        noon = datetime(2026, 10, 3, 12, 0, 0)
        factors = [event_turnout(f"E-{i:03d}", noon) for i in range(1, 208)]
        self.assertLess(min(factors), 0.95)
        self.assertGreater(max(factors), 1.05)
        busy = sum(1 for f in factors if f >= 1.15)
        self.assertLess(busy / len(factors), 0.30)
        self.assertNotEqual(event_turnout("E-007", noon), event_turnout("E-012", noon))
        self.assertAlmostEqual(event_turnout("E-012", noon), event_turnout("E-012", noon))

    def test_discussion_rooms_mix_booked_occupied_and_walk_ins(self) -> None:
        """Booked rooms usually have people; some bookings are empty; unbooked rooms can still be occupied."""
        at = datetime(2026, 9, 30, 15, 0, 0)
        stamp = "2026-09-30T15:00:00+08:00"
        morning = "2026-09-30T08:00:00+08:00"
        events = ROOT / "data" / "sample" / "events.csv"
        blocked = set()
        blocked_morning = set()
        with events.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["start_time"] < "2026-09-30T16:00:00+08:00" and row["end_time"] > stamp:
                    blocked.add(row["location_id"])
                if row["start_time"] < "2026-09-30T09:00:00+08:00" and row["end_time"] > morning:
                    blocked_morning.add(row["location_id"])
        rooms = {}
        with LOCATIONS.open(encoding="utf-8", newline="") as loc_f:
            for row in csv.DictReader(loc_f):
                if row["type"] == "discussion_room":
                    rooms[row["location_id"]] = int(row["capacity"])
        occ = {}
        occ_am = {}
        with GENERATED.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["location_id"] not in rooms:
                    continue
                if row["timestamp"] == stamp:
                    occ[row["location_id"]] = int(row["occupancy_count"])
                elif row["timestamp"] == morning:
                    occ_am[row["location_id"]] = int(row["occupancy_count"])
        booked_used = booked_empty = walk_in = free_empty = 0
        for lid in rooms:
            n = occ[lid]
            if lid in blocked:
                continue
            if demo_slot_booked(lid, at):
                if n >= 2:
                    booked_used += 1
                elif n <= 1:
                    booked_empty += 1
            elif n > 0:
                walk_in += 1
            else:
                free_empty += 1
        morning_empty = 0
        for lid in rooms:
            if lid in blocked_morning:
                continue
            if not demo_slot_booked(lid, datetime(2026, 9, 30, 8, 0, 0)) and occ_am[lid] == 0:
                morning_empty += 1
        self.assertGreaterEqual(booked_used, 8)
        self.assertGreaterEqual(booked_empty, 1)
        self.assertGreaterEqual(walk_in, 3)
        self.assertGreaterEqual(free_empty, 3)
        self.assertGreaterEqual(morning_empty, 3)

    def test_exams_raise_bookings_and_study_occupancy(self) -> None:
        """Weeks 12–14: more DR bookings; library/study headcount above a teaching Wednesday."""
        teaching = datetime(2026, 9, 30, 15, 0, 0)
        exams = datetime(2026, 12, 2, 15, 0, 0)
        rooms = {}
        with LOCATIONS.open(encoding="utf-8", newline="") as loc_f:
            for row in csv.DictReader(loc_f):
                rooms[row["location_id"]] = row["type"]
        drs = [lid for lid, t in rooms.items() if t == "discussion_room"]
        booked_teaching = sum(1 for lid in drs if demo_slot_booked(lid, teaching))
        booked_exams = sum(1 for lid in drs if demo_slot_booked(lid, exams))
        self.assertGreater(booked_exams, booked_teaching)
        teach_lib = exam_lib = 0
        n_lib = 0
        with GENERATED.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if rooms.get(row["location_id"]) != "library":
                    continue
                if row["timestamp"] == "2026-09-30T15:00:00+08:00":
                    teach_lib += int(row["occupancy_count"])
                    n_lib += 1
                elif row["timestamp"] == "2026-12-02T15:00:00+08:00":
                    exam_lib += int(row["occupancy_count"])
        self.assertGreater(n_lib, 5)
        self.assertGreater(exam_lib, teach_lib)


if __name__ == "__main__":
    unittest.main(verbosity=2)
