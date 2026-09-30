# Scope

Static review of the Occuscope frontend dev server (`src/frontend/server.mjs`), browser modules (`app.js`, `model.js`, `data.js`, `index.html`, `styles.css`), read-only API (`src/backend/api.py`), Lambda wrapper (`src/backend/lambda_handler.py`), Lambda build script (`src/infra/build_lambda_package.sh`), and app DB init (`src/db/init_app_db.py`). Deployment hosting and AWS configuration were not exercised.

# Method

Line-by-line read of the listed files on 30 September 2026. Cross-checked `esc()` / `safe()` helpers against every `innerHTML` assignment cited in the runbook. No browser penetration testing, no deployed API Gateway review.

# Findings

| ID | Location (path:line) | What | Severity | Impact in this deployment | Recommended fix | Owner |
|---|---|---|---|---|---|---|
| SR-1 | `src/backend/api.py:38` | `FastAPI(title=...)` leaves default `/docs`, `/redoc`, `/openapi.json` enabled. | Low | Public read-only API; routes are already discoverable from `src/api-contract.md`, but OpenAPI lists every path on any host that serves the app unchanged. | Disable docs on production (`docs_url=None`, `redoc_url=None`, `openapi_url=None`) or protect behind auth. | Zul |
| SR-2 | `src/backend/api.py:47` | 503 body: `initialise it with python src/db/init_app_db.py`. | Low | Confirms stack and repo layout to a client when SQLite is missing; no secrets. | Generic message in production (`Application database unavailable`). | Zul |
| SR-3 | `src/frontend/server.mjs:24` | Successful static responses set only `Content-Type`, `Cache-Control`, `X-Content-Type-Options: nosniff`. | Low | Local dev server on loopback; no CSP / frame / referrer / permissions headers. | Add security headers on production CDN or API Gateway; optional for dev. | Kristen |
| SR-4 | `src/frontend/app.js:37` | Floor chips: `` `${f==='all'?'All floors':'Level '+f}` `` inside `innerHTML` without `esc(f)`. | Low | `f` is `all` or an integer floor from `locations.floor` (SQLite INTEGER / seed CSV); not a free-text field in the schema. | Use `esc(f)` or build with `textContent` for consistency. | Zi Qian |
| SR-5 | `src/frontend/model.js:221` | Floor selector: `` `'Level '+f` `` in `innerHTML` without `safe(f)`. | Low | Same as SR-4: numeric floor or `all`. | Same as SR-4. | Zi Qian |
| SR-6 | `src/backend/lambda_handler.py:11` | Docstring example: `crowdmap-lake-g017`. | Low | Example bucket name in source; not a secret, but names a deployment pattern. | Replace with `<data-bucket>` placeholder (Kristen threat-map row). | Kristen |
| SR-7 | `src/infra/build_lambda_package.sh:13` | `pip install` uses lower-bound ranges (`fastapi>=0.115,<1`, `mangum>=0.19,<1`). | Low | Reproducibility / supply-chain: different builds may resolve different minors. | Pin exact versions or add a lockfile for Lambda builds. | Kristen |
| SR-8 | `src/backend/lambda_handler.py:25-34` | Runtime trusts S3 object at `DB_BUCKET`/`DB_KEY` as the app DB. | Medium | If the object were swapped (IAM misconfiguration), attacker-controlled strings in `location.name`, `event.title`, etc. would reach the UI; most `innerHTML` paths use `esc()`/`safe()`, but defense-in-depth depends on S3 integrity. | Kristen to evidence least-privilege S3 write denial; object versioning or checksum check optional. | Kristen |
| SR-9 | `src/frontend/styles.css:1` | `@import url('https://fonts.googleapis.com/css2?family=DM+Sans...&family=Manrope...')` loads fonts from Google on every page view. | Low | Each visitor's IP address, User-Agent and Referer go to a third party. A future Content-Security-Policy (SR-3) would have to allow `fonts.googleapis.com` and `fonts.gstatic.com`. The page still works without it (`src/frontend/README.md` says fonts have system fallbacks). | Self-host the two font files, or drop the `@import` and use a system font stack. | Zi Qian |

# Checked, not a finding

- **`esc()` / `safe()`** (`app.js:4`, `model.js:11`): escape `& < > " '` (all five). Room/event/building strings in cited `innerHTML` paths use `esc()` or `safe()`; chart `style="height:..."` uses `Number(h.occupancy_count)` / `Number(r.capacity)`.
- **SVG string build** (`model.js:215`): API-derived room labels use `safe(r.name)`, `safe(r.location_id)`, `safe(r.floor)` in attributes and text.
- **`server.mjs`**: GET-only (line 10); asset allowlist (lines 6, 19–22); loopback bind (line 27); `/api/` proxy forwards path after slice(4) to fixed `API_ORIGIN` (lines 12–17); 503 JSON body is static (line 26), no stack trace.
- **`index.html`**: No third-party script; only local `styles.css` and the `app.js` module, plus one user-initiated link to SIT's Campus Wayfinder (`target="_blank" rel="noopener"`, line 4). It does not load fonts itself, but `styles.css:1` does: see SR-9. (An earlier version of this review checked only `index.html` and wrongly reported no third-party fonts; corrected 30 September 2026 after re-checking `styles.css`.)
- **`api.py` SQL**: User input via `?` placeholders; dynamic `WHERE` uses fixed column names from a tuple (lines 65–68), not user strings.
- **No CORS middleware** (`api.py`): Same-origin via frontend proxy; matches local design.
- **`/health`** (`lambda_handler.py:42-45`): Returns only `status` and `database` boolean.
- **`_ensure_db()` partial download**: `.part` then `os.replace` (lines 29–31).
- **`DB_BUCKET` / `DB_KEY` missing**: `KeyError` at import (line 30) — deployment misconfiguration / availability, not an auth bypass.
- **Leads `app.js:67` `title`/`style`**: `title` uses `esc(h.occupancy_count)`; `style` height is numeric only.

# Limitations

No dynamic browser UI testing in this review; no penetration test; deployed API Gateway, IAM, S3 policies, and production headers not reviewed. Findings are from static reads and the automated frontend-server test only.

# Date

30 September 2026, static review by Ryan (AI-assisted, verified against the cited lines).
