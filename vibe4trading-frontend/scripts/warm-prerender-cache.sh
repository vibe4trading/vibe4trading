#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# warm-prerender-cache.sh
#
# Two-pass cache warming for prerendered pages:
#   Pass 1 – Hit the prerender service directly to populate its in-memory cache
#   Pass 2 – Hit the frontend nginx with a Googlebot UA to populate proxy_cache
#
# Routes are kept in sync with public/sitemap.xml.
# ---------------------------------------------------------------------------

# ── Configurable defaults ──────────────────────────────────────────────────
PRERENDER_URL="${PRERENDER_URL:-http://localhost:3001}"
SITE_URL="${SITE_URL:-http://frontend:3000}"
NGINX_URL="${NGINX_URL:-http://localhost:3000}"
TIMEOUT="${TIMEOUT:-30}"

# ── Routes (must match public/sitemap.xml) ─────────────────────────────────
ROUTES=(
  "/"
  "/arena"
  "/leaderboard"
  "/contact"
  "/privacy"
)

# ── Helpers ────────────────────────────────────────────────────────────────
FAILED=0

warm_route() {
  local label="$1"
  local url="$2"
  local route="$3"
  local extra_args=("${@:4}")

  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "${TIMEOUT}" "${extra_args[@]}" "${url}" || true)

  if [[ "${http_code}" =~ ^[0-9]+$ && "${http_code}" -ge 200 && "${http_code}" -lt 400 ]]; then
    echo "  ✓ [${label}] ${route} → HTTP ${http_code}"
  else
    echo "  ✗ [${label}] ${route} → HTTP ${http_code}" >&2
    FAILED=1
  fi
}

# ── Pass 1: Warm prerender service directly ────────────────────────────────
echo "═══ Pass 1: Warming prerender cache (${PRERENDER_URL}) ═══"
for route in "${ROUTES[@]}"; do
  warm_route "prerender" "${PRERENDER_URL}/render?url=${SITE_URL}${route}" "${route}"
done

# ── Pass 2: Warm nginx proxy_cache with Googlebot UA ──────────────────────
echo ""
echo "═══ Pass 2: Warming nginx proxy_cache (${NGINX_URL}) with Googlebot UA ═══"
for route in "${ROUTES[@]}"; do
  warm_route "nginx" "${NGINX_URL}${route}" "${route}" \
    -H "User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
done

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
if [[ "${FAILED}" -ne 0 ]]; then
  echo "ERROR: One or more routes failed to warm." >&2
  exit 1
fi

echo "All ${#ROUTES[@]} routes warmed successfully across both passes."
