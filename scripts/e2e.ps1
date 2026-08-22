. (Join-Path $PSScriptRoot "common.ps1")

$env:NEXT_TELEMETRY_DISABLED = "1"
Invoke-PhaseScript -Name "build.ps1"
$previousDatabaseEnvironment = Get-Item `
    -LiteralPath Env:PHASE1_E2E_DATABASE_PATH `
    -ErrorAction SilentlyContinue
$hadPreviousDatabaseEnvironment = $null -ne $previousDatabaseEnvironment
$previousDatabasePath = if ($hadPreviousDatabaseEnvironment) {
    $previousDatabaseEnvironment.Value
}
else {
    $null
}

$tempDirectory = New-TaskTempDirectory
$databasePath = [System.IO.Path]::GetFullPath(
    (Join-Path $tempDirectory "playwright-e2e.db")
)
$env:PHASE1_E2E_DATABASE_PATH = $databasePath

try {
    Invoke-Checked `
        -FilePath "npm" `
        -ArgumentList @("run", "test:e2e", "--workspace", "apps/web")
}
finally {
    if ($hadPreviousDatabaseEnvironment) {
        $env:PHASE1_E2E_DATABASE_PATH = $previousDatabasePath
    }
    else {
        Remove-Item Env:PHASE1_E2E_DATABASE_PATH -ErrorAction SilentlyContinue
    }
    Remove-TaskTempDirectory -Path $tempDirectory
}
