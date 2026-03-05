import * as path from "node:path";

import { expect, Page } from "@playwright/test";

import { readServerInfo } from "./server-info";

function projectDir() {
  return path.resolve(__dirname, "..");
}

export function origins() {
  const info = readServerInfo(projectDir());
  return { webOrigin: info.webOrigin, backendOrigin: info.backendOrigin, llmOrigin: info.llmOrigin };
}

export async function gotoPath(page: Page, p: string) {
  const { webOrigin } = origins();
  await page.goto(`${webOrigin}${p}`);
}

export async function navTo(page: Page, name: string) {
  await page.getByRole("link", { name }).click();
}

export async function createDataset(
  page: Page,
  opts: {
    category: "spot" | "sentiment";
    source: string;
    start: string;
    end: string;
    params?: Record<string, unknown>;
  },
) {
  const { webOrigin } = origins();
  const createRes = await page.request.post(`${webOrigin}/api/v4t/datasets`, {
    data: {
      category: opts.category,
      source: opts.source,
      start: opts.start,
      end: opts.end,
      params: opts.params ?? {},
    },
  });

  expect(createRes.ok()).toBeTruthy();
  const created = (await createRes.json()) as { dataset_id: string };
  expect(created.dataset_id).toBeTruthy();

  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    const getRes = await page.request.get(
      `${webOrigin}/api/v4t/datasets/${created.dataset_id}`,
    );
    expect(getRes.ok()).toBeTruthy();
    const ds = (await getRes.json()) as { status: string; error?: string | null };

    const status = String(ds.status ?? "").trim().toLowerCase();
    if (status === "ready") return created.dataset_id;
    if (status === "failed") {
      throw new Error(`Dataset ${created.dataset_id} failed: ${ds.error ?? "unknown"}`);
    }
    await page.waitForTimeout(500);
  }

  throw new Error(`Timed out waiting for dataset ${created.dataset_id} to become ready`);
}

export async function createPromptTemplate(page: Page) {
  await gotoPath(page, "/prompt-templates");

  const createButton = page.getByRole("button", { name: "Create" });
  const respPromise = page.waitForResponse((r) =>
    r.url().includes("/api/v4t/prompt_templates") && r.request().method() === "POST",
  );
  await createButton.click();
  const resp = await respPromise;
  expect(resp.ok()).toBeTruthy();
  const body = (await resp.json()) as { template_id: string };
  expect(body.template_id).toBeTruthy();
  return body.template_id;
}

export async function createRun(page: Page, opts: {
  modelKey?: string;
  promptText?: string;
}) {
  await gotoPath(page, "/runs");

  if (opts.modelKey) {
    await page.getByLabel("model_key").fill(opts.modelKey);
  }

  const promptText =
    opts.promptText ??
    `E2E replay prompt. Return ONLY JSON like {"schema_version":1,"targets":{"spot:demo:DEMO":0.25}}.`;
  await page.getByRole("button", { name: /pro mode/i }).click();
  await page
    .locator('textarea[placeholder="Enter your custom prompt..."]')
    .fill(promptText);

  const createButton = page.getByRole("button", { name: "Create + Enqueue Run" });
  const respPromise = page.waitForResponse((r) =>
    r.url().includes("/api/v4t/runs") && r.request().method() === "POST",
  );
  await createButton.click();
  const resp = await respPromise;
  expect(resp.ok()).toBeTruthy();
  const body = (await resp.json()) as { run_id: string };
  expect(body.run_id).toBeTruthy();

  const runCard = page
    .locator("div.rounded-3xl")
    .filter({ has: page.getByText(body.run_id, { exact: true }) })
    .first();
  await expect(runCard).toBeVisible({ timeout: 60_000 });
  await expect(runCard).toContainText(/finished|failed|cancelled/i, { timeout: 120_000 });
  return body.run_id;
}

export async function waitForRunFinishedOnDetail(page: Page, runId: string) {
  await gotoPath(page, `/runs/${runId}`);
  await expect(page.getByText(runId)).toBeVisible();

  const statusValue = page.getByTestId("run-status");
  await expect(statusValue).toContainText(/finished|failed|cancelled/i, { timeout: 120_000 });

  await expect(page.locator("table").first()).toBeVisible();
}

