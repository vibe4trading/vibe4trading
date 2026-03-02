import { NextRequest } from "next/server";

function getBackendBaseUrl() {
  // Server-only env var. Keep a default for local dev.
  return process.env.FCE_API_BASE_URL ?? "http://localhost:8000";
}

async function proxy(request: NextRequest, params: { path: string[] }) {
  const base = getBackendBaseUrl().replace(/\/$/, "");
  const path = params.path.join("/");

  const incomingUrl = new URL(request.url);
  const targetUrl = `${base}/${path}${incomingUrl.search}`;

  const headers: Record<string, string> = {
    accept: request.headers.get("accept") ?? "application/json",
  };
  const contentType = request.headers.get("content-type");
  if (contentType) headers["content-type"] = contentType;

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  const res = await fetch(targetUrl, init);
  const body = await res.text();

  return new Response(body, {
    status: res.status,
    headers: {
      "content-type": res.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxy(request, await context.params);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxy(request, await context.params);
}
