$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
$runtimeDirectory = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var"))
$sentinelPath = [System.IO.Path]::GetFullPath(
    (Join-Path $runtimeDirectory "phase-01-build-sentinel.txt")
)
if (
    [System.IO.Path]::GetDirectoryName($sentinelPath) -ne $runtimeDirectory -or
    [System.IO.Path]::GetFileName($sentinelPath) -ne "phase-01-build-sentinel.txt"
) {
    throw "Refusing to read an E2E sentinel outside the repository runtime directory."
}
if (-not (Test-Path -LiteralPath $sentinelPath -PathType Leaf)) {
    throw "The Phase 1 build sentinel is missing. Run scripts/build.ps1 before E2E."
}

$sentinel = [System.IO.File]::ReadAllText($sentinelPath)
if ($sentinel -notmatch '^PHASE1_RUNTIME_[0-9a-f]{32}$') {
    throw "The Phase 1 build sentinel has an invalid format."
}

$env:PHASE1_SERVER_ONLY_SENTINEL = $sentinel
$env:DASHBOARD_API_BASE_URL = "http://127.0.0.1:8000"
$env:NEXT_TELEMETRY_DISABLED = "1"

try {
    & npm run dev
    if ($LASTEXITCODE -ne 0) {
        throw "E2E frontend exited with a non-zero status."
    }
}
finally {
    Remove-Item Env:PHASE1_SERVER_ONLY_SENTINEL -ErrorAction SilentlyContinue
    Remove-Item Env:DASHBOARD_API_BASE_URL -ErrorAction SilentlyContinue
}
