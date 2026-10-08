#!/usr/bin/env bash
# Check that AWS runs the LATEST versions from the repo (Kristen).
# 1. On your laptop:  python src/infra/make_expected_versions.py   -> deploy/expected-versions.txt
# 2. Upload that file and this script to CloudShell (lab started), then:
#       bash check_versions.sh g017        (or g07 after renaming the buckets)
# Output: version-check.txt (account ID redacted). Read-only: changes nothing in AWS.
set -uo pipefail
SUFFIX=${1:?usage: bash check_versions.sh <bucket-suffix, e.g. g017>}
EXP=${2:-expected-versions.txt}
WEB=crowdmap-web-$SUFFIX; LAKE=crowdmap-lake-$SUFFIX
ACCT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo NONE)
want() { awk -v k="$1" '$1==k {print $2}' "$EXP"; }
ok=0; bad=0
check() {  # name expected actual
  if [ "$2" = "$3" ]; then echo "MATCH     $1"; ok=$((ok+1)); else echo "MISMATCH  $1  (expected ${2:-?}, AWS has ${3:-?})"; bad=$((bad+1)); fi
}
TMP=$(mktemp -d)
{
echo "# Version check, $(TZ=Asia/Singapore date '+%Y-%m-%d %H:%M SGT'), buckets *-$SUFFIX"
sed -n 1p "$EXP"

echo; echo "## Lambda code and runtime"
for f in crowdmap-api crowdmap-bookings; do
  read -r sha rt handler < <(aws lambda get-function-configuration --function-name $f \
      --query '[CodeSha256,Runtime,Handler]' --output text)
  check "$f code = latest zip" "$(want lambda_zip)" "$sha"
  check "$f runtime" "python3.11" "$rt"
  check "$f handler" "lambda_handler.handler" "$handler"
done
check "crowdmap-web runtime" "python3.11" "$(aws lambda get-function-configuration --function-name crowdmap-web --query Runtime --output text)"

echo; echo "## Frontend files in $WEB"
for name in index.html styles.css login.css app.js data.js model.js bookings.js; do
  if aws s3 cp "s3://$WEB/$name" "$TMP/$name" --quiet 2>/dev/null; then
    check "web/$name" "$(want web/$name)" "$(sha256sum "$TMP/$name" | cut -d' ' -f1)"
  else
    check "web/$name" "$(want web/$name)" "MISSING"
  fi
done

echo; echo "## Database s3://$LAKE/db/occuscope.db"
aws s3 cp "s3://$LAKE/db/occuscope.db" "$TMP/occuscope.db" --quiet
if [ "$(sha256sum "$TMP/occuscope.db" | cut -d' ' -f1)" = "$(want db)" ]; then
  echo "MATCH     db is exactly the uploaded build (no logins/bookings since)"; ok=$((ok+1))
else
  echo "INFO      db differs from the build: expected once anyone logs in or books (the writer saves it back)."
  echo "          Checking its contents instead:"
fi
python3 - "$TMP/occuscope.db" <<'PY'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
q = lambda s: c.execute(s).fetchone()[0]
for label, sql, want in [("locations", "select count(*) from location", 64),
                         ("occupancy readings", "select count(*) from occupancy", 99008),
                         ("events", "select count(*) from event", 207),
                         ("demo accounts", "select count(*) from student_profile", 1998)]:
    got = q(sql)
    print(f"{'MATCH    ' if got == want else 'MISMATCH '} db {label} = {got} (expected {want})")
booked = q("select count(*) from room_booking where status='confirmed'")
print(f"INFO      db confirmed bookings = {booked}")
PY
echo "INFO      db object versions kept in S3: $(aws s3api list-object-versions --bucket "$LAKE" --prefix db/occuscope.db --query 'length(Versions)' --output text)"

echo; echo "## Summary: $ok match, $bad mismatch (lines marked MISMATCH need a re-upload)"
} 2>&1 | sed "s/$ACCT/<ACCOUNT>/g" | tee version-check.txt
rm -rf "$TMP"
