#!/usr/bin/env bash
set -euo pipefail

: "${MODAL_API_URL:?Set MODAL_API_URL to the deployed API URL}"
: "${PIPELINE_API_TOKEN:?Set PIPELINE_API_TOKEN to the pipeline bearer token}"

curl --fail --silent --show-error "${MODAL_API_URL%/}/health" >/dev/null

response_file="$(mktemp)"
trap 'rm -f "$response_file"' EXIT

http_status="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' \
  --header "Authorization: Bearer ${PIPELINE_API_TOKEN}" \
  --header 'Content-Type: application/json' \
  --data "{\"input_data\":{\"gameweek\":${GAMEWEEK:-1},\"per_expert_limit\":1,\"expert_count\":1}}" \
  "${MODAL_API_URL%/}/api/pipeline-runs")"

if [[ "$http_status" != "202" ]]; then
  printf 'Expected pipeline POST status 202, received %s\n' "$http_status" >&2
  sed -n '1,20p' "$response_file" >&2
  exit 1
fi

run_id="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["run_id"])' "$response_file")"
printf 'Accepted pipeline run: %s\n' "$run_id"

deadline="$((SECONDS + ${SMOKE_TIMEOUT_SECONDS:-3600}))"
while (( SECONDS < deadline )); do
  curl --fail --silent --show-error \
    "${MODAL_API_URL%/}/api/pipeline-runs/${run_id}" >"$response_file"
  run_status="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$response_file")"
  printf 'Pipeline status: %s\n' "$run_status"
  if [[ "$run_status" == "completed" ]]; then
    printf 'Modal smoke test passed.\n'
    exit 0
  fi
  if [[ "$run_status" == "failed" ]]; then
    python -c 'import json,sys; print(json.load(open(sys.argv[1])).get("error") or "Pipeline failed")' "$response_file" >&2
    exit 1
  fi
  sleep 5
done

printf 'Timed out waiting for pipeline %s; it may still be running.\n' "$run_id" >&2
exit 1
