#!/usr/bin/env bash
PRERENDER_URL="${PRERENDER_URL:-http://localhost:3001}"
SITE_URL="${SITE_URL:-http://frontend:3000}"
ROUTES=("/" "/arena" "/leaderboard" "/contact" "/privacy")
for route in "${ROUTES[@]}"; do
  echo "Warming: ${route}"
  curl -s -o /dev/null "${PRERENDER_URL}/render?url=${SITE_URL}${route}"
done
echo "Cache warm complete."
