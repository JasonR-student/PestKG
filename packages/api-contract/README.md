# PestKG API contract

`openapi-v1.1.json` is the versioned source of truth for the public `/api/v1`
contract. The FastAPI application produces the snapshot, and the web client
generates TypeScript declarations from it.

```powershell
.\.venv\Scripts\python packages\api-contract\export_openapi.py
npm --prefix apps/web run api:generate
```

Both generated files are committed and checked for drift in CI.
