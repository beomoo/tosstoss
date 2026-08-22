$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
. (Join-Path $repoRoot "scripts\common.ps1")
if ([System.IO.Path]::GetFullPath((Get-RepoRoot)) -cne $repoRoot) {
    throw "The E2E backend resolved an unexpected repository root."
}
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "The repository .venv is missing. Run scripts/setup.ps1 first."
}
$uvicornLogConfig = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "services\api\uvicorn_log_config.json")
)
if (-not (Test-Path -LiteralPath $uvicornLogConfig -PathType Leaf)) {
    throw "The Uvicorn JSON log configuration is missing."
}

$fixtureDirectory = Join-Path $repoRoot "fixtures\phase_01"
$runtimeDirectory = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var"))
Assert-SafeRepositoryPath -Path $runtimeDirectory
[System.IO.Directory]::CreateDirectory($runtimeDirectory) | Out-Null
Assert-SafeRepositoryPath -Path $runtimeDirectory
$webBuildDirectory = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "apps\web\.next"))
$buildIdPath = [System.IO.Path]::GetFullPath((Join-Path $webBuildDirectory "BUILD_ID"))
$sentinelPath = [System.IO.Path]::GetFullPath(
    (Join-Path $runtimeDirectory "phase-01-build-sentinel.txt")
)
$buildEvidencePath = [System.IO.Path]::GetFullPath(
    (Join-Path $runtimeDirectory "phase-01-build-evidence.json")
)
foreach ($requiredFile in @($buildIdPath, $sentinelPath, $buildEvidencePath)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required current-build evidence is missing: $requiredFile"
    }
}
$buildId = [System.IO.File]::ReadAllText($buildIdPath).Trim()
$sentinel = [System.IO.File]::ReadAllText($sentinelPath).Trim()
if ($buildId -notmatch '^[A-Za-z0-9_-]{8,128}$') {
    throw "The production BUILD_ID is empty or invalid."
}
if ($sentinel -notmatch '^PHASE1_RUNTIME_[0-9a-f]{32}$') {
    throw "The Phase 1 build sentinel has an invalid format."
}
if (
    (Get-Item -LiteralPath $buildIdPath).LastWriteTimeUtc -lt
    (Get-Item -LiteralPath $sentinelPath).LastWriteTimeUtc
) {
    throw "The production build predates the current sentinel."
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

$logDirectory = [System.IO.Path]::GetFullPath((Join-Path $runtimeDirectory "logs"))
Assert-SafeRepositoryPath -Path $logDirectory
[System.IO.Directory]::CreateDirectory($logDirectory) | Out-Null
Assert-SafeRepositoryPath -Path $logDirectory
$apiLogPath = [System.IO.Path]::GetFullPath((Join-Path $logDirectory "phase-01-e2e-api.jsonl"))
Assert-SafeRepositoryPath -Path $apiLogPath
if (
    [System.IO.Path]::GetDirectoryName($apiLogPath) -ne $logDirectory -or
    [System.IO.Path]::GetFileName($apiLogPath) -ne "phase-01-e2e-api.jsonl"
) {
    throw "Refusing to write an E2E API log outside the repository log directory."
}
$coherenceMarker = [ordered]@{
    timestamp = [System.DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    level = "INFO"
    logger = "phase1.e2e"
    event = "e2e_build_coherence"
    build_id = $buildId
    sentinel_sha256 = $sentinelSha256
}
[System.IO.File]::WriteAllText(
    $apiLogPath,
    (($coherenceMarker | ConvertTo-Json -Compress) + [Environment]::NewLine)
)
$configuredDatabasePath = [Environment]::GetEnvironmentVariable(
    "PHASE1_E2E_DATABASE_PATH"
)
if ([string]::IsNullOrWhiteSpace($configuredDatabasePath)) {
    throw "The parent E2E script did not provide a disposable database path."
}
$databasePath = [System.IO.Path]::GetFullPath($configuredDatabasePath)
$taskTempRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "var\tmp\phase-01")
)
$taskTempPrefix = $taskTempRoot.TrimEnd(
    [System.IO.Path]::DirectorySeparatorChar
) + [System.IO.Path]::DirectorySeparatorChar
$databaseDirectory = [System.IO.Path]::GetDirectoryName($databasePath)
$relativeDatabasePath = [System.IO.Path]::GetRelativePath(
    $taskTempRoot,
    $databasePath
)
$relativeSegments = @(
    $relativeDatabasePath.Split(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.StringSplitOptions]::RemoveEmptyEntries
    )
)
if (
    -not $databasePath.StartsWith(
        $taskTempPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -or
    $relativeSegments.Count -ne 2 -or
    $relativeSegments[0] -cnotmatch '^[0-9a-f]{32}$' -or
    $relativeSegments[1] -cne "playwright-e2e.db" -or
    -not (Test-Path -LiteralPath $databaseDirectory -PathType Container) -or
    ((Get-Item -LiteralPath $databaseDirectory).Attributes -band
        [System.IO.FileAttributes]::ReparsePoint)
) {
    throw "Refusing to use an E2E database outside a fresh Phase 1 task directory."
}
Assert-SafeRepositoryPath -Path $databaseDirectory
Assert-SafeRepositoryPath -Path $databasePath
if (Test-Path -LiteralPath $databasePath) {
    throw "The disposable E2E database path must not exist before startup."
}
$normalizedDatabasePath = $databasePath.Replace("\", "/")
$databaseUrl = "sqlite:///$normalizedDatabasePath"

Push-Location -LiteralPath $repoRoot
try {
    & $python -m alembic -x "database_url=$databaseUrl" upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "E2E database migration failed."
    }
    & $python -m toss_dashboard_api.fixtures.importer `
        --database-url $databaseUrl `
        --fixture-dir $fixtureDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "E2E fixture import failed."
    }
}
finally {
    Pop-Location
}

$env:DASHBOARD_DATABASE_URL = $databaseUrl
$env:DASHBOARD_FIXTURE_DIR = $fixtureDirectory
& $python -m uvicorn toss_dashboard_api.main:app `
    --app-dir (Join-Path $repoRoot "services\api\src") `
    --host 127.0.0.1 `
    --port 8000 `
    --no-access-log `
    --log-config $uvicornLogConfig 2>&1 | Tee-Object -FilePath $apiLogPath -Append
$apiExitCode = $LASTEXITCODE
if ($apiExitCode -ne 0) {
    throw "E2E backend exited with a non-zero status."
}
