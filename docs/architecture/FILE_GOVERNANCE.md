# File governance

## Tracked source

- `apps/` contains deployable services.
- `packages/` contains shared versioned contracts.
- `tools/` contains deterministic maintenance and release tooling.
- `research/` contains reproducible research source, not generated outputs.
- `infra/` contains runtime and deployment configuration.
- `docs/` contains maintained engineering and release documentation.
- `data/releases/` contains approved metadata and bounded samples only.

## Local generated state

- `artifacts/` stores build deliveries, research outputs, offline images,
  screenshots and migration manifests.
- `runtime/` stores mutable service state and caches.
- Both directories are ignored by Git and must not be used as source inputs
  unless a command explicitly documents that dependency.

## Naming and retention

- Version immutable releases and public contracts explicitly.
- Use ISO dates (`YYYY-MM-DD`) for audit evidence and dated handoffs.
- Do not keep duplicate delivery trees beside their generators.
- Preserve a SHA-256 manifest before moving or replacing large artifacts.
