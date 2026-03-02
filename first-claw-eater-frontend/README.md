# First Claw Eater Frontend

Next.js dashboard for the First Claw Eater MVP.

## Local dev

Backend should be running at `http://localhost:8000` (default). The frontend proxies API calls via
`/api/fce/*` so you don't need CORS locally.

```bash
cd apps/web
pnpm dev
```

Optional: point the proxy at a different backend base URL:

```bash
cd apps/web
FCE_API_BASE_URL=http://localhost:8000 pnpm dev
```

## Pages

- `/live` curated global live run dashboard (starts via backend `/live/run`)
- `/datasets` create/list datasets (demo, empty, seeded DexScreener)
- `/prompt-templates` create/list prompt templates
- `/runs` create/list replay runs (queued to backend worker)
- `/runs/:runId` run detail: equity timeline + decisions + summary
