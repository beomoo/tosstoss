. (Join-Path $PSScriptRoot "common.ps1")
. (Join-Path $PSScriptRoot "process-ownership.ps1")

Assert-PhaseNodeRuntime
$repoRoot = Get-RepoRoot
$offlineGuardPath = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "scripts\node_offline_guard.cjs")
)
$nodePreflightPath = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "scripts\node_runtime_preflight.cjs")
)
foreach ($requiredNodeScript in @($offlineGuardPath, $nodePreflightPath)) {
    if (-not (Test-Path -LiteralPath $requiredNodeScript -PathType Leaf)) {
        throw "A required offline Node.js guard is missing: $requiredNodeScript"
    }
}
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
$hadNodeOptions = Test-Path -LiteralPath Env:NODE_OPTIONS
$previousNodeOptions = $env:NODE_OPTIONS
$hadPythonBytecodeSetting = Test-Path -LiteralPath Env:PYTHONDONTWRITEBYTECODE
$previousPythonBytecodeSetting = $env:PYTHONDONTWRITEBYTECODE
$env:NODE_OPTIONS = [System.String]::Concat(
    '--require="',
    $offlineGuardPath.Replace("\", "/"),
    '"'
)
$env:NPM_CONFIG_OFFLINE = "true"
$env:NEXT_IGNORE_INCORRECT_LOCKFILE = "1"
$env:NEXT_DISABLE_SWC_WASM = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
$primaryFailure = $null
$ownedProcessGroup = $null

try {
    Assert-NpmDependencyTreeClean
    Invoke-Checked -FilePath "node" -ArgumentList @($nodePreflightPath)
    $npmCommand = Get-Command npm.cmd -ErrorAction Stop
    $e2eOut = Join-Path $tempDirectory "playwright.out.log"
    $e2eErr = Join-Path $tempDirectory "playwright.err.log"
    $ownedProcessGroup = New-OwnedProcessGroup
    $e2eProcess = Start-OwnedProcess `
        -Group $ownedProcessGroup `
        -Name "playwright" `
        -FilePath $npmCommand.Source `
        -ArgumentList @("run", "test:e2e", "--workspace", "apps/web") `
        -WorkingDirectory $repoRoot `
        -TaskTempDirectory $tempDirectory `
        -StandardOutputPath $e2eOut `
        -StandardErrorPath $e2eErr
    $e2eProcess.WaitForExit()
    foreach ($logPath in @($e2eOut, $e2eErr)) {
        if (Test-Path -LiteralPath $logPath -PathType Leaf) {
            Get-Content -LiteralPath $logPath | ForEach-Object { Write-Host $_ }
        }
    }
    if ($e2eProcess.ExitCode -ne 0) {
        throw "The owned Playwright process failed with exit code $($e2eProcess.ExitCode)."
    }
}
catch {
    $primaryFailure = $_
    throw
}
finally {
    $cleanupErrors = [System.Collections.Generic.List[string]]::new()
    if ($null -ne $ownedProcessGroup) {
        try {
            Stop-OwnedProcessGroup -Group $ownedProcessGroup
        }
        catch {
            $cleanupErrors.Add($_.Exception.Message)
        }
    }
    if ($hadPreviousDatabaseEnvironment) {
        $env:PHASE1_E2E_DATABASE_PATH = $previousDatabasePath
    }
    else {
        Remove-Item Env:PHASE1_E2E_DATABASE_PATH -ErrorAction SilentlyContinue
    }
    if ($hadNodeOptions) {
        $env:NODE_OPTIONS = $previousNodeOptions
    }
    else {
        Remove-Item Env:NODE_OPTIONS -ErrorAction SilentlyContinue
    }
    if ($hadPythonBytecodeSetting) {
        $env:PYTHONDONTWRITEBYTECODE = $previousPythonBytecodeSetting
    }
    else {
        Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
    }
    try {
        Remove-TaskTempDirectory -Path $tempDirectory
    }
    catch {
        $cleanupErrors.Add($_.Exception.Message)
    }
    if ($cleanupErrors.Count -gt 0) {
        $cleanupMessage = $cleanupErrors -join [Environment]::NewLine
        if ($null -ne $primaryFailure) {
            Write-Warning "E2E cleanup also failed: $cleanupMessage"
        }
        else {
            throw $cleanupMessage
        }
    }
}
