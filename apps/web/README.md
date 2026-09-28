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
The production build enforces a 550 KiB limit for every JavaScript chunk.

## Backend

This frontend is the original MyPestKg-Beta code and speaks the original /api/v1`r
contract. The Java backend on port 18088 serves those paths through a
compatibility layer plus the new Java contract paths; the vite dev proxy
(ite.config.ts) targets http://127.0.0.1:18088.
