"""Appendix A submission preflight: structure (must pass) and completeness report."""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "project_manifest.yaml"

MANIFEST_KEYS = (
    "diagram",
    "functional_test",
    "security_test",
    "data_ai_test",
    "scale_resilience_test",
    "monitoring",
    "dataset",
    "threat_control_map",
    "ai_use",
    "contributions",
)

EXPECTED_MISSING: set[str] = set()

HEADING_CHECKS = (
    "objective",
    "setup",
    "command",
    "expected result",
    "actual result",
    "artefact path",
)

DATE_RE = re.compile(
    r"\b\d{1,2} (January|February|March|April|May|June|July|August|"
    r"September|October|November|December) 2026\b",
    re.IGNORECASE,
)

EVIDENCE_TEST_KEYS = (
    "functional_test",
    "security_test",
    "data_ai_test",
    "scale_resilience_test",
    "monitoring",
)


def _manifest_value(key: str) -> str | None:
    text = MANIFEST.read_text(encoding="utf-8")
    m = re.search(rf'^\s*{key}:\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else None


def _manifest_values() -> dict[str, str]:
    out: dict[str, str] = {}
    for key in MANIFEST_KEYS:
        val = _manifest_value(key)
        if val is None:
            raise ValueError(f"missing manifest key: {key}")
        out[key] = val
    return out


def _is_todo_template(content: str) -> bool:
    body = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return bool(body) and all("TODO" in line for line in body)


def _heading_ok(content: str, label: str) -> bool:
    return bool(
        re.search(
            rf"^#+\s*{re.escape(label)}(\s|/|$)",
            content,
            re.IGNORECASE | re.MULTILINE,
        )
    )


class SubmissionPreflightStructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = _manifest_values()

    def test_manifest_paths_exist(self) -> None:
        for key, rel in self.paths.items():
            path = ROOT / rel
            if rel in EXPECTED_MISSING:
                if path.is_file():
                    print(f"{rel}: present (was expected missing)")
                else:
                    print(f"{rel}: MISSING (expected)")
                continue
            self.assertTrue(path.is_file(), f"{key} -> {rel} missing")

    def test_required_root_files(self) -> None:
        required_files = [
            "README.md",
            "project_manifest.yaml",
            "TEAM_CONTRIBUTIONS.md",
            "AI_USE_DECLARATION.md",
            "data/DATA_DICTIONARY.md",
            "analytics/README.md",
            "analytics/requirements.txt",
        ]
        for name in required_files:
            self.assertTrue((ROOT / name).is_file(), name)
        for name in ("src", "data", "analytics", "evidence", "tests"):
            self.assertTrue((ROOT / name).is_dir(), name)

    def test_env_example_present(self) -> None:
        root_env = ROOT / ".env.example"
        src_env = ROOT / "src" / ".env.example"
        self.assertTrue(root_env.is_file() or src_env.is_file(), ".env.example missing")
        if root_env.is_file() and not src_env.is_file():
            print("NOTE: .env.example at repo root only (brief lists src/)")

    def test_four_tests_have_required_headings(self) -> None:
        for key in (
            "functional_test",
            "security_test",
            "data_ai_test",
            "scale_resilience_test",
        ):
            rel = self.paths[key]
            content = (ROOT / rel).read_text(encoding="utf-8")
            for label in HEADING_CHECKS:
                self.assertTrue(
                    _heading_ok(content, label),
                    f"{rel} missing heading: {label}",
                )
            if _is_todo_template(content):
                continue
            has_date = _heading_ok(content, "date") or bool(DATE_RE.search(content))
            self.assertTrue(has_date, f"{rel} missing Date heading or 2026 date")

    def test_manifest_test_files_are_distinct_paths(self) -> None:
        vals = [self.paths[k] for k in EVIDENCE_TEST_KEYS]
        self.assertEqual(len(vals), len(set(vals)))


class SubmissionPreflightCompletenessTest(unittest.TestCase):
    def test_completeness_report(self) -> None:
        paths = _manifest_values()
        open_items = 0
        for key in EVIDENCE_TEST_KEYS:
            rel = paths[key]
            todo_count = sum(
                1
                for line in (ROOT / rel).read_text(encoding="utf-8").splitlines()
                if "TODO" in line
            )
            status = "COMPLETE" if todo_count == 0 else f"OPEN ({todo_count} TODO)"
            if todo_count:
                open_items += 1
            print(f"{rel}: {status}")

        manifest_text = MANIFEST.read_text(encoding="utf-8")
        if 'group_id: "Gxxx"' in manifest_text:
            print("manifest group_id: still Gxxx")
            open_items += 1
        empty_students = len(re.findall(r'student_id:\s*""', manifest_text))
        print(f"manifest empty student_id count: {empty_students}")
        if empty_students:
            open_items += 1
        if re.search(r'repository_commit:\s*""', manifest_text):
            print("manifest repository_commit: empty")
            open_items += 1
        arch = ROOT / "evidence" / "architecture.png"
        print(
            f"evidence/architecture.png: {'present' if arch.is_file() else 'MISSING (expected until Kristen)'}"
        )
        if not arch.is_file():
            open_items += 1
        report = ROOT / "report.pdf"
        print(
            f"report.pdf: {'present' if report.is_file() else 'MISSING (expected until ZIP)'}"
        )
        if not report.is_file():
            open_items += 1
        video = ROOT / "video_link.txt"
        print(
            f"video_link.txt: {'present (optional)' if video.is_file() else 'absent (optional)'}"
        )

        print(f"PREFLIGHT SUMMARY: {open_items} open items")
        if os.environ.get("PREFLIGHT_STRICT") == "1":
            self.fail(f"PREFLIGHT_STRICT=1: {open_items} open items remain")


if __name__ == "__main__":
    unittest.main(verbosity=2)
