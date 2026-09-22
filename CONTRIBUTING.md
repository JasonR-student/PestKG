# Contributing

## Change boundaries

- Keep `/api/v1` backward compatible. Additive response fields are allowed;
  renames, removals and semantic changes require a new API version.
- Treat `packages/api-contract/openapi-v1.1.json` and the generated web types as
  committed artifacts. Regenerate both whenever response models change.
- Do not commit files under `artifacts/` or `runtime/`.
- Keep release data immutable. New releases use a new directory under
  `data/releases/`; existing release contents are not edited in place.

## Verification

Windows:

```powershell
.\tools\verify.ps1
```

Linux or macOS:

```bash
./tools/verify.sh
```

The verification entrypoint checks API and pipeline tests, generated contract
drift, frontend lint/tests/build, bundle limits and Compose configuration.
