# PestKG deployment and operations manual

This runbook deploys the anonymous read-only portal on one Linux host. The
reference capacity is 8 CPU cores, 32 GB RAM, and 500 GB SSD. Commands are run
from the repository root unless stated otherwise.

The application images contain code only. Immutable release data, the writable
release registry, and release-specific Neo4j volumes remain outside the images.

## 1. Host requirements

- Linux x86_64 with Docker Engine 27 or newer.
- Docker Compose 2.24 or newer. The production override uses `!reset` to remove
  local build definitions.
- At least 500 GB SSD for two full releases plus import headroom.
- Ports 80 and 443 open; ports 7474 and 7687 should remain firewalled from the
  public internet.
- DNS for `SITE_ADDRESS` pointing to the host before public TLS activation.

Create the runtime layout:

```bash
sudo install -d -m 0755 /srv/pestkg/releases /srv/pestkg/state
sudo chown -R "$USER":"$USER" /srv/pestkg/releases
sudo chown 100:101 /srv/pestkg/state
cp .env.example .env
chmod 0600 .env
```

Set at least `SITE_ADDRESS`, `PESTKG_RELEASE_ROOT`, `PESTKG_STATE_ROOT`, image
namespace/tag, CORS origin, and strong Neo4j credentials in `.env`.

For DuckDB/Parquet-only operation, leave `PESTKG_NEO4J_URI` and
`PESTKG_NEO4J_PASSWORD` empty. For the full graph profile, set:

```dotenv
PESTKG_NEO4J_URI=bolt://neo4j:7687
PESTKG_NEO4J_PASSWORD=replace-with-a-strong-password
NEO4J_AUTH=neo4j/replace-with-the-same-strong-password
```

## 2. Prepare an immutable release

The source RAR never enters Git or an application image. Prepare it on a
controlled workstation or staging host:

```bash
python tools/release-pipeline/prepare_release.py \
  --archive /srv/input/multicountry_pesticide_kg_research.rar \
  --output /srv/pestkg/releases
```

The pipeline extracts only the federated release, verifies the manifest,
materializes partitioned Parquet, exports supported graph formats, and rebuilds
the versioned download catalog.

The supplied `2026.08.3_federated` archive is currently blocked for public
distribution because multiple text files differ from the top-level manifest.
Do not use `ALLOW_BLOCKED=1` on a public host. That override is for private
integration testing only. See `docs/releases/RELEASE_AUDIT_2026-08-28.md`.

## 3. Build and publish images

Build code images with OCI version, commit, and build-date labels:

```bash
PESTKG_IMAGE_NAMESPACE=ghcr.io/OWNER/pestkg \
  infra/scripts/build-images.sh 1.1.0

docker push ghcr.io/OWNER/pestkg/api:1.1.0
docker push ghcr.io/OWNER/pestkg/web:1.1.0
```

The API image builds dependency wheels in a separate stage and installs them
offline into the runtime stage. The web image uses `npm ci` and the committed
lockfile. Neither image contains `data/`, `runtime/`, or the source archive.

For an air-gapped server, export all four required images:

```bash
PESTKG_IMAGE_NAMESPACE=ghcr.io/OWNER/pestkg \
  infra/scripts/export-images.sh 1.1.0 /srv/pestkg/images
```

On the target host:

```bash
cd /srv/pestkg/images
sha256sum -c pestkg-images-1.1.0.tar.gz.sha256
gzip -dc pestkg-images-1.1.0.tar.gz | docker load
```

Keep the generated manifest JSON and SHA-256 file with the delivery record.

## 4. Initial deployment

### DuckDB/Parquet mode

Production pulls prebuilt images and does not compile on the host:

```bash
infra/scripts/release.sh 2026.08.3_federated --prod
```

For local integration, omit `--prod`; the script builds the code images first.

### Full Neo4j mode

The full profile creates a Neo4j volume whose name contains
`PESTKG_RELEASE_ID`. It imports into that empty volume before activation:

```bash
infra/scripts/release.sh 2026.08.3_federated --prod --full
```

The old release volume is not reused or deleted. The API uses Neo4j only when
the graph volume release matches the active request release; otherwise it
falls back to the selected DuckDB/Parquet repository.

## 5. Release script gates

`infra/scripts/release.sh` performs these gates in order:

