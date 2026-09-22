# PestKG web application

The web application is a React/Vite research workspace organized into:

- `src/app`: routing, providers and application shell.
- `src/features`: page-level research workflows and feature components.
- `src/shared`: generated API types, request utilities, charts and shared UI.
- `src/styles`: design tokens, base rules, shell, feature and responsive CSS.

Generate API declarations before changing contract-derived models:

```powershell
npm run api:generate
```

Run the local checks with `npm run lint`, `npm run test`, and `npm run build`.
The production build enforces a 500 KiB limit for every JavaScript chunk.
