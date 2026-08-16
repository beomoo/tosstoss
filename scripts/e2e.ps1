. (Join-Path $PSScriptRoot "common.ps1")

$env:NEXT_TELEMETRY_DISABLED = "1"
Invoke-Checked -FilePath "npm" -ArgumentList @("run", "test:e2e", "--workspace", "apps/web")
