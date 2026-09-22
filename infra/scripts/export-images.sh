#!/usr/bin/env bash
set -Eeuo pipefail

tag="${1:-1.1.0}"
output_dir="${2:-artifacts/deploy/images}"
namespace="${PESTKG_IMAGE_NAMESPACE:-pestkg}"
caddy_image="${CADDY_IMAGE:-caddy:2.11.4-alpine}"
neo4j_image="${NEO4J_IMAGE:-neo4j:2026.02.2}"
archive_name="pestkg-images-$tag.tar.gz"
archive="$output_dir/$archive_name"

mkdir -p "$output_dir"
docker pull "$caddy_image"
docker pull "$neo4j_image"
docker save \
  "$namespace/api:$tag" \
  "$namespace/web:$tag" \
  "$caddy_image" \
  "$neo4j_image" \
  | gzip -9 > "$archive"

(
  cd "$output_dir"
  sha256sum "$archive_name" > "$archive_name.sha256"
)
docker image inspect \
  "$namespace/api:$tag" \
  "$namespace/web:$tag" \
  "$caddy_image" \
  "$neo4j_image" \
  > "$output_dir/pestkg-images-$tag.manifest.json"

echo "Offline image bundle: $archive"
echo "Checksum: $archive.sha256"
