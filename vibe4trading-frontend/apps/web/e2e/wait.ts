import * as http from "node:http";
import * as https from "node:https";

export async function waitForHttpOk(url: string, timeoutMs: number) {
  const deadline = Date.now() + timeoutMs;
  let lastErr: unknown = undefined;

  while (Date.now() < deadline) {
    try {
      const status = await getStatus(url);
      if (status && status >= 200 && status < 400) return;
    } catch (e) {
      lastErr = e;
    }
    await sleep(250);
  }

  throw new Error(`Timed out waiting for ${url}. Last error: ${String(lastErr)}`);
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function getStatus(urlStr: string): Promise<number | null> {
  return new Promise((resolve, reject) => {
    const u = new URL(urlStr);
    const lib = u.protocol === "https:" ? https : http;
    const req = lib.request(
      {
        protocol: u.protocol,
        hostname: u.hostname,
        port: u.port,
        path: u.pathname + u.search,
        method: "GET",
        headers: { accept: "text/html,application/json" },
      },
      (res) => {
        res.resume();
        resolve(res.statusCode ?? null);
      },
    );
    req.on("error", reject);
    req.end();
  });
}