export async function startAndStopLive(page: Page) {
  await gotoPath(page, "/live");

  await page.getByRole("button", { name: /pro mode/i }).click();
  await page
    .locator('textarea[placeholder="Enter your custom prompt..."]')
    .fill(
      `E2E live prompt. Return ONLY JSON like {"schema_version":1,"targets":{"spot:demo:DEMO":0.25}}.`,
    );

  const startButton = page.getByRole("button", { name: "Start Live Run" });
  const respPromise = page.waitForResponse((r) =>
    r.url().includes("/api/v4t/live/run") && r.request().method() === "POST",
  );
  await startButton.click();
  const resp = await respPromise;
  expect(resp.ok()).toBeTruthy();
  const body = (await resp.json()) as { run_id: string };
  expect(body.run_id).toBeTruthy();

  await expect(page.getByText(/Current Live Run/i)).toBeVisible();
  await expect(page.getByText(body.run_id)).toBeVisible({ timeout: 60_000 });

  const decisionBadge = page
    .locator("tbody span")
    .filter({ hasText: /^(yes|no)$/ });
  await expect(decisionBadge.first()).toBeVisible({ timeout: 120_000 });

  const stopButton = page.getByRole("button", { name: /stop run/i });
  if (await stopButton.isVisible().catch(() => false)) {
    await stopButton.click();
  } else {
    const { webOrigin } = origins();
    const stopRes = await page.request.post(`${webOrigin}/api/v4t/runs/${body.run_id}/stop`);
    expect(stopRes.ok()).toBeTruthy();
  }
}

export async function createArenaSubmission(
  page: Page,
  opts?: {
    modelKey?: string;
    promptText?: string;
  },
) {
  await gotoPath(page, "/arena");

  const modelKey = opts?.modelKey ?? "stub";
  const promptText =
    opts?.promptText ??
    `E2E tournament prompt. Return ONLY JSON like {"schema_version":1,"targets":{"spot:demo:DEMO":0.25}}.`;

  const startButton = page.getByRole("button", { name: "Start a new run" });
  await expect(startButton).toBeEnabled({ timeout: 60_000 });
  await startButton.click();

  const dialog = page.getByRole("dialog", { name: "Start new run" });
  await expect(dialog).toBeVisible({ timeout: 10_000 });

  const modelSelect = dialog.getByLabel("model");
  await expect(modelSelect).toBeEnabled({ timeout: 60_000 });
  await modelSelect.selectOption(modelKey);

  await dialog
    .locator('textarea[placeholder="Enter your custom prompt..."]')
    .fill(promptText);

  const submitButton = dialog.getByRole("button", { name: /^Start run$/ });
  const respPromise = page.waitForResponse((r) =>
    r.url().includes("/api/v4t/arena/submissions") && r.request().method() === "POST",
  );
  await submitButton.click();
  const resp = await respPromise;
  expect(resp.ok()).toBeTruthy();
  const body = (await resp.json()) as { submission_id: string };
  expect(body.submission_id).toBeTruthy();

  await expect(page).toHaveURL(new RegExp(`/arena/submissions/${body.submission_id}(/)?$`));
  const statusValue = page.getByTestId("tournament-run-status");
  await expect(statusValue).toContainText(/finished|failed|cancelled/i, { timeout: 180_000 });
  return body.submission_id;
}

export async function summonDemoArenaSubmission(page: Page) {
  await gotoPath(page, "/arena");

  const summonButton = page.getByRole("button", { name: "Summon Demo Run" });
  await expect(summonButton).toBeEnabled({ timeout: 60_000 });
  const respPromise = page.waitForResponse((r) =>
    r.url().includes("/api/v4t/arena/submissions") && r.request().method() === "POST",
  );
  await summonButton.click();
  const resp = await respPromise;
  expect(resp.ok()).toBeTruthy();
  const body = (await resp.json()) as { submission_id: string };
  expect(body.submission_id).toBeTruthy();

  await expect(page).toHaveURL(new RegExp(`/arena/submissions/${body.submission_id}(/)?$`));
  const statusValue = page.getByTestId("tournament-run-status");
  await expect(statusValue).toContainText(/finished|failed|cancelled/i, { timeout: 180_000 });
  return body.submission_id;
}
