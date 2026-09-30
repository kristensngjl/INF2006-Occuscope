# Monitoring evidence

Ryan: CloudWatch dashboard / log query goes here after Kristen deploys. Redact account IDs, IPs, and secrets before paste.

# Wishlist (implement on AWS; not running today)

Kristen should expose at least:

- API 4xx and 5xx counts (by route if possible)
- API latency (p50 / p99)
- RDS connection count / failed connections
- Failed auth count (only if mutating routes exist; skip if API is public read-only)
- Deploy / instance health (ALB target or Lambda errors)

Logs should not contain `.env` values, access keys, or full connection strings.

# Date

TODO (blocked on deploy)

# Interpretation

TODO after the first redacted export: whether error rate and latency are acceptable for the demo, and what we would page on.

# Export commands for Kristen (redact before committing)

Run in AWS CloudShell or a configured CLI. Save each output as a .txt file under evidence/ and remove the account ID (12 digits), role ARNs' account part, API ID and hostname before committing. Replace with <ACCOUNT>, <API_ID>, <REGION>.

1. Lambda runtime and limits:
   aws lambda get-function-configuration --function-name crowdmap-api --query "{Runtime:Runtime,MemorySize:MemorySize,Timeout:Timeout,Handler:Handler,Role:Role,Env:Environment.Variables}"
   (redact Role account ID and env values)

2. IAM role policies (least privilege):
   aws iam list-attached-role-policies --role-name <LAMBDA_ROLE_NAME>
   aws iam list-role-policies --role-name <LAMBDA_ROLE_NAME>
   aws iam get-role-policy --role-name <LAMBDA_ROLE_NAME> --policy-name <INLINE_POLICY_NAME>
   Expect: S3 read on the one DB object, CloudWatch Logs write, nothing else.

3. S3 bucket is private:
   aws s3api get-public-access-block --bucket <DATA_BUCKET>
   Expect all four block settings true.

4. Lambda errors and duration (last 24h):
   aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Errors --dimensions Name=FunctionName,Value=crowdmap-api --start-time <ISO> --end-time <ISO> --period 3600 --statistics Sum
   (repeat with --metric-name Duration --statistics Average Maximum)

5. API Gateway 4xx/5xx (HTTP API):
   aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway --metric-name 4xx --dimensions Name=ApiId,Value=<API_ID> --start-time <ISO> --end-time <ISO> --period 3600 --statistics Sum
   (repeat with --metric-name 5xx and Count)
   If the API uses a stage with detailed metrics disabled, note that instead of guessing.

6. Liveness check:
   curl -s https://<API_HOST>/api/health
   Save only the JSON body ({"status":"ok",...}); never the hostname.

Also needed: evidence/architecture.png (labels match: frontend-map, backend-api, relational-db/S3 database file, occupancy-model, cloudwatch), and the Python runtime shown in step 1.
