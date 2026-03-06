import { spawn } from "node:child_process";
import * as fs from "node:fs";
import * as net from "node:net";
import * as path from "node:path";

import { writeServerInfo } from "./server-info";
import { waitForHttpOk } from "./wait";

function resolveUvBin() {
  const envPath = (process.env.UV_PATH || "").trim();
  if (envPath && fs.existsSync(envPath)) return envPath;
  if (fs.existsSync("/usr/bin/uv")) return "/usr/bin/uv";
  if (fs.existsSync("/usr/local/bin/uv")) return "/usr/local/bin/uv";
  return "uv";
}

async function getFreePort(): Promise<number> {
  return await new Promise((resolve, reject) => {
    const s = net.createServer();
    s.unref();
    s.on("error", reject);
    s.listen(0, "127.0.0.1", () => {
      const addr = s.address();
      s.close(() => {
        if (!addr || typeof addr === "string") return reject(new Error("port lookup failed"));
        resolve(addr.port);
      });
    });
  });
}

function repoRootFromProject(projectDir: string) {
  return path.resolve(projectDir, "..", "..", "..");
}

function resolveFeatherPath(repoRoot: string) {
  const candidates = [
    path.join(repoRoot, "user_data", "data", "binance", "BTC_USDT-1h.feather"),
    path.join(repoRoot, "vibe4trading-backend", "data-loader", "data", "W10", "binance", "BTC_USDT-1h.feather"),
  ];

  const existing = candidates.find((candidate) => fs.existsSync(candidate));
  if (existing) return existing;

  throw new Error(`freqtrade feather file missing: ${candidates.join(" or ")}`);
}

function killQuiet(pid: number, signal: NodeJS.Signals = "SIGTERM") {
  try {
    process.kill(pid, signal);
  } catch {
  }
}

function killGroupQuiet(pid: number, signal: NodeJS.Signals = "SIGTERM") {
  if (!pid) return;
  try {
    process.kill(-pid, signal);
  } catch {
    killQuiet(pid, signal);
  }
}

async function startFakeLlm(opts: { projectDir: string; port: number; seed: string }) {
  const scriptPath = path.join(opts.projectDir, "e2e", "fake-llm-server.mjs");

  const child = spawn(
    process.execPath,
    [scriptPath, "--host", "127.0.0.1", "--port", String(opts.port), "--seed", opts.seed],
    {
      cwd: opts.projectDir,
      env: process.env,
      stdio: "inherit",
      detached: true,
    },
  );

  if (!child.pid) throw new Error("Fake LLM server failed to start (no pid)");

  const exitedEarly = new Promise<never>((_, reject) => {
    child.once("exit", (code, signal) => {
      reject(new Error(`Fake LLM server exited early (code=${code} signal=${signal})`));
    });
    child.once("error", (e) => reject(e));
  });

  await Promise.race([
    exitedEarly,
    waitForHttpOk(`http://127.0.0.1:${opts.port}/health`, 30_000),
  ]);

  return child.pid;
}

