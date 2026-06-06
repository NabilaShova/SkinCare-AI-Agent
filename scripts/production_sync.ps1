param(
  [string]$ApiUrl = $env:API_URL,
  [string]$AdminApiKey = $env:ADMIN_API_KEY
)

if (-not $ApiUrl) { $ApiUrl = "http://localhost:8000" }
if (-not $AdminApiKey) { throw "Set ADMIN_API_KEY before running production sync." }

Invoke-RestMethod `
  -Method Post `
  -Uri "$ApiUrl/api/shopify/sync-all" `
  -Headers @{ "X-Admin-API-Key" = $AdminApiKey }
