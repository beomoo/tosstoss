$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "The repository .venv is missing. Run scripts/setup.ps1 first."
}

$fixtureDirectory = Join-Path $repoRoot "fixtures\phase_01"
$runtimeDirectory = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var"))
[System.IO.Directory]::CreateDirectory($runtimeDirectory) | Out-Null
$databasePath = [System.IO.Path]::GetFullPath((Join-Path $runtimeDirectory "playwright-e2e.db"))
if (
    [System.IO.Path]::GetDirectoryName($databasePath) -ne $runtimeDirectory -or
    [System.IO.Path]::GetFileName($databasePath) -ne "playwright-e2e.db"
) {
    throw "Refusing to prepare an E2E database outside the repository runtime directory."
}
if (Test-Path -LiteralPath $databasePath -PathType Leaf) {
    Remove-Item -LiteralPath $databasePath -Force
}
$normalizedDatabasePath = $databasePath.Replace("\", "/")
$databaseUrl = "sqlite:///$normalizedDatabasePath"

try {
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
        --port 8000
    if ($LASTEXITCODE -ne 0) {
        throw "E2E backend exited with a non-zero status."
    }
}
finally {
    if (Test-Path -LiteralPath $databasePath -PathType Leaf) {
        Remove-Item -LiteralPath $databasePath -Force
    }
}
