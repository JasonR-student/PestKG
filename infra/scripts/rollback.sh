#!/usr/bin/env bash
set -Eeuo pipefail

state_root="${PESTKG_STATE_ROOT:-./data/state}"
state_file="$state_root/active-release.json"
if [[ ! -f "$state_file" ]]; then
  echo "No active release state exists; rollback is unavailable" >&2
  exit 2
fi

previous_release="$(awk -F'"' '/"previous_release_id"/ {print $4; exit}' "$state_file")"
if [[ -z "$previous_release" ]]; then
  echo "No previous release is recorded; rollback is unavailable" >&2
  exit 2
fi

compose_files=(-f docker-compose.yml)
if [[ "${PESTKG_PRODUCTION:-0}" == "1" ]]; then
  compose_files+=(-f infra/docker-compose.prod.yml)
fi

dc() {
  docker compose "${compose_files[@]}" "$@"
}

export PESTKG_RELEASE_ID="$previous_release"
dc run --rm api pestkg-release rollback --allow-blocked

if [[ "${PESTKG_FULL_GRAPH:-0}" == "1" ]]; then
  dc --profile full up -d --wait api web caddy neo4j neo4j-init
else
  dc up -d --wait api web caddy
fi

infra/scripts/smoke-test.sh "${PESTKG_BASE_URL:-http://localhost}" "$previous_release"
echo "Rolled back to $previous_release"