async function startBackend(opts: {
  repoRoot: string;
  port: number;
  dbPath: string;
  llmOrigin: string;
  arenaDatasetIds?: string;
}) {
  const backendDir = path.join(opts.repoRoot, "vibe4trading-backend");

  const uvBin = resolveUvBin();

  const env = {
    ...process.env,
    V4T_DATABASE_URL: `sqlite:///${opts.dbPath}`,
    V4T_CELERY_ALWAYS_EAGER: "1",
    V4T_BYPASS_AUTH: "1",
    V4T_ARENA_DATASET_IDS: (opts.arenaDatasetIds ?? "").trim(),
    V4T_LIVE_MAX_TICKS: process.env.V4T_LIVE_MAX_TICKS ?? "1",
    V4T_LIVE_BASE_INTERVAL_SECONDS: process.env.V4T_LIVE_BASE_INTERVAL_SECONDS ?? "1",
    V4T_LIVE_MIN_INTERVAL_SECONDS: process.env.V4T_LIVE_MIN_INTERVAL_SECONDS ?? "1",
    V4T_LIVE_PRICE_TICK_SECONDS: process.env.V4T_LIVE_PRICE_TICK_SECONDS ?? "1",
    V4T_LLM_BASE_URL: opts.llmOrigin,
    V4T_LLM_API_KEY: process.env.V4T_LLM_API_KEY ?? "e2e",
    V4T_LLM_MAX_RETRIES: process.env.V4T_LLM_MAX_RETRIES ?? "3",
  } satisfies NodeJS.ProcessEnv;

  const child = spawn(
    uvBin,
    [
      "run",
      "python",
      "-m",
      "uvicorn",
      "v4t.api.app:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(opts.port),
    ],
    {
      cwd: backendDir,
      env,
      stdio: "inherit",
      detached: true,
    },
  );

  if (!child.pid) throw new Error("Backend failed to start (no pid)");

  const exitedEarly = new Promise<never>((_, reject) => {
    child.once("exit", (code, signal) => {
      reject(new Error(`Backend exited early (code=${code} signal=${signal})`));
    });
    child.once("error", (e) => reject(e));
  });

  await Promise.race([exitedEarly, waitForHttpOk(`http://127.0.0.1:${opts.port}/health`, 60_000)]);
  const health = await fetch(`http://127.0.0.1:${opts.port}/health`, {
    headers: { accept: "application/json" },
  }).then((r) => r.json() as Promise<{ status?: string }>);
  if (health.status !== "ok") throw new Error("Backend health check returned unexpected body");
  return child.pid;
}

async function waitForDatasetReady(backendOrigin: string, datasetId: string) {
  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    const getRes = await fetch(`${backendOrigin}/datasets/${datasetId}`, {
      headers: { accept: "application/json" },
    });
    if (!getRes.ok) {
      throw new Error(`dataset status fetch failed (id=${datasetId} http=${getRes.status})`);
    }
    const ds = (await getRes.json()) as { status?: string; error?: string | null };
    const status = String(ds.status ?? "").trim().toLowerCase();
    if (status === "ready") return;
    if (status === "failed") {
      throw new Error(`dataset import failed (id=${datasetId} err=${ds.error ?? "unknown"})`);
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`timed out waiting for dataset ready (id=${datasetId})`);
}

