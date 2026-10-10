# Scope

Static review of the Occuscope frontend (`src/frontend/server.mjs`, `app.js`, `model.js`, `data.js`, `bookings.js`, `index.html`, `styles.css`), API (`src/backend/api.py`, `bookings.py`, `chat.py`), Lambda wrapper (`src/backend/lambda_handler.py`), Lambda build script (`src/infra/build_lambda_package.sh`), and app DB init (`src/db/init_app_db.py`). Deployment hosting and AWS configuration were not exercised in this file.

# Method

Line-by-line read 30 September 2026; re-cited 10 October 2026 after login/booking/chat landed. Cross-checked `esc()` / `safe()` against `innerHTML` paths. No penetration test; no deployed API Gateway packet capture.

# Findings

| ID | Location (path:line) | What | Severity | Impact in this deployment | Recommended fix | Owner | Status |
|---|---|---|---|---|---|---|---|
| SR-1 | `src/backend/api.py:40` | `FastAPI(title=...)` leaves default `/docs`, `/redoc`, `/openapi.json` enabled. | Low | Routes are already in `src/api-contract.md`, but OpenAPI lists login and booking paths on any host that serves the app unchanged. | Disable docs in production (`docs_url=None`, `redoc_url=None`, `openapi_url=None`) or protect behind auth. | Zul | open |
| SR-2 | `src/backend/api.py:49` | 503 body: `initialise it with python src/db/init_app_db.py`. | Low | Confirms stack and repo layout when SQLite is missing; no secrets. | Generic message (`Application database unavailable`). | Zul | open |
| SR-3 | `src/frontend/server.mjs:39` | Successful static responses set only `Content-Type`, `Cache-Control`, `X-Content-Type-Options: nosniff`. | Low | Local dev server on loopback. Kristen records that `crowdmap-web` adds production headers; no header dump in git yet. | Keep headers on `crowdmap-web`; optional on dev. | Kristen | open (prod claim unverified) |
| SR-4 | `src/frontend/app.js:82` | Floor chips: `` `${f==='all'?'All floors':'Level '+f}` `` inside `innerHTML` without `esc(f)`. | Low | `f` is `all` or an integer floor from `locations.floor`; not free text. | Use `esc(f)` or `textContent`. | Zi Qian | open |
| SR-5 | `src/frontend/model.js:282` | Floor selector: `` `'Level '+f` `` in `innerHTML` without `safe(f)`. | Low | Same as SR-4. | Same as SR-4. | Zi Qian | open |
| SR-6 | `src/backend/lambda_handler.py:23` | Docstring example bucket. | Low | Was `crowdmap-lake-g017`; now `<data-bucket>`. | — | Kristen | **closed** 10 Oct 2026 |
| SR-7 | `src/infra/build_lambda_package.sh:16` | `pip install` uses lower-bound ranges (`fastapi>=0.115,<1`, `mangum>=0.19,<1`). | Low | Different builds may resolve different minors. | Pin exact versions or add a lockfile for Lambda builds. | Kristen | open |
| SR-8 | `src/backend/lambda_handler.py:50-77` | Runtime trusts S3 object at `DB_BUCKET`/`DB_KEY` as the app DB. Writer uploads after successful POST. | Medium | If the object were swapped, attacker-controlled strings in `location.name` / `event.title` would reach the UI; most `innerHTML` paths use `esc()`/`safe()`, but integrity depends on S3 + LabRole. | Evidence least-privilege S3 write; versioning is on. | Kristen | open |
| SR-9 | `src/frontend/styles.css:1` | Google Fonts `@import` on every page view. | Low | Visitor IP/UA/Referer go to Google; a future CSP would have to allow those hosts. | Self-host or system font stack. | Zi Qian | open |

Open count: **8** (**7** Low, **1** Medium). Closed: SR-6.

# Checked, not a finding

- **`esc()` / `safe()`** (`app.js:5`, `model.js:11`): escape `& < > " '` (all five). Room/event/building strings in cited `innerHTML` paths use them; chart height uses `Number(...)`.
- **`server.mjs`**: loopback bind (line 42); asset allowlist; `/api/` proxy to fixed `API_ORIGIN`; POST only on chat/auth/bookings (line 10); mutations need `X-Occuscope-Request` except chat (lines 12–16); 503 JSON is static (line 41).
- **`bookings.py`**: PBKDF2-SHA256; hashed session cookie HttpOnly SameSite=Strict; write guard; 10/min login throttle; parameterised SQL.
- **`chat.py`**: user text in the user role; system prompt says treat questions as untrusted; location_ids allowlisted to snapshot IDs; no booking.
- **`api.py` occupancy SQL**: `?` placeholders; occupancy connection `?mode=ro`.
- **`/health`** (`lambda_handler.py`): `status`, `database` boolean, `role` reader/writer.
- **`DB_BUCKET` / `DB_KEY` missing**: `KeyError` at import — misconfiguration, not an auth bypass.

# Limitations

No dynamic browser UI testing in this file; no penetration test; deployed API Gateway, IAM JSON, and production response headers not captured. Findings are from static reads plus `tests/test_api_security.py` and `tests/test_frontend_server_security.py`.

# Date

30 September 2026 (initial), re-cited 10 October 2026 by Ryan (AI-assisted, verified against the cited lines).
