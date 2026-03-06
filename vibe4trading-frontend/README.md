Vibe4Trading web dashboard (Next.js App Router).

## Getting Started

Run the development server:

```bash
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

This app proxies backend API calls through `GET/POST /api/v4t/*`.

By default it targets `http://localhost:8000`. Override with:

```bash
V4T_API_BASE_URL=http://localhost:8000 pnpm dev
```

Realtime updates (WebSocket) default to `ws://localhost:8000` in local dev. Override with:

```bash
NEXT_PUBLIC_V4T_WS_BASE_URL=ws://localhost:8000 pnpm dev
```

Key routes:

- `/live`
- `/prompt-templates`
- `/runs`

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
