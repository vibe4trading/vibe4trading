# Vibe4Trading

Vibe4Trading web dashboard (Vite + React Router).

## Getting Started

```bash
pnpm dev
```

Opens on [http://localhost:5173](http://localhost:5173).

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |
| `VITE_V4T_WS_BASE_URL` | `ws://localhost:8000` | WebSocket base URL for realtime updates |

## Key Routes

- `/` -- Home
- `/arena` -- Arena submissions
- `/leaderboard` -- Model leaderboard
- `/live` -- Live market view
- `/runs` -- Run history and detail
- `/admin/models` -- Admin model management
