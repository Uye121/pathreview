#!/usr/bin/env bash
# Fire concurrent requests at /auth/login to exercise the rate limiter.
# The endpoint uses OAuth2PasswordRequestForm, so creds are form-encoded.
# Requests don't need to succeed — we just count status codes (401 vs 429).
#
# Usage:
#   ./scripts/load_test_login.sh
#   URL=http://localhost:8000 COUNT=70 ./scripts/load_test_login.sh

set -u

URL="${URL:-http://localhost:8000}"
COUNT="${COUNT:-70}"
ENDPOINT="$URL/auth/login"
TMPDIR="$(mktemp -d)"

echo "Sending $COUNT concurrent requests to $ENDPOINT ..."

for i in $(seq 1 "$COUNT"); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST "$ENDPOINT" \
    -d "username=loadtest@example.com" \
    -d "password=wrong-password" \
    > "$TMPDIR/$i" &
done

wait

echo
echo "Status code summary:"
cat "$TMPDIR"/* | sort | uniq -c | sort -rn

rm -rf "$TMPDIR"
