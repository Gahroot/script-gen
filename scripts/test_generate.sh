#!/usr/bin/env bash
# Smoke-test the async /generate flow end-to-end.
#
# Usage:
#   ./scripts/test_generate.sh                              # hits local server
#   BASE_URL=https://your-app.up.railway.app ./scripts/test_generate.sh
#
# POSTs intake → receives job_id → polls /jobs/{job_id} until terminal state.
# Writes the markdown to test_output.md.

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8100}"
PAYLOAD="${PAYLOAD:-sample_intake.json}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"
POLL_TIMEOUT="${POLL_TIMEOUT:-900}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT"

if [[ ! -f "$PAYLOAD" ]]; then
  echo "Payload file not found: $PAYLOAD" >&2
  exit 1
fi

echo "→ Health check: $BASE_URL/health"
curl -sf "$BASE_URL/health" || { echo "Health check failed"; exit 1; }
echo

echo "→ POST $BASE_URL/generate"
http_code=$(curl -sS -o test_generate_response.json -w "%{http_code}" \
  -X POST "$BASE_URL/generate" \
  -H "Content-Type: application/json" \
  --data-binary "@$PAYLOAD")

if [[ "$http_code" != "202" ]]; then
  echo "Expected 202, got HTTP $http_code"
  cat test_generate_response.json
  exit 1
fi

JOB_ID=$(python3 -c "import json; print(json.load(open('test_generate_response.json'))['job_id'])")
STATUS_URL="$BASE_URL/jobs/$JOB_ID"
echo "  job_id: $JOB_ID"
echo "  polling: $STATUS_URL"
echo

start=$(date +%s)
while true; do
  curl -sf "$STATUS_URL" > test_output.json
  status=$(python3 -c "import json; print(json.load(open('test_output.json'))['status'])")
  elapsed=$(( $(date +%s) - start ))
  printf '  [%4ds] status=%s\n' "$elapsed" "$status"

  if [[ "$status" == "completed" || "$status" == "failed" ]]; then
    break
  fi
  if (( elapsed >= POLL_TIMEOUT )); then
    echo "Timed out waiting for job (>${POLL_TIMEOUT}s)"
    exit 1
  fi
  sleep "$POLL_INTERVAL"
done

python3 -c "
import json, re, sys
data = json.load(open('test_output.json'))
status = data['status']
if status == 'failed':
    print(f'  JOB FAILED: {data.get(\"error\")}', file=sys.stderr)
    sys.exit(2)

md = data.get('markdown') or ''
open('test_output.md', 'w').write(md)
hooks = len(re.findall(r'^\*\*HOOK \d+:\*\*', md, re.M))
meats = len(re.findall(r'^## MEAT \d+', md, re.M))
ctas  = len(re.findall(r'^\*\*CTA \d+:\*\*', md, re.M))
print()
print(f'  business:      {data[\"business_name\"]}')
print(f'  duration:      {data[\"duration_seconds\"]:.1f}s')
print(f'  email_sent:    {data[\"email_sent\"]}')
print(f'  markdown size: {len(md):,} chars')
print(f'  hooks:         {hooks} (expected 50)')
print(f'  meats:         {meats} (expected 3)')
print(f'  ctas:          {ctas} (expected 2)')
print(f'  combinations:  {hooks * meats * ctas} (expected 300)')
if (hooks, meats, ctas) != (50, 3, 2):
    print('  WARNING: counts do not match expected 50/3/2', file=sys.stderr)
    sys.exit(2)
"

echo
echo "✓ Wrote test_output.json and test_output.md"
