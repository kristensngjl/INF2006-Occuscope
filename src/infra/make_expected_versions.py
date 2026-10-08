#!/usr/bin/env python3
"""Write deploy/expected-versions.txt: fingerprints of what SHOULD be deployed.

Run from the repo root after building (bash src/infra/build_lambda_package.sh):
    python src/infra/make_expected_versions.py
Then upload deploy/expected-versions.txt to CloudShell and run check_versions.sh.
"""
import base64, hashlib, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = ["index.html", "styles.css", "login.css", "app.js", "data.js", "model.js", "bookings.js"]

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h

zip_path = ROOT / "deploy" / "crowdmap-api.zip"
lines = [f"# generated {datetime.datetime.now():%Y-%m-%d %H:%M} from the local repo",
         # Lambda reports CodeSha256 as base64 of the zip's SHA-256
         f"lambda_zip {base64.b64encode(sha256(zip_path).digest()).decode()}",
         f"db {sha256(ROOT / 'deploy' / 'occuscope.db').hexdigest()}"]
lines += [f"web/{name} {sha256(ROOT / 'src' / 'frontend' / name).hexdigest()}" for name in FRONTEND]
(ROOT / "deploy" / "expected-versions.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
