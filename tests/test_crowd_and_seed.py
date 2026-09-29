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


if __name__ == "__main__":
    unittest.main(verbosity=2)
