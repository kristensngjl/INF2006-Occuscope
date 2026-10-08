#!/usr/bin/env bash
# Create CloudWatch alarms + an SNS email topic + a dashboard for Occuscope (Kristen / Ryan).
# Run in AWS CloudShell with the lab started:
#     bash setup_alarms.sh you@example.com <api-id>
# Then CONFIRM the subscription email from AWS (check spam), or no alerts arrive.
# Free tier covers 10 alarms, 3 dashboards and SNS email at this volume.
set -euo pipefail
EMAIL=${1:?usage: bash setup_alarms.sh <email> <api-id>}
API_ID=${2:?usage: bash setup_alarms.sh <email> <api-id>}
REGION=us-east-1
TOPIC=$(aws sns create-topic --name crowdmap-alerts --query TopicArn --output text)
aws sns subscribe --topic-arn "$TOPIC" --protocol email --notification-endpoint "$EMAIL" >/dev/null
echo "SNS topic crowdmap-alerts created; confirm the email sent to $EMAIL"

lambda_alarm() {  # name function metric threshold description
  aws cloudwatch put-metric-alarm --alarm-name "$1" --alarm-description "$5" \
    --namespace AWS/Lambda --metric-name "$3" --dimensions Name=FunctionName,Value="$2" \
    --statistic Sum --period 300 --evaluation-periods 1 --threshold "$4" \
    --comparison-operator GreaterThanOrEqualToThreshold --treat-missing-data notBreaching \
    --alarm-actions "$TOPIC" --ok-actions "$TOPIC"
  echo "alarm $1"
}
api_alarm() {  # name metric statistic threshold description [extended-statistic]
  local stat=(--statistic "$3")
  [ "$3" = "p95" ] && stat=(--extended-statistic p95)
  aws cloudwatch put-metric-alarm --alarm-name "$1" --alarm-description "$5" \
    --namespace AWS/ApiGateway --metric-name "$2" \
    --dimensions Name=ApiId,Value="$API_ID" Name=Stage,Value='$default' \
    "${stat[@]}" --period 300 --evaluation-periods 1 --threshold "$4" \
    --comparison-operator GreaterThanOrEqualToThreshold --treat-missing-data notBreaching \
    --alarm-actions "$TOPIC" --ok-actions "$TOPIC"
  echo "alarm $1"
}

lambda_alarm crowdmap-api-errors      crowdmap-api      Errors    1 "Map/forecast/chat API raised an unhandled error"
lambda_alarm crowdmap-bookings-errors crowdmap-bookings Errors    1 "Login/booking writer raised an unhandled error"
lambda_alarm crowdmap-web-errors      crowdmap-web      Errors    1 "Frontend file server raised an unhandled error"
lambda_alarm crowdmap-bookings-throttled crowdmap-bookings Throttles 1 "Single-writer Lambda hit its concurrency limit"
api_alarm crowdmap-http-5xx     5xx     Sum  5    "API returned 5 or more server errors in 5 minutes"
api_alarm crowdmap-http-4xx     4xx     Sum  50   "Many client errors (incl. 429 throttling) in 5 minutes: possible abuse or load spike"
api_alarm crowdmap-http-latency Latency p95  3000 "95th percentile API latency at or above 3 s"

cat > /tmp/dash.json <<JSON
{"widgets":[
 {"type":"metric","x":0,"y":0,"width":12,"height":6,"properties":{"title":"API requests and errors","region":"$REGION","stat":"Sum","period":60,
  "metrics":[["AWS/ApiGateway","Count","ApiId","$API_ID","Stage","\$default"],[".","4xx",".",".",".","."],[".","5xx",".",".",".","."]]}},
 {"type":"metric","x":12,"y":0,"width":12,"height":6,"properties":{"title":"API latency (ms)","region":"$REGION","period":60,
  "metrics":[["AWS/ApiGateway","Latency","ApiId","$API_ID","Stage","\$default",{"stat":"p50"}],["...",{"stat":"p95"}]]}},
 {"type":"metric","x":0,"y":6,"width":12,"height":6,"properties":{"title":"Lambda invocations","region":"$REGION","stat":"Sum","period":60,
  "metrics":[["AWS/Lambda","Invocations","FunctionName","crowdmap-api"],["...","crowdmap-bookings"],["...","crowdmap-web"]]}},
 {"type":"metric","x":12,"y":6,"width":12,"height":6,"properties":{"title":"Lambda errors, throttles, concurrency","region":"$REGION","stat":"Sum","period":60,
  "metrics":[["AWS/Lambda","Errors","FunctionName","crowdmap-api"],["...","crowdmap-bookings"],["...","crowdmap-web"],[".","Throttles",".","crowdmap-bookings"],[".","ConcurrentExecutions",".","crowdmap-api",{"stat":"Maximum"}]]}},
 {"type":"alarm","x":0,"y":12,"width":24,"height":4,"properties":{"title":"Occuscope alarms","alarms":[
  "arn:aws:cloudwatch:$REGION:$(aws sts get-caller-identity --query Account --output text):alarm:crowdmap-api-errors"]}}
]}
JSON
# Replace the single alarm ARN with all seven
ACCT=$(aws sts get-caller-identity --query Account --output text)
ARNS=$(for a in crowdmap-api-errors crowdmap-bookings-errors crowdmap-web-errors crowdmap-bookings-throttled crowdmap-http-5xx crowdmap-http-4xx crowdmap-http-latency; do printf '"arn:aws:cloudwatch:%s:%s:alarm:%s",' "$REGION" "$ACCT" "$a"; done)
python3 - "$ARNS" <<'PY'
import json, sys
d = json.load(open("/tmp/dash.json"))
d["widgets"][-1]["properties"]["alarms"] = json.loads("[" + sys.argv[1].rstrip(",") + "]")
json.dump(d, open("/tmp/dash.json", "w"))
PY
aws cloudwatch put-dashboard --dashboard-name crowdmap --dashboard-body file:///tmp/dash.json >/dev/null
echo "dashboard crowdmap created (CloudWatch -> Dashboards -> crowdmap)"

echo; echo "Saved alarm list:"
aws cloudwatch describe-alarms --alarm-name-prefix crowdmap \
  --query 'MetricAlarms[].[AlarmName,MetricName,Threshold,StateValue]' --output table \
  | sed "s/$ACCT/<ACCOUNT>/g; s/$API_ID/<API_ID>/g" | tee alarms-config.txt
