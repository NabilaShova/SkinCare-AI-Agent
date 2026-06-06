#!/usr/bin/env sh
# Cron-friendly script to sync all connected Shopify stores.
# Example crontab (every 6 hours):
# 0 */6 * * * /path/to/scripts/production_sync.sh

set -eu

API_URL="${API_URL:-http://localhost:8000}"
ADMIN_API_KEY="${ADMIN_API_KEY:?Set ADMIN_API_KEY}"

curl -sS -X POST "${API_URL}/api/shopify/sync-all" \
  -H "X-Admin-API-Key: ${ADMIN_API_KEY}" \
  -H "Content-Type: application/json"

echo ""
