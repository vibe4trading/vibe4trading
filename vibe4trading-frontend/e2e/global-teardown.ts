import * as fs from "node:fs";
import * as path from "node:path";

import { readServerInfo, serverInfoPath } from "./server-info";

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

async function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export default async function globalTeardown() {
  const projectDir = path.resolve(__dirname, "..");
  const p = serverInfoPath(projectDir);
  if (!fs.existsSync(p)) return;

  const info = readServerInfo(projectDir);

  killGroupQuiet(info.webPid, "SIGTERM");
  killGroupQuiet(info.backendPid, "SIGTERM");
  if (info.llmPid) killGroupQuiet(info.llmPid, "SIGTERM");
  await sleep(1500);
  killGroupQuiet(info.webPid, "SIGKILL");
  killGroupQuiet(info.backendPid, "SIGKILL");
  if (info.llmPid) killGroupQuiet(info.llmPid, "SIGKILL");

  try {
    fs.rmSync(path.dirname(p), { recursive: true, force: true });
  } catch {
  }
}
