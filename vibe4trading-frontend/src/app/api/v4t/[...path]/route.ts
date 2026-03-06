import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

const MAX_BODY_BYTES = 1024 * 1024; // 1 MB

function getBackendBaseUrl() {
  // Server-only env var. Keep a default for local dev.
  return process.env.V4T_API_BASE_URL ?? "http://localhost:8000";
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
  
  const jwt = await getToken({ req: request, secret: process.env.AUTH_SECRET });
  const accessToken = typeof jwt?.accessToken === "string" ? jwt.accessToken : null;
  const accessTokenExpires =
    typeof jwt?.accessTokenExpires === "number" ? jwt.accessTokenExpires : null;
  const hasSessionJwt = jwt !== null;
  const hasFreshAccessToken =
    !!accessToken && (!accessTokenExpires || Date.now() < accessTokenExpires - 30_000);

  if (hasFreshAccessToken && accessToken) {
    headers["authorization"] = `Bearer ${accessToken}`;
  } else if (!hasSessionJwt) {
    const auth = request.headers.get("authorization");
    if (auth) headers["authorization"] = auth;
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    const contentLength = request.headers.get("content-length");
    if (contentLength && parseInt(contentLength, 10) > MAX_BODY_BYTES) {
      return NextResponse.json(
        { detail: "Request body too large" },
        { status: 413 },
      );
    }
    init.body = await request.text();
    if (init.body && (init.body as string).length > MAX_BODY_BYTES) {
      return NextResponse.json(
        { detail: "Request body too large" },
        { status: 413 },
      );
    }
  }

  try {
    const res = await fetch(targetUrl, init);

    const outHeaders: Record<string, string> = {
      "content-type": res.headers.get("content-type") ?? "application/json",
    };
    const cacheControl = res.headers.get("cache-control");
    if (cacheControl) outHeaders["cache-control"] = cacheControl;
    const xAccelBuffering = res.headers.get("x-accel-buffering");
    if (xAccelBuffering) outHeaders["x-accel-buffering"] = xAccelBuffering;

    return new Response(res.body, {
      status: res.status,
      headers: outHeaders,
    });
  } catch {
    return NextResponse.json(
      { detail: "Backend unavailable" },
      { status: 502 },
    );
  }
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

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxy(request, await context.params);
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxy(request, await context.params);
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxy(request, await context.params);
}
