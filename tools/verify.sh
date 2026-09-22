#!/usr/bin/env bash
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

contract_temp="$(mktemp -d)"
trap 'rm -rf "$contract_temp"' EXIT
cp packages/api-contract/openapi-v1.1.json "$contract_temp/openapi-v1.1.json"
cp apps/web/src/shared/api/generated/types.gen.ts "$contract_temp/types.gen.ts"
cp apps/web/src/shared/api/generated/index.ts "$contract_temp/index.ts"

python packages/api-contract/export_openapi.py
npm --prefix apps/web run api:generate
cmp "$contract_temp/openapi-v1.1.json" packages/api-contract/openapi-v1.1.json
cmp "$contract_temp/types.gen.ts" apps/web/src/shared/api/generated/types.gen.ts
cmp "$contract_temp/index.ts" apps/web/src/shared/api/generated/index.ts

python -m pytest apps/api/tests tools/release-pipeline/tests
python -m unittest discover -s research/figures/tests -v
python -m compileall apps/api/src tools/release-pipeline research/figures
npm --prefix apps/web run lint
npm --prefix apps/web run test
npm --prefix apps/web run build
docker compose config --quiet
docker compose -f docker-compose.yml -f infra/docker-compose.prod.yml config --quiet
