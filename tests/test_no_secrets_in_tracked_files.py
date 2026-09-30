"""No credentials, deployed URLs or AWS account IDs in tracked or uncommitted files (offline, stdlib)."""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2 * 1024 * 1024
SKIP_PATHS = {
    "tests/test_no_secrets_in_tracked_files.py",
    "tests/test_gitignore_secrets.py",
    ".env.example",
}

PATTERNS: dict[str, re.Pattern[str]] = {
    "aws-access-key-id": re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    "aws-secret-assignment": re.compile(
        r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{20,}"
    ),
    "private-key-block": re.compile(
        r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
    ),
    "aws-account-in-arn": re.compile(
        r"arn:aws[a-z-]*:[a-z0-9-]*:[a-z0-9-]*:\d{12}:"
    ),
    "deployed-api-url": re.compile(
        r"https?://[a-z0-9]+\.execute-api\.[a-z0-9-]+\.amazonaws\.com"
    ),
    "presigned-url": re.compile(r"X-Amz-Signature="),
    "token-in-url": re.compile(
        r"(?i)https?://\S*[?&](access_)?(token|secret|key|password)=[^&\s]{8,}"
    ),
}


def _git_file_list() -> list[Path]:
    try:
        tracked = subprocess.check_output(
            ["git", "ls-files"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise unittest.SkipTest(f"git unavailable: {exc}") from exc
    paths: list[Path] = []
    for line in (tracked + untracked).splitlines():
        line = line.strip()
        if line:
            paths.append(ROOT / line.replace("/", "\\") if "\\" in str(ROOT) else ROOT / line)
    # Normalise to forward-slash relative paths for skip set
    unique: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        rel = p.relative_to(ROOT).as_posix()
        if rel not in seen:
            seen.add(rel)
            unique.append(ROOT / rel)
    return unique


def _scannable_files() -> list[Path]:
    out: list[Path] = []
    for path in _git_file_list():
        rel = path.relative_to(ROOT).as_posix()
        if rel in SKIP_PATHS:
            continue
        if not path.is_file():
            continue
        if path.stat().st_size > MAX_BYTES:
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        out.append(path)
    return out


def _find_matches(pattern: re.Pattern[str], files: list[Path]) -> list[str]:
    hits: list[str] = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            m = pattern.search(line)
            if m:
                snippet = m.group(0)[:4] + "..."
                hits.append(f"{rel}:{lineno} ({pattern.pattern[:20]}…): {snippet}")
    return hits


class NoSecretsInTrackedFilesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.files = _scannable_files()

    def test_scanned_at_least_one_file(self) -> None:
        self.assertGreater(len(self.files), 0, "no scannable files from git")

    def _assert_pattern_absent(self, name: str) -> None:
        hits = _find_matches(PATTERNS[name], self.files)
        if hits:
            self.fail(
                f"pattern {name}: " + "; ".join(
                    f"{h.split(' (')[0]} ({name})" for h in hits
                )
            )

    def test_aws_access_key_id(self) -> None:
        self._assert_pattern_absent("aws-access-key-id")

    def test_aws_secret_assignment(self) -> None:
        self._assert_pattern_absent("aws-secret-assignment")

    def test_private_key_block(self) -> None:
        self._assert_pattern_absent("private-key-block")

    def test_aws_account_in_arn(self) -> None:
        self._assert_pattern_absent("aws-account-in-arn")

    def test_deployed_api_url(self) -> None:
        self._assert_pattern_absent("deployed-api-url")

    def test_presigned_url(self) -> None:
        self._assert_pattern_absent("presigned-url")

    def test_token_in_url(self) -> None:
        self._assert_pattern_absent("token-in-url")


if __name__ == "__main__":
    unittest.main(verbosity=2)
