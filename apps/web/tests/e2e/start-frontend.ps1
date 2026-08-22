$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
. (Join-Path $repoRoot "scripts\common.ps1")
if ([System.IO.Path]::GetFullPath((Get-RepoRoot)) -cne $repoRoot) {
    throw "The E2E frontend resolved an unexpected repository root."
}
$webRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "apps\web"))
$buildDirectory = [System.IO.Path]::GetFullPath((Join-Path $webRoot ".next"))
$buildIdPath = [System.IO.Path]::GetFullPath((Join-Path $buildDirectory "BUILD_ID"))
$runtimeDirectory = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var"))
$sentinelPath = [System.IO.Path]::GetFullPath(
    (Join-Path $runtimeDirectory "phase-01-build-sentinel.txt")
)
$buildEvidencePath = [System.IO.Path]::GetFullPath(
    (Join-Path $runtimeDirectory "phase-01-build-evidence.json")
)
$logDirectory = [System.IO.Path]::GetFullPath((Join-Path $runtimeDirectory "logs"))
$webLogPath = [System.IO.Path]::GetFullPath(
    (Join-Path $logDirectory "phase-01-e2e-web.log")
)
foreach ($mutablePath in @($logDirectory, $webLogPath)) {
    Assert-SafeRepositoryPath -Path $mutablePath
}
if (
    [System.IO.Path]::GetDirectoryName($sentinelPath) -ne $runtimeDirectory -or
    [System.IO.Path]::GetFileName($sentinelPath) -ne "phase-01-build-sentinel.txt"
) {
    throw "Refusing to read an E2E sentinel outside the repository runtime directory."
}
if (-not (Test-Path -LiteralPath $sentinelPath -PathType Leaf)) {
    throw "The Phase 1 build sentinel is missing. Run scripts/build.ps1 before E2E."
}
if (-not (Test-Path -LiteralPath $buildEvidencePath -PathType Leaf)) {
    throw "The Phase 1 build evidence is missing. Run scripts/build.ps1 before E2E."
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
try {
    $buildEvidence = Get-Content -LiteralPath $buildEvidencePath -Raw |
        ConvertFrom-Json -ErrorAction Stop
}
catch {
    throw "The Phase 1 build evidence is not valid JSON."
}
$sentinelSha256 = (Get-FileHash -LiteralPath $sentinelPath -Algorithm SHA256).Hash.ToLowerInvariant()
if (
    $buildEvidence.schema_version -ne 1 -or
    $buildEvidence.build_id -ne $buildId -or
    $buildEvidence.sentinel_sha256 -ne $sentinelSha256
) {
    throw "The Phase 1 build evidence does not match the current production build."
}
if (
    [System.IO.Path]::GetDirectoryName($webLogPath) -ne $logDirectory -or
    [System.IO.Path]::GetFileName($webLogPath) -ne "phase-01-e2e-web.log"
) {
    throw "Refusing to write an E2E web log outside the repository log directory."
}
[System.IO.Directory]::CreateDirectory($logDirectory) | Out-Null
Assert-SafeRepositoryPath -Path $logDirectory
[System.IO.File]::WriteAllText(
    $webLogPath,
    ("PHASE1_E2E_WEB_BUILD_ID=$buildId" + [Environment]::NewLine)
)

$env:PHASE1_SERVER_ONLY_SENTINEL = $sentinel
$env:DASHBOARD_API_BASE_URL = "http://127.0.0.1:8000"
$env:NEXT_TELEMETRY_DISABLED = "1"

try {
    Push-Location -LiteralPath $webRoot
    try {
        & npm run start 2>&1 | Tee-Object -FilePath $webLogPath -Append
        $webExitCode = $LASTEXITCODE
        if ($webExitCode -ne 0) {
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
