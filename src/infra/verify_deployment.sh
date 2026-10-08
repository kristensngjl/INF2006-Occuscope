#!/usr/bin/env bash
# Check the live AWS deployment against evidence/architecture.png (Kristen).
# Run in AWS CloudShell:   bash verify_deployment.sh <api-id>
# Output: aws-deployment-check.txt, with the account ID and API ID
# suffix redacted. Environment variable VALUES are never printed (keys only).
set -uo pipefail
API_ID=${1:?usage: bash verify_deployment.sh <api-id>}
REGION=us-east-1
ACCT=$(aws sts get-caller-identity --query Account --output text)
BASE="https://$API_ID.execute-api.$REGION.amazonaws.com"
SINCE=$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

redact() {
  sed -E -e "s/$ACCT/<ACCOUNT>/g" -e "s/$API_ID/<API_ID>/g"
}

{
echo "# Occuscope deployment check, $(TZ=Asia/Singapore date '+%Y-%m-%d %H:%M SGT'), region $REGION"

echo; echo "## 1. API Gateway crowdmap-http: routes -> integration"
aws apigatewayv2 get-routes --api-id "$API_ID" --query 'Items[].[RouteKey,Target]' --output table
aws apigatewayv2 get-integrations --api-id "$API_ID" --query 'Items[].[IntegrationId,IntegrationUri]' --output table

echo; echo "## 2. Stage \$default: auto-deploy and throttling"
aws apigatewayv2 get-stage --api-id "$API_ID" --stage-name '$default' \
  --query '{AutoDeploy:AutoDeploy,DefaultRouteSettings:DefaultRouteSettings,RouteSettings:RouteSettings}'

echo; echo "## 3. Lambda functions (env var KEYS only, values hidden)"
for f in crowdmap-api crowdmap-bookings crowdmap-web; do
  aws lambda get-function-configuration --function-name "$f" \
    --query '{Name:FunctionName,Runtime:Runtime,Handler:Handler,MemoryMB:MemorySize,TimeoutS:Timeout,Role:Role,EnvKeys:keys(Environment.Variables || `{}`)}'
  echo "reserved concurrency for $f: $(aws lambda get-function-concurrency --function-name "$f" --query ReservedConcurrentExecutions --output text)"
done

echo; echo "## 4. S3 buckets: private, versioning, contents"
for b in $(aws s3api list-buckets --query "Buckets[?starts_with(Name,'crowdmap-')].Name" --output text); do
  echo "### $b"
  aws s3api get-public-access-block --bucket "$b" --query PublicAccessBlockConfiguration
  echo "policy is public: $(aws s3api get-bucket-policy-status --bucket "$b" --query PolicyStatus.IsPublic --output text 2>/dev/null || echo 'no bucket policy')"
  echo "versioning: $(aws s3api get-bucket-versioning --bucket "$b" --query Status --output text)"
  aws s3 ls "s3://$b" --recursive --human-readable | awk '{print $3, $4, $5}'
done

echo; echo "## 5. CloudWatch: log groups and last-24h Lambda errors/throttles"
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/crowdmap \
  --query 'logGroups[].[logGroupName,storedBytes]' --output table
for f in crowdmap-api crowdmap-bookings crowdmap-web; do
  for m in Invocations Errors Throttles; do
    v=$(aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name $m \
        --dimensions Name=FunctionName,Value=$f --start-time "$SINCE" --end-time "$NOW" \
        --period 86400 --statistics Sum --query 'Datapoints[0].Sum' --output text)
    echo "$f $m (24h): $v"
  done
done

echo; echo "## 6. Things that must NOT exist (cost / design)"
echo "NAT gateways: $(aws ec2 describe-nat-gateways --filter Name=state,Values=available --query 'length(NatGateways)')"
echo "running EC2 instances: $(aws ec2 describe-instances --filters Name=instance-state-name,Values=running --query 'length(Reservations)')"
echo "RDS instances: $(aws rds describe-db-instances --query 'length(DBInstances)' 2>/dev/null || echo 'n/a')"
echo "CloudFront distributions: $(aws cloudfront list-distributions --query 'DistributionList.Quantity' 2>/dev/null || echo 'not permitted in Learner Lab')"
echo "Budgets: $(aws budgets describe-budgets --account-id "$ACCT" --query 'Budgets[].BudgetName' --output text 2>/dev/null || echo 'not permitted in Learner Lab')"

echo; echo "## 7. Live endpoints"
echo "GET /api/health -> $(curl -s "$BASE/api/health")"
echo "GET /api/locations -> $(curl -s "$BASE/api/locations" | grep -o '"location_id"' | wc -l) locations"
echo "GET / -> HTTP $(curl -s -o /dev/null -w '%{http_code}' "$BASE/")"
for f in styles.css login.css app.js data.js model.js bookings.js; do
  echo "GET /$f -> HTTP $(curl -s -o /dev/null -w '%{http_code}' "$BASE/$f")"
done
echo "GET /api/auth/me (signed out) -> HTTP $(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/auth/me") (expect 401)"
} 2>&1 | redact | tee aws-deployment-check.txt

echo; echo "Saved aws-deployment-check.txt (redacted)."
