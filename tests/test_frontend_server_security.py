"""Frontend dev server: allowlist, GET-only, loopback bind, proxy fail-closed (stdlib + Node)."""

from __future__ import annotations

import http.client
import os
import shutil
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "src" / "frontend" / "server.mjs"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FrontendServerSecurityTest(unittest.TestCase):
    port: int
    proc: subprocess.Popen[str] | None = None

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise unittest.SkipTest("node is not on PATH")
        if not SERVER.is_file():
            raise unittest.SkipTest(f"missing {SERVER}")
        cls.port = _free_port()
        env = os.environ.copy()
        env["PORT"] = str(cls.port)
        env["API_ORIGIN"] = "http://127.0.0.1:9"
        cls.proc = subprocess.Popen(
            ["node", str(SERVER)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.time() + 8
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=0.3):
                    break
            except OSError:
                if cls.proc.poll() is not None:
                    err = (cls.proc.stderr.read() if cls.proc.stderr else "") or ""
                    raise unittest.SkipTest(f"server exited early: {err[:500]}")
                time.sleep(0.15)
        else:
            cls.tearDownClass()
            raise unittest.SkipTest("server did not accept connections within 8s")

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.proc and cls.proc.poll() is None:
            cls.proc.terminate()
            try:
                cls.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                cls.proc.kill()
        cls.proc = None

    def _conn(self) -> http.client.HTTPConnection:
        return http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)

    def _get(self, path: str) -> http.client.HTTPResponse:
        conn = self._conn()
        conn.request("GET", path)
        resp = conn.getresponse()
        resp.read()
        conn.close()
        return resp

    def _method(self, method: str, path: str) -> int:
        conn = self._conn()
        conn.request(method, path)
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp.status

    def test_index_and_assets_served(self) -> None:
        for path in ("/", "/app.js", "/data.js", "/model.js", "/styles.css"):
            resp = self._get(path)
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.getheader("X-Content-Type-Options"), "nosniff")

    def test_non_allowlisted_paths_are_404(self) -> None:
        forbidden = (
            "/server.mjs",
            "/package.json",
            "/README.md",
            "/tests/api.test.mjs",
            "/src/backend/api.py",
            "/../.env",
            "/%2e%2e/.env",
            "/..%2f..%2f.env",
            "/.git/config",
            "/data/occuscope.db",
        )
        needles = ("DATABASE_URL", "AWS_", "SELECT")
        for path in forbidden:
            conn = self._conn()
            conn.request("GET", path)
            resp = conn.getresponse()
            body = resp.read().decode("utf-8", errors="replace")
            conn.close()
            self.assertIn(resp.status, (400, 404), msg=path)
            for needle in needles:
                self.assertNotIn(needle, body, msg=f"{path} leaked {needle}")

    def test_only_get_is_allowed(self) -> None:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            for path in ("/", "/api/occupancy/current"):
                status = self._method(method, path)
                self.assertEqual(status, 405, msg=f"{method} {path}")

    def test_api_proxy_fails_closed(self) -> None:
        conn = self._conn()
        conn.request("GET", "/api/occupancy/current")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        conn.close()
        self.assertEqual(resp.status, 503)
        ctype = resp.getheader("Content-Type") or ""
        self.assertIn("json", ctype.lower())
        self.assertNotIn("Error:", body)
        self.assertNotIn(" at ", body)
        self.assertNotIn("node:", body)
        self.assertNotIn("C:\\", body)
        self.assertNotIn("/home/", body)

    def test_response_headers_report(self) -> None:
        resp = self._get("/")
        for name in (
            "Content-Security-Policy",
            "X-Frame-Options",
            "Referrer-Policy",
            "Permissions-Policy",
        ):
            present = resp.getheader(name)
            print(f"header {name}: {'present' if present else 'absent'}")

    def test_server_binds_loopback_only(self) -> None:
        text = SERVER.read_text(encoding="utf-8")
        self.assertIn(".listen(", text)
        self.assertIn("'127.0.0.1'", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