1. Pull production images or build local images.
2. Verify required metadata, JSON integrity, artifact sizes, and SHA-256 values.
3. Register the release and run a repository smoke test.
4. Optionally import a new release-specific Neo4j volume.
5. Atomically update `/srv/pestkg/state/active-release.json`.
6. Start services and wait for health checks.
7. Verify readiness, selected-release headers, overview, one-row filtering, and
   the versioned download index through HTTPS.
8. Restore the prior active release and volume automatically if post-activation
   checks fail. On a failed first deployment, public services stop fail-closed.

Set `PESTKG_BASE_URL=https://pestkg.example.org` so the final smoke test uses the
public reverse-proxy path rather than loopback HTTP.

## 6. Manual health and contract checks

```bash
curl --fail https://pestkg.example.org/health/live
curl --fail https://pestkg.example.org/health/ready
curl --fail https://pestkg.example.org/health
curl --fail \
  -H 'X-PestKG-Release: 2026.08.3_federated' \
  https://pestkg.example.org/api/v1/stats/overview
```

- `/health/live` proves the process is serving.
- `/health/ready` verifies the active release and, when configured, Neo4j.
- `/health` reports API version, schema version, data mode, release count, and
  graph connectivity.
- `/openapi.json` must match `packages/api-contract/openapi-v1.1.json` for the deployed code tag.

Use request IDs from `X-Request-ID` to correlate user reports with proxy and API
logs.

## 7. Upgrade to a new data release

1. Place the new immutable directory beside the old one under
   `/srv/pestkg/releases/<release_id>`.
2. Do not edit an existing release directory in place.
3. Keep at least the current and previous release plus both Neo4j volumes.
4. Run the same release command with the new ID.
5. After acceptance, update the default `PESTKG_RELEASE_ID` in `.env` for clean
   disaster recovery; runtime selection still comes from the atomic state file.

Example:

```bash
PESTKG_BASE_URL=https://pestkg.example.org \
  infra/scripts/release.sh 2026.10.1_federated --prod --full
```

Requests already in progress stay pinned to their resolved version. New
requests use the newly active state after activation.

## 8. Rollback

Automatic rollback runs on failed deployment smoke tests. For an operator
rollback:

```bash
PESTKG_PRODUCTION=1 \
PESTKG_FULL_GRAPH=1 \
PESTKG_BASE_URL=https://pestkg.example.org \
  infra/scripts/rollback.sh
```

The CLI reads `previous_release_id`, atomically activates it, starts the matching
release-specific Neo4j volume, and repeats HTTP smoke tests. A rollback never
rewrites either release directory.

## 9. Backup and retention

Back up these small mutable files after every successful activation:

```bash
tar -C /srv/pestkg -czf \
  "/srv/pestkg/state-backup-$(date -u +%Y%m%dT%H%M%SZ).tar.gz" state
```

Release directories and image bundles are immutable and should be replicated to
separate storage. Neo4j volumes are reproducible from the versioned import CSV;
retain the previous volume for fast rollback and rebuild older volumes on
demand. Never delete the previous release during the same maintenance window.

## 10. Operations and security

Useful commands:

```bash
docker compose ps
docker compose logs --since 30m api caddy web
docker compose --profile full logs --since 30m neo4j
docker compose exec api pestkg-release list
docker stats --no-stream
```

- Caddy terminates TLS and adds content, referrer, and permissions headers.
- API and web containers run with health checks; the production override uses a
  read-only root filesystem, tmpfs runtime paths, PID limits, and
  `no-new-privileges`.
- Release data is mounted read-only. Only `/data/state` is writable by the API
  administrative CLI.
- The public API is anonymous and read-only. Release mutation remains a local
  CLI operation and is never exposed over HTTP.
- Monitor 5xx rate, readiness, response latency, disk use, container restarts,
  and Caddy certificate renewal. Alert before SSD use reaches 80%.
- Redact Neo4j credentials and `.env` from support bundles and CI artifacts.

## 11. Performance acceptance

Run acceptance against warmed caches and the intended full release:

- Overview P95 at or below 1 second.
- Search and combined filters P95 at or below 2 seconds.
- Bounded graph requests P95 at or below 3 seconds.
- A 100,000-row CSV export completes within 60 seconds.

Record the release ID, image digests, host resources, concurrency, and query set
with every benchmark. Sample-mode timings are functional checks, not full-data
capacity evidence.

## 12. Stop and remove application containers

```bash
docker compose -f docker-compose.yml -f infra/docker-compose.prod.yml down
```

This leaves release data, Caddy state, and named Neo4j volumes intact. Do not add
`--volumes` during routine shutdown or rollback.