async function createDatasetReady(
  backendOrigin: string,
  req: {
    category: "spot" | "sentiment";
    source: string;
    start: string;
    end: string;
    params?: Record<string, unknown>;
  },
) {
  const res = await fetch(`${backendOrigin}/datasets`, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify({
      category: req.category,
      source: req.source,
      start: req.start,
      end: req.end,
      params: req.params ?? {},
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`dataset create failed (http=${res.status} body=${text})`);
  }
  const created = (await res.json()) as { dataset_id?: string };
  const datasetId = String(created.dataset_id ?? "");
  if (!datasetId) throw new Error("dataset create returned empty dataset_id");
  await waitForDatasetReady(backendOrigin, datasetId);
  return datasetId;
}

async function startWeb(opts: {
  projectDir: string;
  port: number;
  backendOrigin: string;
  marketDatasetId: string;
  sentimentDatasetId: string;
}) {
  const env = {
    ...process.env,
    V4T_API_BASE_URL: opts.backendOrigin,
    PORT: String(opts.port),
    NODE_ENV: "test",
    NEXT_PUBLIC_V4T_MARKET_DATASET_ID: opts.marketDatasetId,
    NEXT_PUBLIC_V4T_SENTIMENT_DATASET_ID: opts.sentimentDatasetId,
  } satisfies NodeJS.ProcessEnv;

  const child = spawn("pnpm", ["exec", "next", "dev", "--webpack", "-p", String(opts.port)], {
    cwd: opts.projectDir,
    env,
    stdio: "inherit",
    detached: true,
  });

  if (!child.pid) throw new Error("Web failed to start (no pid)");

  const exitedEarly = new Promise<never>((_, reject) => {
    child.once("exit", (code, signal) => {
      reject(new Error(`Web exited early (code=${code} signal=${signal})`));
    });
    child.once("error", (e) => reject(e));
  });

  await Promise.race([exitedEarly, waitForHttpOk(`http://127.0.0.1:${opts.port}/`, 90_000)]);
  return child.pid;
}

export default async function globalSetup() {
  const projectDir = path.resolve(__dirname, "..");
  const repoRoot = repoRootFromProject(projectDir);

  const e2eDir = path.join(projectDir, ".e2e");
  fs.mkdirSync(e2eDir, { recursive: true });

  const dbPath = path.join(e2eDir, `v4t-e2e-${Date.now()}-${process.pid}.db`);
  const backendPort = process.env.E2E_BACKEND_PORT
    ? Number(process.env.E2E_BACKEND_PORT)
    : await getFreePort();
  const webPort = process.env.E2E_WEB_PORT ? Number(process.env.E2E_WEB_PORT) : await getFreePort();
  const llmPort = process.env.E2E_LLM_PORT ? Number(process.env.E2E_LLM_PORT) : await getFreePort();

  let backendPid = 0;
  let webPid = 0;
  let llmPid = 0;
  try {
    const llmOrigin = `http://127.0.0.1:${llmPort}`;
    llmPid = await startFakeLlm({ projectDir, port: llmPort, seed: process.env.V4T_E2E_RUN_ID ?? "e2e" });

    backendPid = await startBackend({ repoRoot, port: backendPort, dbPath, llmOrigin });
    const backendOrigin = `http://127.0.0.1:${backendPort}`;

    const featherPath = resolveFeatherPath(repoRoot);

    const marketId = "spot:demo:DEMO";
    const runStartIso = new Date("2026-03-01T00:00:00.000Z").toISOString();
    const runEndIso = new Date("2026-03-01T06:00:00.000Z").toISOString();

    const marketDatasetId = await createDatasetReady(backendOrigin, {
      category: "spot",
      source: "freqtrade",
      start: runStartIso,
      end: runEndIso,
      params: { market_id: marketId, feather_path: featherPath },
    });
    const sentimentDatasetId = await createDatasetReady(backendOrigin, {
      category: "sentiment",
      source: "rss",
      start: runStartIso,
      end: runEndIso,
      params: { market_id: marketId },
    });

    const arenaBase = new Date("2026-02-25T00:00:00.000Z");
    const arenaIds: string[] = [];
    for (let i = 0; i < 10; i++) {
      const st = new Date(arenaBase.getTime() + i * 12 * 3600 * 1000);
      const en = new Date(st.getTime() + 12 * 3600 * 1000);
      const id = await createDatasetReady(backendOrigin, {
        category: "spot",
        source: "freqtrade",
        start: st.toISOString(),
        end: en.toISOString(),
        params: { market_id: marketId, feather_path: featherPath },
      });
      arenaIds.push(id);
    }

    killGroupQuiet(backendPid);
    await new Promise((r) => setTimeout(r, 750));
    backendPid = await startBackend({
      repoRoot,
      port: backendPort,
      dbPath,
      llmOrigin,
      arenaDatasetIds: arenaIds.join(","),
    });

    const envMarkets = await fetch(`${backendOrigin}/arena/markets`, {
      headers: { accept: "application/json" },
    }).then((r) => r.json() as Promise<unknown>);
    if (!Array.isArray(envMarkets) || envMarkets.length < 1) {
      throw new Error(
        `arena env markets not configured after restart (markets=${JSON.stringify(envMarkets)})`,
      );
    }

    const createModelRes = await fetch(`${backendOrigin}/admin/models`, {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify({ model_key: "gpt-4o-mini", label: "E2E Fake LLM", enabled: true }),
    });
    if (!createModelRes.ok && createModelRes.status !== 409) {
      const text = await createModelRes.text().catch(() => "");
      throw new Error(`admin model create failed (http=${createModelRes.status} body=${text})`);
    }

    webPid = await startWeb({
      projectDir,
      port: webPort,
      backendOrigin,
      marketDatasetId,
      sentimentDatasetId,
    });

    writeServerInfo(projectDir, {
      webOrigin: `http://127.0.0.1:${webPort}`,
      backendOrigin,
      llmOrigin,
      dbPath,
      backendPid,
      webPid,
      llmPid,
    });
  } catch (e) {
    if (webPid) killGroupQuiet(webPid);
    if (backendPid) killGroupQuiet(backendPid);
    if (llmPid) killGroupQuiet(llmPid);
    throw e;
  }
}
