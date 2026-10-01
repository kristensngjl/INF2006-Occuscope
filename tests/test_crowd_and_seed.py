"""C8: crowd-band thresholds and generated seed columns (offline, stdlib)."""

from __future__ import annotations

import csv
import unittest
from pathlib import Path

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
        with events.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                self.assertIn(row["location_id"], ids, row["event_id"])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
