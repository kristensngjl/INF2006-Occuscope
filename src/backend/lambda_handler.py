"""AWS Lambda entry point for the Occuscope API (crowdmap-api).

Wraps Zul's FastAPI app (src/backend/api.py) with Mangum so it runs on
API Gateway (HTTP API) + Lambda without code changes to the API itself.

The read-only SQLite database is kept in the private data bucket
(s3://$DB_BUCKET/$DB_KEY). On a cold start it is copied to /tmp (Lambda's only
writable folder) and reused by later requests to the same instance.

Environment variables (set in Lambda -> Configuration -> Environment variables):
  DB_BUCKET  private S3 bucket holding the database, e.g. crowdmap-lake-g017
  DB_KEY     object key of the database, e.g. db/occuscope.db
"""

from __future__ import annotations

import os

import boto3
from mangum import Mangum

DB_LOCAL = "/tmp/occuscope.db"


def _ensure_db() -> None:
    """Download the database from S3 once per Lambda instance (cold start)."""
    if os.path.exists(DB_LOCAL):
        return
    partial = DB_LOCAL + ".part"
    boto3.client("s3").download_file(os.environ["DB_BUCKET"], os.environ["DB_KEY"], partial)
    os.replace(partial, DB_LOCAL)  # only expose a complete file


_ensure_db()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_LOCAL}"

from src.backend.api import create_app  # noqa: E402  (import after the DB exists)

app = create_app(DB_LOCAL)


@app.get("/health")
def health():
    """Liveness check for monitoring and the deployment test."""
    return {"status": "ok", "database": os.path.exists(DB_LOCAL)}


# The frontend calls /api/<endpoint>; strip the /api prefix before FastAPI routes it.
handler = Mangum(app, api_gateway_base_path="/api", lifespan="off")
