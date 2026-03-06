import * as http from "node:http";

function intArg(name, fallback) {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx === -1) return fallback;
  const raw = process.argv[idx + 1];
  const v = Number(raw);
  if (!Number.isFinite(v) || v <= 0) return fallback;
  return v;
}

function strArg(name, fallback) {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx === -1) return fallback;
  const raw = process.argv[idx + 1];
  return typeof raw === "string" && raw.length ? raw : fallback;
}

function hash32(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function clamp01(x) {
  if (x < 0) return 0;
  if (x > 1) return 1;
  return x;
}

function jsonResponse(res, status, obj) {
  const body = Buffer.from(JSON.stringify(obj));
  res.writeHead(status, {
    "content-type": "application/json",
    "content-length": String(body.length),
  });
  res.end(body);
}

function textResponse(res, status, text) {
  const body = Buffer.from(String(text));
  res.writeHead(status, {
    "content-type": "text/plain; charset=utf-8",
    "content-length": String(body.length),
  });
  res.end(body);
}

async function readJson(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const raw = Buffer.concat(chunks).toString("utf8");
  if (!raw.trim()) return null;
  return JSON.parse(raw);
}

function buildDecisionContent(rng, opts) {
  const marketId = opts.marketId;

  const roll = rng();
  let targets;
  let rationale;
  let confidence;
  let keySignals;

  if (roll < 0.08) {
    targets = { "spot:demo:OTHER": 0.25 };
    rationale = "I found a better opportunity elsewhere.";
    confidence = 0.41;
    keySignals = ["hallucinated_market"];
  } else if (roll < 0.16) {
    targets = { [marketId]: -0.1 };
    rationale = "Shorting based on bearish momentum.";
    confidence = 0.48;
    keySignals = ["bearish_momentum"];
  } else if (roll < 0.28) {
    targets = { [marketId]: 1.5 };
    rationale = "High conviction; go max leverage.";
    confidence = 0.72;
    keySignals = ["overconfident"];
  } else {
    const base = 0.15 + rng() * 0.7;
    targets = { [marketId]: Number(clamp01(base).toFixed(2)) };
    rationale = "Balancing trend and risk; moderate exposure.";
    confidence = Number((0.45 + rng() * 0.45).toFixed(2));
    keySignals = ["trend", "volatility", "risk_budget"];
  }

  const obj = {
    schema_version: 1,
    targets,
    confidence,
    key_signals: keySignals,
    rationale,
  };

  const wrap = rng();
  const jsonText = JSON.stringify(obj);
  if (wrap < 0.25) return `Here is the JSON decision:\n\n${jsonText}`;
  if (wrap < 0.5) return `\`\`\`json\n${jsonText}\n\`\`\``;
  return jsonText;
}

function buildSummaryContent(rng, reqBody) {
  const user = (reqBody?.messages?.[1]?.content || "").toString();
  const retMatch = user.match(/"return_pct"\s*:\s*"([^"]+)"/);
  const retPct = retMatch ? retMatch[1] : "?";
  const mood = rng() < 0.5 ? "concise" : "opinionated";
  return `(${mood} fake) Run complete. return_pct=${retPct}. Decisions included occasional invalid JSON; fallback held prior target.`;
}

function openAiChatCompletion(content, model) {
  return {
    id: `chatcmpl_fake_${Date.now()}`,
    object: "chat.completion",
    created: Math.floor(Date.now() / 1000),
    model: model || "fake-model",
    choices: [{ index: 0, message: { role: "assistant", content }, finish_reason: "stop" }],
    usage: { prompt_tokens: 42, completion_tokens: Math.max(1, Math.ceil(content.length / 4)), total_tokens: 42 },
  };
}

async function main() {
  const port = intArg("port", 0);
  const host = strArg("host", "127.0.0.1");
  const seedStr = strArg("seed", "e2e");
  const seed = hash32(seedStr);

  const stats = {
    seed: seedStr,
    startedAt: new Date().toISOString(),
    requests: 0,
    chatCompletions: 0,
    simulated429: 0,
    simulated500: 0,
    simulatedMalformedJson: 0,
  };

  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url || "/", `http://${host}`);
      if (req.method === "GET" && url.pathname === "/health") {
        return jsonResponse(res, 200, { status: "ok" });
      }
      if (req.method === "GET" && url.pathname === "/stats") {
        return jsonResponse(res, 200, stats);
      }

      if (req.method !== "POST" || url.pathname !== "/chat/completions") {
        return textResponse(res, 404, "not found");
      }

      stats.requests += 1;
      stats.chatCompletions += 1;

      const body = await readJson(req);
      const model = body?.model;
      const system = (body?.messages?.[0]?.content || "").toString();

      const rng = mulberry32((seed ^ stats.requests) >>> 0);

      if (stats.requests % 23 === 1) {
        stats.simulated429 += 1;
        return jsonResponse(res, 429, { error: { message: "rate_limited", type: "rate_limit" } });
      }
      if (stats.requests % 41 === 7) {
        stats.simulated500 += 1;
        return jsonResponse(res, 500, { error: { message: "upstream_error", type: "server_error" } });
      }

      let content;
      if (system.includes("trading run reviewer")) {
        content = buildSummaryContent(rng, body);
      } else {
        if (stats.requests % 29 === 0) {
          stats.simulatedMalformedJson += 1;
          content = "{\"schema_version\":1,\"targets\":{\"spot:demo:DEMO\":0.25}";
        } else {
          content = buildDecisionContent(rng, { marketId: "spot:demo:DEMO" });
        }
      }

      return jsonResponse(res, 200, openAiChatCompletion(content, model));
    } catch (e) {
      return jsonResponse(res, 500, { error: { message: String(e && e.message ? e.message : e) } });
    }
  });

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, host, () => resolve());
  });

  const addr = server.address();
  const actualPort = typeof addr === "object" && addr ? addr.port : port;
  console.log(`[fake-llm] listening on http://${host}:${actualPort}`);
}

main().catch((e) => {
  console.error("[fake-llm] fatal", e);
  process.exit(1);
});
