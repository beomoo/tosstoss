. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
$repoRoot = Get-RepoRoot
$env:NEXT_TELEMETRY_DISABLED = "1"
Invoke-Checked -FilePath $python -ArgumentList @(
    "-m", "compileall", "-q", "services/api/src"
)

$runtimeDirectory = Join-Path $repoRoot "var"
[System.IO.Directory]::CreateDirectory($runtimeDirectory) | Out-Null
$sentinelPath = Join-Path $runtimeDirectory "phase-01-build-sentinel.txt"
$sentinelValue = "PHASE1_RUNTIME_" + [System.Guid]::NewGuid().ToString("N")
[System.IO.File]::WriteAllText($sentinelPath, $sentinelValue)
$env:PHASE1_SERVER_ONLY_SENTINEL = $sentinelValue

try {
    Invoke-Checked -FilePath "npm" -ArgumentList @(
        "run", "build", "--workspace", "apps/web"
    )
}
finally {
    Remove-Item Env:PHASE1_SERVER_ONLY_SENTINEL -ErrorAction SilentlyContinue
}
