#!/usr/bin/env bash
# Rebuild the Lambda package and the SQLite database (run from the repo root).
# Output: deploy/crowdmap-api.zip (upload to BOTH crowdmap-api and crowdmap-bookings)
#         deploy/occuscope.db     (upload to s3://<data-bucket>/db/occuscope.db)
# Needs Python 3.11 (same as the Lambda runtime), pip and fastapi installed locally
# (init_app_db.py seeds demo accounts using src/backend/bookings.py).
set -euo pipefail
rm -rf build/lambda deploy/crowdmap-api.zip && mkdir -p build/lambda/src/backend deploy
python src/db/init_app_db.py
cp data/occuscope.db deploy/occuscope.db
# Backend modules the API imports at runtime (tests are not packaged).
cp src/backend/api.py src/backend/chat.py src/backend/bookings.py src/backend/booking_schema.sql build/lambda/src/backend/
cp src/backend/lambda_handler.py build/lambda/lambda_handler.py
# Linux (x86_64, CPython 3.11) wheels so compiled parts like pydantic-core work on Lambda.
python -m pip install --target build/lambda --platform manylinux2014_x86_64 \
  --implementation cp --python-version 3.11 --only-binary=:all: "fastapi>=0.115,<1" "mangum>=0.19,<1"
if command -v zip >/dev/null 2>&1; then
  (cd build/lambda && zip -qr9 ../../deploy/crowdmap-api.zip .)
else
  python -c "import shutil; shutil.make_archive('deploy/crowdmap-api', 'zip', 'build/lambda')"
fi
echo "Built deploy/crowdmap-api.zip and deploy/occuscope.db"
