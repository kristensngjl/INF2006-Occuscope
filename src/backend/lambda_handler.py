"""AWS Lambda entry point for the Occuscope API.

Wraps the FastAPI app (src/backend/api.py) with Mangum so it runs on
API Gateway (HTTP API) + Lambda. The same package is deployed twice:

* crowdmap-api       (reader)  map, forecasts, events, chat. Scales out freely.
* crowdmap-bookings  (writer)  login and discussion-room bookings. Reserved
                               concurrency = 1, so there is exactly one writer.

The SQLite database lives in the private data bucket (s3://$DB_BUCKET/$DB_KEY).
On a cold start each instance copies it to /tmp (Lambda's only writable folder).

* Writer: after every successful POST it uploads the updated database back to
  S3, so bookings and sessions survive cold starts.
* Readers: at most every DB_REFRESH_SECONDS they compare the S3 ETag and
  re-download if the writer has published a newer copy, so the map's "booked"
  flag is at most about one minute behind (eventual consistency).

This is a single-writer design for a demo-scale service. Scaling bookings
horizontally would need a shared database (for example RDS); see the report.

Environment variables (Lambda -> Configuration -> Environment variables):
  DB_BUCKET           private S3 bucket holding the database, e.g. <data-bucket>
  DB_KEY              object key of the database, e.g. db/occuscope.db
  DB_WRITER           "1" on crowdmap-bookings only; unset or "0" elsewhere
  DB_REFRESH_SECONDS  reader refresh interval, default 60
  COOKIE_SECURE       "1" so session cookies are only sent over HTTPS
  GROQ_API_KEY        chatbot key (reader only); never commit it
"""

from __future__ import annotations

import os
import time

import boto3
from mangum import Mangum

DB_LOCAL = "/tmp/occuscope.db"
DB_BUCKET = os.environ["DB_BUCKET"]
DB_KEY = os.environ["DB_KEY"]
WRITER = os.getenv("DB_WRITER", "0") == "1"
REFRESH_SECONDS = int(os.getenv("DB_REFRESH_SECONDS", "60"))
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}

_s3 = boto3.client("s3")
_state = {"etag": None, "checked": 0.0}


def _download() -> None:
    """Copy the database from S3 to /tmp, replacing the old copy atomically."""
    partial = DB_LOCAL + ".part"
    obj = _s3.get_object(Bucket=DB_BUCKET, Key=DB_KEY)
    with open(partial, "wb") as f:
        for chunk in obj["Body"].iter_chunks(1 << 20):
            f.write(chunk)
    os.replace(partial, DB_LOCAL)
    _state["etag"] = obj.get("ETag")
    _state["checked"] = time.time()


def _refresh_if_changed() -> None:
    """Reader only: pick up a newer database published by the writer."""
    if time.time() - _state["checked"] < REFRESH_SECONDS:
        return
    _state["checked"] = time.time()
    try:
        etag = _s3.head_object(Bucket=DB_BUCKET, Key=DB_KEY).get("ETag")
    except Exception:  # keep serving the current copy if S3 is briefly unavailable
        return
    if etag != _state["etag"]:
        _download()


def _publish() -> None:
    """Writer only: save the updated database back to S3."""
    _s3.upload_file(DB_LOCAL, DB_BUCKET, DB_KEY)


_download()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_LOCAL}"

from src.backend.api import create_app  # noqa: E402  (import after the DB exists)

app = create_app(DB_LOCAL)


@app.get("/health")
def health():
    """Liveness check for monitoring and the deployment test."""
    return {"status": "ok", "database": os.path.exists(DB_LOCAL), "role": "writer" if WRITER else "reader"}


# The frontend calls /api/<endpoint>; strip the /api prefix before FastAPI routes it.
_mangum = Mangum(app, api_gateway_base_path="/api", lifespan="off")


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    if not WRITER:
        _refresh_if_changed()
    response = _mangum(event, context)
    if WRITER and method in MUTATING and response.get("statusCode", 500) < 400:
        _publish()
    return response
