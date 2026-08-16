. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
$env:NEXT_TELEMETRY_DISABLED = "1"

Invoke-Checked -FilePath $python -ArgumentList @("-m", "pip", "check")
Invoke-Checked -FilePath "npm" -ArgumentList @("ls", "--depth=0", "--workspaces", "--include-workspace-root")
Invoke-PhaseScript -Name "lint.ps1"
Invoke-PhaseScript -Name "typecheck.ps1"
Invoke-Checked -FilePath $python -ArgumentList @("-m", "pytest", "tests/backend", "-q")
Invoke-PhaseScript -Name "migrate.ps1" -ArgumentList @("-Action", "Test")
Invoke-PhaseScript -Name "import-fixtures.ps1" -ArgumentList @("-VerifyIdempotency")
Invoke-Checked -FilePath "npm" -ArgumentList @("run", "test", "--workspace", "apps/web")
Invoke-PhaseScript -Name "export-openapi.ps1" -ArgumentList @("-Check")
Invoke-PhaseScript -Name "build.ps1"
Invoke-PhaseScript -Name "e2e.ps1"
Invoke-PhaseScript -Name "secret-scan.ps1"
Invoke-PhaseScript -Name "policy-scan.ps1"

Write-Host "All Phase 1 checks passed."
