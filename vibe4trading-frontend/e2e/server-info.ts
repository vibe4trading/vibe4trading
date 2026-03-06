import * as fs from "node:fs";
import * as path from "node:path";

export type ServerInfo = {
  webOrigin: string;
  backendOrigin: string;
  llmOrigin?: string;
  dbPath: string;
  backendPid: number;
  webPid: number;
  llmPid?: number;
};

function runId() {
  const raw = (process.env.V4T_E2E_RUN_ID || "default").trim();
  return raw.replace(/[^a-zA-Z0-9_.-]/g, "_");
}

export function serverInfoPath(projectDir: string) {
  return path.join(projectDir, ".e2e", runId(), "server-info.json");
}

export function readServerInfo(projectDir: string): ServerInfo {
  const p = serverInfoPath(projectDir);
  const raw = fs.readFileSync(p, "utf8");
  return JSON.parse(raw) as ServerInfo;
}

export function writeServerInfo(projectDir: string, info: ServerInfo) {
  const dir = path.dirname(serverInfoPath(projectDir));
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(serverInfoPath(projectDir), JSON.stringify(info, null, 2));
}
