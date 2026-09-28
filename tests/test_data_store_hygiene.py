"""B7: NUS training files stay out of git and out of the application database."""

from __future__ import annotations

import sqlite3
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = (ROOT / "src" / "db" / "init_app_db.py").read_text(encoding="utf-8")
SCHEMA = (ROOT / "src" / "db" / "schema.sql").read_text(encoding="utf-8")

FORBIDDEN_TRACKED = (
    "CLOUDPROJ.md",
    "INF2006_Team_Project_Brief_2026.pdf",
    "data/occuscope.db",
    "analytics/models/occupancy_v0.joblib",
    ".env",
)


class DataStoreHygieneTest(unittest.TestCase):
    def test_init_does_not_read_raw(self) -> None:
        self.assertNotIn('ROOT / "data" / "raw"', INIT)
        self.assertIn("SAMPLE", INIT)
        self.assertIn("read_csv", INIT)

    def test_schema_is_sit_app_only(self) -> None:
        self.assertIn("SIT Punggol", SCHEMA)
        self.assertNotIn("create table if not exists robod", SCHEMA.lower())
        self.assertIn("CREATE TABLE IF NOT EXISTS occupancy", SCHEMA)

    def test_forbidden_paths_not_tracked(self) -> None:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            self.skipTest("git ls-files unavailable")
        tracked = set(proc.stdout.splitlines())
        for rel in FORBIDDEN_TRACKED:
            self.assertNotIn(rel, tracked, f"{rel} must not be in git")
        for line in tracked:
            self.assertFalse(
                line.startswith("data/raw/") and line != "data/raw/.gitkeep",
                f"NUS raw file is tracked: {line}",
            )
            self.assertFalse(line.endswith(".db"), f"database is tracked: {line}")
            self.assertFalse(line.endswith(".joblib"), f"joblib is tracked: {line}")

    def test_local_db_has_only_app_sources(self) -> None:
        db = ROOT / "data" / "occuscope.db"
        if not db.exists():
            self.skipTest("occuscope.db not built (run python src/db/init_app_db.py)")
        conn = sqlite3.connect(db)
        names = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        self.assertNotIn("robod", {n.lower() for n in names})
        sources = {
            r[0]
            for r in conn.execute("SELECT DISTINCT source FROM occupancy").fetchall()
        }
        self.assertTrue(sources <= {"dummy", "generated", "model"})
        conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
