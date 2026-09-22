#!/usr/bin/env bash
set -Eeuo pipefail

base_url="${1:-http://localhost}"
release_id="${2:?usage: smoke-test.sh BASE_URL RELEASE_ID}"
base_url="${base_url%/}"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

request() {
  local name="$1"
  shift
  curl --fail --silent --show-error --max-time 60 \
    --output "$work_dir/$name.body" \
    --dump-header "$work_dir/$name.headers" \
    "$@"
}

assert_release_body() {
  local name="$1"
  if ! grep -Eq "\"release_id\"[[:space:]]*:[[:space:]]*\"${release_id}\"" "$work_dir/$name.body"; then
    echo "Smoke test failed: $name did not report release $release_id" >&2
    return 1
  fi
}

request ready "$base_url/health/ready"
assert_release_body ready

request overview \
  --header "X-PestKG-Release: $release_id" \
  "$base_url/api/v1/stats/overview"
assert_release_body overview
if ! tr -d '\r' < "$work_dir/overview.headers" | grep -Fqi "X-PestKG-Release: $release_id"; then
  echo "Smoke test failed: release response header is missing" >&2
  exit 1
fi

request releases "$base_url/api/v1/releases/active"
assert_release_body releases

request query \
  --request POST \
  --header "Content-Type: application/json" \
  --header "X-PestKG-Release: $release_id" \
  --data '{"filters":{},"page_size":1}' \
  "$base_url/api/v1/registration-uses/query"
assert_release_body query

request downloads "$base_url/downloads/$release_id/index.json"
assert_release_body downloads

echo "Smoke tests passed for $release_id at $base_url"
