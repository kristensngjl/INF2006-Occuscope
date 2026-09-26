"""Repeatable check: secrets, raw NUS files, the brief PDF, and local notes stay gitignored."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

IGNORED_PATHS = (
    ".env",
    "data/raw/dummy.csv",
    "CLOUDPROJ.md",
    "INF2006_Team_Project_Brief_2026.pdf",
    "analytics/models/occupancy_v0.joblib",
    "liddy.md",
)

GITIGNORE_FALLBACK_NEEDLES = (
    ".env",
    "data/raw/*",
    "CLOUDPROJ.md",
    "Team_Project_Brief",
    "*.joblib",
    "liddy.md",
)


def _git_available() -> bool:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "true"


class GitignoreSecretsTest(unittest.TestCase):
    def test_env_example_secret_key_is_placeholder(self) -> None:
        text = (ROOT / ".env.example").read_text(encoding="utf-8")
        found = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            if key.strip() != "AWS_SECRET_ACCESS_KEY":
                continue
            found = True
            self.assertEqual(
                value.strip(),
                "",
                "AWS_SECRET_ACCESS_KEY must be empty in .env.example",
            )
        self.assertTrue(found, "AWS_SECRET_ACCESS_KEY missing from .env.example")

    def test_sensitive_paths_are_ignored(self) -> None:
        if _git_available():
            for rel in IGNORED_PATHS:
                proc = subprocess.run(
                    ["git", "check-ignore", "-q", rel],
                    cwd=ROOT,
                    check=False,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    f"{rel} should be gitignored (git check-ignore -q)",
                )
            return

        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for needle in GITIGNORE_FALLBACK_NEEDLES:
            self.assertIn(needle, gitignore, f".gitignore should mention {needle}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
