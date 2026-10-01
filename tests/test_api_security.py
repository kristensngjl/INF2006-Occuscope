"""Named threat: client cannot forge crowd_level; API is read-only and fails closed (offline, local SQLite)."""

from __future__ import annotations

import csv
import sqlite3
import sys
import unittest
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "occuscope.db"
LOCATIONS_CSV = ROOT / "data" / "sample" / "locations.csv"
DEMO_AT = "2026-09-30T15:00:00+08:00"
KNOWN_ID = "E2-03-07-DR209"

QUIET_MAX = 0.30
MODERATE_MAX = 0.70

try:
    from fastapi.testclient import TestClient

    from src.backend.api import create_app

    _IMPORT_ERROR: str | None = None
except ImportError as exc:
    TestClient = None  # type: ignore[misc, assignment]
    create_app = None  # type: ignore[misc, assignment]
    _IMPORT_ERROR = (
        "Install API and test deps: pip install -r src/backend/requirements.txt "
        "-r tests/requirements-test.txt"
    )


def _skip_if_unavailable() -> None:
    if _IMPORT_ERROR:
        raise unittest.SkipTest(_IMPORT_ERROR)
    if not DB_PATH.is_file():
        raise unittest.SkipTest(
            "Missing data/occuscope.db — run: python src/db/init_app_db.py"
        )


def _location_row_count() -> int:
    with LOCATIONS_CSV.open(encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def _expected_crowd(occupancy_count: int | None, capacity: int) -> str | None:
    if occupancy_count is None:
        return None
    ratio = occupancy_count / capacity
    if ratio <= QUIET_MAX:
        return "quiet"
    if ratio <= MODERATE_MAX:
        return "moderate"
    return "crowded"


def _make_client() -> TestClient:
    return TestClient(create_app(DB_PATH))


class ApiSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _skip_if_unavailable()
        cls.client = _make_client()

    def test_current_requires_at(self) -> None:
        r = self.client.get("/occupancy/current")
        self.assertEqual(r.status_code, 422)

    def test_current_rejects_time_without_offset(self) -> None:
        r = self.client.get("/occupancy/current", params={"at": "2026-09-30T15:00:00"})
        self.assertEqual(r.status_code, 422)
        r2 = self.client.get("/occupancy/current", params={"at": "not-a-date"})
        self.assertEqual(r2.status_code, 422)

    def test_current_rows_match_thresholds(self) -> None:
        requested = datetime.fromisoformat(DEMO_AT)
        r = self.client.get("/occupancy/current", params={"at": DEMO_AT})
        self.assertEqual(r.status_code, 200)
        rows = r.json()
        self.assertEqual(len(rows), _location_row_count())
        any_crowd = False
        for row in rows:
            count = row.get("occupancy_count")
            capacity = row["capacity"]
            ratio = row.get("occupancy_ratio")
            crowd = row.get("crowd_level")
            if count is None:
                self.assertIsNone(crowd)
                self.assertIsNone(ratio)
            else:
                self.assertIsNotNone(ratio)
                expected = _expected_crowd(int(count), int(capacity))
                self.assertEqual(crowd, expected)
                self.assertEqual(row.get("source"), "generated")
                if crowd is not None:
                    any_crowd = True
            ts = row.get("timestamp")
            if ts is not None:
                self.assertLessEqual(datetime.fromisoformat(ts), requested)
        self.assertTrue(any_crowd, "expected at least one populated crowd_level at demo instant")

    def test_client_cannot_supply_crowd_level(self) -> None:
        base = self.client.get("/occupancy/current", params={"at": DEMO_AT})
        self.assertEqual(base.status_code, 200)
        baseline = base.json()
        for extra in (
            {"at": DEMO_AT, "crowd_level": "crowded"},
            {"at": DEMO_AT, "crowd_level": "quiet"},
            {"at": DEMO_AT, "colour": "red"},
        ):
            r = self.client.get("/occupancy/current", params=extra)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json(), baseline)

    def test_unknown_location_is_404(self) -> None:
        bad = "NOPE-00-00-XX"
        self.assertEqual(self.client.get(f"/locations/{bad}").status_code, 404)
        self.assertEqual(
            self.client.get(
                f"/occupancy/{bad}/prediction", params={"at": DEMO_AT}
            ).status_code,
            404,
        )
        r = self.client.get(
            f"/occupancy/{bad}",
            params={
                "from": "2026-09-30T00:00:00+08:00",
                "to": "2026-10-01T00:00:00+08:00",
            },
        )
        self.assertEqual(r.status_code, 404)

    def test_injection_style_id_is_404_not_500(self) -> None:
        for bad in ("x' OR '1'='1", "1; DROP TABLE location;--"):
            r = self.client.get("/locations/" + quote(bad, safe=""))
            self.assertEqual(r.status_code, 404, msg=bad)
            self.assertNotEqual(r.status_code, 500)
        buildings = self.client.get("/buildings")
        self.assertEqual(buildings.status_code, 200)
        self.assertGreaterEqual(len(buildings.json()), 1)

    def test_timeline_range_rules(self) -> None:
        params = {
            "from": "2026-09-30T00:00:00+08:00",
            "to": "2026-10-01T00:00:00+08:00",
        }
        r = self.client.get(f"/occupancy/{KNOWN_ID}", params=params)
        self.assertEqual(r.status_code, 200)
        items = r.json()
        self.assertLessEqual(len(items), 13)
        for item in items:
            self.assertEqual(item.get("source"), "generated")
        same = {
            "from": "2026-09-30T00:00:00+08:00",
            "to": "2026-09-30T00:00:00+08:00",
        }
        self.assertEqual(
            self.client.get(f"/occupancy/{KNOWN_ID}", params=same).status_code, 422
        )
        eight_days = {
            "from": "2026-09-30T00:00:00+08:00",
            "to": "2026-10-08T00:00:00+08:00",
        }
        self.assertEqual(
            self.client.get(f"/occupancy/{KNOWN_ID}", params=eight_days).status_code, 422
        )
        missing_to = {"from": "2026-09-30T00:00:00+08:00"}
        self.assertEqual(
            self.client.get(f"/occupancy/{KNOWN_ID}", params=missing_to).status_code, 422
        )

    def test_prediction_shape(self) -> None:
        r = self.client.get(
            f"/occupancy/{KNOWN_ID}/prediction", params={"at": DEMO_AT}
        )
        self.assertEqual(r.status_code, 200)
        items = r.json()
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 1)
        self.assertLessEqual(len(items), 2)
        missing = self.client.get(f"/occupancy/{KNOWN_ID}/prediction")
        self.assertEqual(missing.status_code, 422)

    def test_no_write_routes(self) -> None:
        paths = self.client.app.openapi()["paths"]
        for path, ops in paths.items():
            for method in ops:
                if method == "parameters":
                    continue
                self.assertEqual(method.lower(), "get", msg=f"{method.upper()} {path}")
        for method in ("post", "put", "patch", "delete"):
            for path in ("/occupancy/current", "/locations"):
                r = getattr(self.client, method)(path)
                self.assertIn(r.status_code, (404, 405), msg=f"{method} {path}")
                self.assertFalse(200 <= r.status_code < 300)

    def test_db_is_read_only(self) -> None:
        uri = DB_PATH.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute(
                    "INSERT INTO building(building_id, name) VALUES ('ZZ','zz')"
                )
        with sqlite3.connect(uri, uri=True) as conn:
            row = conn.execute(
                "SELECT 1 FROM building WHERE building_id = 'ZZ'"
            ).fetchone()
        self.assertIsNone(row)


if __name__ == "__main__":
    unittest.main(verbosity=2)
