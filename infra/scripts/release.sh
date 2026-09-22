#!/usr/bin/env bash
set -Eeuo pipefail

release_id="${1:?usage: release.sh RELEASE_ID [--prod] [--full]}"
shift

prod=0
full=0
for argument in "$@"; do
  case "$argument" in
    --prod) prod=1 ;;
    --full) full=1 ;;
    *) echo "Unknown option: $argument" >&2; exit 2 ;;
  esac
done

compose_files=(-f docker-compose.yml)
if (( prod )); then
  compose_files+=(-f infra/docker-compose.prod.yml)
fi

dc() {
  docker compose "${compose_files[@]}" "$@"
}

state_root="${PESTKG_STATE_ROOT:-./data/state}"
mkdir -p "$state_root"
previous_release=""
if [[ -f "$state_root/active-release.json" ]]; then
  previous_release="$(awk -F'"' '/"release_id"/ {print $4; exit}' "$state_root/active-release.json")"
fi

allow_blocked=()
if [[ "${ALLOW_BLOCKED:-0}" == "1" ]]; then
  allow_blocked=(--allow-blocked)
fi

export PESTKG_RELEASE_ID="$release_id"
export BUILD_DATE="${BUILD_DATE:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
export VCS_REF="${VCS_REF:-$(git rev-parse --short=12 HEAD 2>/dev/null || printf unknown)}"

if (( prod )); then
  dc pull api web caddy
else
  dc build api web
fi

dc run --rm api pestkg-release validate "$release_id"
dc run --rm api pestkg-release register "$release_id"
dc run --rm api pestkg-release smoke-test "$release_id"

if (( full )); then
  dc --profile full run --rm --entrypoint sh neo4j /opt/pestkg/import.sh
fi

activated=0
rollback_on_error() {
  local exit_code=$?
  if (( activated )) && [[ -n "$previous_release" ]]; then
    echo "Deployment failed; restoring release $previous_release" >&2
    export PESTKG_RELEASE_ID="$previous_release"
    dc run --rm api pestkg-release activate "$previous_release" --allow-blocked || true
    if (( full )); then
      dc --profile full up -d --wait api web caddy neo4j neo4j-init || true
    else
      dc up -d --wait api web caddy || true
    fi
  elif (( activated )); then
    echo "Initial deployment failed after activation; stopping the public services" >&2
    rm -f "$state_root/active-release.json"
    dc stop caddy api web || true
  fi
  exit "$exit_code"
}
trap rollback_on_error ERR

dc run --rm api pestkg-release activate "$release_id" "${allow_blocked[@]}"
activated=1

if (( full )); then
  dc --profile full up -d --wait api web caddy neo4j neo4j-init
else
  dc up -d --wait api web caddy
fi

infra/scripts/smoke-test.sh "${PESTKG_BASE_URL:-http://localhost}" "$release_id"
trap - ERR
echo "Release $release_id is active"
