# Launch Render Blueprint after code is pushed to GitHub.
# Prerequisites: Render CLI installed + authenticated (render login)
# Usage: .\scripts\render_blueprint_launch.ps1

param(
  [string]$Repo = "https://github.com/NabilaShova/SkinCare-AI-Agent",
  [string]$Branch = "main"
)

Write-Host "Validating render.yaml..."
render blueprints validate render.yaml
if ($LASTEXITCODE -ne 0) {
  throw "render.yaml validation failed"
}

Write-Host "Launching Blueprint from $Repo ($Branch)..."
render blueprint launch `
  --file render.yaml `
  --repo $Repo `
  --branch $Branch

Write-Host "Done. Open Render Dashboard to enter secret env vars and monitor deploys."
