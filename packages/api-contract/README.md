# PestKG API contract

`openapi-v1.1.json` is the versioned snapshot of the original (Python v1.1) contract served by the Java compatibility layer on port 18088.
contract. It is retained as the historical wire contract the restored MyPestKg-Beta frontend speaks; the Java backend reproduces these paths (CompatibilityController), and the web client generates its TypeScript declarations from the frontend's own openapi-ts config.

```powershell
.\.venv\Scripts\python packages\api-contract\export_openapi.py
npm --prefix apps/web run api:generate
```

Both generated files are committed and checked for drift in CI.
