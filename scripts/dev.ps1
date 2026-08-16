. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-RepoRoot
$python = Get-VenvPython
$nodePath = (Get-Command node).Source
$nextScript = Join-Path $repoRoot "node_modules\next\dist\bin\next"
if (-not (Test-Path -LiteralPath $nextScript -PathType Leaf)) {
    throw "Next.js is not installed. Run scripts/setup.ps1 first."
}

Invoke-PhaseScript -Name "migrate.ps1" -ArgumentList @("-Action", "Upgrade")
Invoke-PhaseScript -Name "import-fixtures.ps1"

$logDirectory = Join-Path $repoRoot "var\logs"
[System.IO.Directory]::CreateDirectory($logDirectory) | Out-Null
$apiOut = Join-Path $logDirectory "api.out.log"
$apiErr = Join-Path $logDirectory "api.err.log"
$webOut = Join-Path $logDirectory "web.out.log"
$webErr = Join-Path $logDirectory "web.err.log"

$databasePath = (Join-Path $repoRoot "var\dashboard.db").Replace("\", "/")
$env:DASHBOARD_DATABASE_URL = "sqlite:///$databasePath"
$env:DASHBOARD_FIXTURE_DIR = Join-Path $repoRoot "fixtures\phase_01"
$env:DASHBOARD_API_BASE_URL = "http://127.0.0.1:8000"
$env:NEXT_TELEMETRY_DISABLED = "1"

$apiProcess = Start-Process -FilePath $python `
    -ArgumentList @("-m", "uvicorn", "toss_dashboard_api.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr

$webProcess = Start-Process -FilePath $nodePath `
    -ArgumentList @($nextScript, "dev", (Join-Path $repoRoot "apps\web"), "--hostname", "127.0.0.1", "--port", "3000") `
    -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $webOut -RedirectStandardError $webErr

try {
    Start-Sleep -Seconds 2
    if ($apiProcess.HasExited) {
        throw "API process exited early. See $apiErr"
    }
    if ($webProcess.HasExited) {
        throw "Web process exited early. See $webErr"
    }

    Write-Host "Web: http://127.0.0.1:3000"
    Write-Host "API: http://127.0.0.1:8000/health"
    Write-Host "Logs: $logDirectory"
    Write-Host "Press Ctrl+C to stop both processes."

    while (-not $apiProcess.HasExited -and -not $webProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
    throw "A development process exited unexpectedly. See logs in $logDirectory"
}
finally {
    foreach ($process in @($apiProcess, $webProcess)) {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
