#!/usr/bin/env bash
# Rebuild the crowdmap-api Lambda package and the SQLite database (run from the repo root).
# Output: deploy/crowdmap-api.zip (upload to Lambda) and deploy/occuscope.db (upload to S3 db/).
# Needs Python 3.11 (same as the Lambda runtime) and pip.
set -euo pipefail
rm -rf build/lambda deploy/crowdmap-api.zip && mkdir -p build/lambda/src/backend deploy
python src/db/init_app_db.py
cp data/occuscope.db deploy/occuscope.db
cp src/backend/api.py build/lambda/src/backend/api.py
cp src/backend/lambda_handler.py build/lambda/lambda_handler.py
# Linux (x86_64, CPython 3.11) wheels so compiled parts like pydantic-core work on Lambda.
python -m pip install --target build/lambda --platform manylinux2014_x86_64 \
  --implementation cp --python-version 3.11 --only-binary=:all: "fastapi>=0.115,<1" "mangum>=0.19,<1"
(cd build/lambda && zip -qr9 ../../deploy/crowdmap-api.zip .)
echo "Built deploy/crowdmap-api.zip and deploy/occuscope.db"
