#!/usr/bin/env bash
set -Eeuo pipefail

tag="${1:-1.1.0}"
export PESTKG_IMAGE_NAMESPACE="${PESTKG_IMAGE_NAMESPACE:-pestkg}"
export PESTKG_IMAGE_TAG="$tag"
export BUILD_DATE="${BUILD_DATE:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
export VCS_REF="${VCS_REF:-$(git rev-parse --short=12 HEAD 2>/dev/null || printf unknown)}"

docker compose build --pull api web

for image in \
  "$PESTKG_IMAGE_NAMESPACE/api:$tag" \
  "$PESTKG_IMAGE_NAMESPACE/web:$tag"; do
  docker image inspect --format \
    '{{.RepoTags}} {{index .Config.Labels "org.opencontainers.image.version"}} {{index .Config.Labels "org.opencontainers.image.revision"}}' \
    "$image"
done
