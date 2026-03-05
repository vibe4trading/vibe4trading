# Vibe4Trading Frontend

Next.js dashboard for the Vibe4Trading MVP.

## Local dev

Backend should be running at `http://localhost:8000` (default). The frontend proxies API calls via
`/api/v4t/*` so you don't need CORS locally.

```bash
cd apps/web
pnpm dev
```

Optional: point the proxy at a different backend base URL:

```bash
cd apps/web
V4T_API_BASE_URL=http://localhost:8000 pnpm dev
```

## Pages

- `/live` curated global live run dashboard (starts via backend `/live/run`)
- `/prompt-templates` create/list prompt templates
- `/runs` create/list replay runs (queued to backend worker)
- `/runs/:runId` run detail: equity timeline + decisions + summary
