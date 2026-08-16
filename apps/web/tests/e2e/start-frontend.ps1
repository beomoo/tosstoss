$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
$webRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "apps\web"))
$buildDirectory = [System.IO.Path]::GetFullPath((Join-Path $webRoot ".next"))
$buildIdPath = [System.IO.Path]::GetFullPath((Join-Path $buildDirectory "BUILD_ID"))
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
if (
    [System.IO.Path]::GetDirectoryName($buildIdPath) -ne $buildDirectory -or
    [System.IO.Path]::GetFileName($buildIdPath) -ne "BUILD_ID"
) {
    throw "Refusing to start a production build outside the web build directory."
}
if (-not (Test-Path -LiteralPath $buildIdPath -PathType Leaf)) {
    throw "The production BUILD_ID is missing. Run scripts/build.ps1 before E2E."
}

$sentinel = [System.IO.File]::ReadAllText($sentinelPath).Trim()
if ($sentinel -notmatch '^PHASE1_RUNTIME_[0-9a-f]{32}$') {
    throw "The Phase 1 build sentinel has an invalid format."
}
$buildId = [System.IO.File]::ReadAllText($buildIdPath).Trim()
if ([string]::IsNullOrWhiteSpace($buildId) -or $buildId -notmatch '^[A-Za-z0-9_-]{8,128}$') {
    throw "The production BUILD_ID is empty or invalid."
}
if (
    (Get-Item -LiteralPath $buildIdPath).LastWriteTimeUtc -lt
    (Get-Item -LiteralPath $sentinelPath).LastWriteTimeUtc
) {
    throw "The production build predates the current sentinel. Run scripts/build.ps1 again."
}

$env:PHASE1_SERVER_ONLY_SENTINEL = $sentinel
$env:DASHBOARD_API_BASE_URL = "http://127.0.0.1:8000"
$env:NEXT_TELEMETRY_DISABLED = "1"

try {
    Push-Location -LiteralPath $webRoot
    try {
        & npm run start
        if ($LASTEXITCODE -ne 0) {
            throw "E2E production frontend exited with a non-zero status."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    Remove-Item Env:PHASE1_SERVER_ONLY_SENTINEL -ErrorAction SilentlyContinue
    Remove-Item Env:DASHBOARD_API_BASE_URL -ErrorAction SilentlyContinue
}
