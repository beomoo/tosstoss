param(
    [switch] $Smoke
)

. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-RepoRoot
$python = Get-VenvPython
$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($null -eq $npmCommand) {
    throw "npm.cmd is not installed or not available on PATH."
}
$npmPath = $npmCommand.Source
$webRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "apps\web"))
$uvicornLogConfig = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "services\api\uvicorn_log_config.json")
)
if (-not (Test-Path -LiteralPath $uvicornLogConfig -PathType Leaf)) {
    throw "The Uvicorn JSON log configuration is missing."
}
$uvicornLogConfigArgument = '"' + $uvicornLogConfig + '"'

function Wait-ForLocalEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Uri,
        [Parameter(Mandatory = $true)]
        [string] $Name,
        [Parameter(Mandatory = $true)]
        [object[]] $OwnedProcesses,
        [int] $TimeoutSeconds = 60
    )

    $requestedUri = [System.Uri] $Uri
    if (
        -not $requestedUri.IsAbsoluteUri -or
        $requestedUri.Scheme -cne "http" -or
        $requestedUri.Host -cne "127.0.0.1" -or
        -not [string]::IsNullOrEmpty($requestedUri.UserInfo) -or
        -not [string]::IsNullOrEmpty($requestedUri.Fragment)
    ) {
        throw "$Name readiness URI must be an absolute http://127.0.0.1 loopback URL."
    }

    $deadline = [System.DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([System.DateTime]::UtcNow -lt $deadline) {
        foreach ($ownedProcess in $OwnedProcesses) {
            if ($null -ne $ownedProcess) {
                $ownedProcess.Refresh()
                if ($ownedProcess.HasExited) {
                    throw "$Name did not become ready because an owned process exited early."
                }
            }
        }
        try {
            $response = Invoke-WebRequest `
                -Uri $requestedUri `
                -TimeoutSec 2 `
                -MaximumRedirection 0 `
                -SkipHttpErrorCheck
        }
        catch {
            # Local services may refuse connections until their startup completes.
            Start-Sleep -Milliseconds 250
            continue
        }

        $statusCode = [int] $response.StatusCode
        if ($statusCode -ge 300 -and $statusCode -lt 400) {
            throw "$Name readiness endpoint returned a redirect, which is not allowed."
        }
        if ($statusCode -eq 200) {
            $finalUri = $response.BaseResponse.RequestMessage.RequestUri
            if ($null -eq $finalUri) {
                throw "$Name readiness response did not expose its final request URI."
            }
            $sameOrigin =
                $finalUri.Scheme -ceq $requestedUri.Scheme -and
                $finalUri.Host -ceq $requestedUri.Host -and
                $finalUri.Port -eq $requestedUri.Port
            $samePathAndQuery =
                $finalUri.AbsolutePath -ceq $requestedUri.AbsolutePath -and
                $finalUri.Query -ceq $requestedUri.Query
            if (-not $sameOrigin -or -not $samePathAndQuery) {
                throw "$Name readiness response final URI did not match the requested loopback origin and path."
            }
            return $response
        }
        Start-Sleep -Milliseconds 250
    }
    throw "$Name did not become ready within $TimeoutSeconds seconds."
}

function Stop-OwnedProcessTree {
    param(
        [System.Diagnostics.Process] $Process
    )

    if ($null -eq $Process) {
        return
    }
    $Process.Refresh()
    if ($Process.HasExited) {
        return
    }

    $taskkill = Join-Path $env:SystemRoot "System32\taskkill.exe"
    & $taskkill /PID $Process.Id /T /F *> $null
    if ($LASTEXITCODE -ne 0) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
}

function Assert-JsonLogLines {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Paths
    )

    $lineCount = 0
    foreach ($path in $Paths) {
        $lines = @(Get-Content -LiteralPath $path |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        foreach ($line in $lines) {
            try {
                $parsedLine = $line | ConvertFrom-Json -ErrorAction Stop
            }
            catch {
                throw "API development log contains a non-JSON line: $path"
            }
            if ($null -eq $parsedLine -or $parsedLine -isnot [pscustomobject]) {
                throw "API development log lines must be JSON objects: $path"
            }
            $lineCount += 1
        }
    }
    if ($lineCount -eq 0) {
        throw "API development logs are empty after readiness checks."
    }
    return $lineCount
}

$fixtureDirectory = Join-Path $repoRoot "fixtures\phase_01"
$fixtureManifestPath = Join-Path $fixtureDirectory "manifest.json"
if (-not (Test-Path -LiteralPath $fixtureManifestPath -PathType Leaf)) {
    throw "The Phase 1 fixture manifest is missing."
}
$previousSentinelEnvironment = Get-Item `
    -LiteralPath Env:PHASE1_SERVER_ONLY_SENTINEL `
    -ErrorAction SilentlyContinue
$hadPreviousSentinel = $null -ne $previousSentinelEnvironment
$previousSentinel = if ($hadPreviousSentinel) {
    $previousSentinelEnvironment.Value
}
else {
    $null
}

$smokeTempDirectory = $null
$sentinelWasConfigured = $false
$apiProcess = $null
$webProcess = $null
try {
    if ($Smoke) {
        $smokeTempDirectory = New-TaskTempDirectory
        $databasePath = Join-Path $smokeTempDirectory "dashboard.db"
    }
    else {
        $runtimeDirectory = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var"))
        Assert-SafeRepositoryPath -Path $runtimeDirectory
        [System.IO.Directory]::CreateDirectory($runtimeDirectory) | Out-Null
        Assert-SafeRepositoryPath -Path $runtimeDirectory
        $fixtureManifestHash = (Get-FileHash `
                -LiteralPath $fixtureManifestPath `
                -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($fixtureManifestHash -cnotmatch '^[0-9a-f]{64}$') {
            throw "The Phase 1 fixture manifest SHA-256 was not canonical."
        }
        $databaseName = "dashboard-fixture-$($fixtureManifestHash.Substring(0, 12)).db"
        $databasePath = Join-Path $runtimeDirectory $databaseName
    }

    Invoke-PhaseScript `
        -Name "migrate.ps1" `
        -ArgumentList @("-Action", "Upgrade", "-DatabasePath", $databasePath)
    Invoke-PhaseScript `
        -Name "import-fixtures.ps1" `
        -ArgumentList @("-DatabasePath", $databasePath)

    $logDirectory = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var\logs"))
    Assert-SafeRepositoryPath -Path $logDirectory
    [System.IO.Directory]::CreateDirectory($logDirectory) | Out-Null
    Assert-SafeRepositoryPath -Path $logDirectory
    $apiOut = Join-Path $logDirectory "api.out.log"
    $apiErr = Join-Path $logDirectory "api.err.log"
    $webOut = Join-Path $logDirectory "web.out.log"
    $webErr = Join-Path $logDirectory "web.err.log"
    foreach ($logPath in @($apiOut, $apiErr, $webOut, $webErr)) {
        Assert-SafeRepositoryPath -Path $logPath
        [System.IO.File]::WriteAllText($logPath, "")
    }

    $env:DASHBOARD_DATABASE_URL = Convert-ToSqliteUrl -Path $databasePath
    $env:DASHBOARD_FIXTURE_DIR = $fixtureDirectory
    $env:DASHBOARD_API_BASE_URL = "http://127.0.0.1:8000"
    $env:NEXT_TELEMETRY_DISABLED = "1"

    $sentinelBytes = [byte[]]::new(16)
    $randomNumberGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $randomNumberGenerator.GetBytes($sentinelBytes)
    }
    finally {
        $randomNumberGenerator.Dispose()
    }
    $sentinelHex = [System.BitConverter]::ToString($sentinelBytes).Replace("-", "").ToLowerInvariant()
    $runtimeSentinel = "PHASE1_RUNTIME_$sentinelHex"
    if ($runtimeSentinel -cnotmatch '^PHASE1_RUNTIME_[0-9a-f]{32}$') {
        throw "Generated Phase 1 runtime sentinel did not satisfy the required format."
    }
    $env:PHASE1_SERVER_ONLY_SENTINEL = $runtimeSentinel
    $sentinelWasConfigured = $true

    $apiProcess = Start-Process -FilePath $python `
        -ArgumentList @(
            "-m", "uvicorn", "toss_dashboard_api.main:app",
            "--host", "127.0.0.1", "--port", "8000",
            "--no-access-log", "--log-config", $uvicornLogConfigArgument
        ) `
        -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr

    $webProcess = Start-Process -FilePath $npmPath `
        -ArgumentList @("run", "dev") `
        -WorkingDirectory $webRoot -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $webOut -RedirectStandardError $webErr

    $ownedProcesses = @($apiProcess, $webProcess)
    $healthResponse = Wait-ForLocalEndpoint `
        -Uri "http://127.0.0.1:8000/health" `
        -Name "API" `
        -OwnedProcesses $ownedProcesses
    $health = $healthResponse.Content | ConvertFrom-Json
    if ($health.status -ne "ok" -or $health.data_mode -ne "FIXTURE") {
        throw "API readiness response did not satisfy the fixture contract."
    }
    $webResponse = Wait-ForLocalEndpoint `
        -Uri "http://127.0.0.1:3000" `
        -Name "Web" `
        -OwnedProcesses $ownedProcesses
    if ($webResponse.Content -notmatch 'data-testid="fixture-banner"') {
        throw "Web readiness response did not contain the persistent fixture banner."
    }

    Write-Host "Web: http://127.0.0.1:3000"
    Write-Host "API: http://127.0.0.1:8000/health"
    Write-Host "Logs: $logDirectory"
    if ($Smoke) {
        $apiJsonLineCount = Assert-JsonLogLines -Paths @($apiOut, $apiErr)
        Write-Host "API JSON log lines verified: $apiJsonLineCount"
        Write-Host "Development smoke passed; stopping owned process trees."
        return
    }
    Write-Host "Press Ctrl+C to stop both processes."

    while (-not $apiProcess.HasExited -and -not $webProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
    throw "A development process exited unexpectedly. See logs in $logDirectory"
}
finally {
    foreach ($process in @($webProcess, $apiProcess)) {
        Stop-OwnedProcessTree -Process $process
    }
    Remove-Item Env:DASHBOARD_DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:DASHBOARD_FIXTURE_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:DASHBOARD_API_BASE_URL -ErrorAction SilentlyContinue
    if ($sentinelWasConfigured) {
        if ($hadPreviousSentinel) {
            $env:PHASE1_SERVER_ONLY_SENTINEL = $previousSentinel
        }
        else {
            Remove-Item Env:PHASE1_SERVER_ONLY_SENTINEL -ErrorAction SilentlyContinue
        }
    }
    if ($null -ne $smokeTempDirectory) {
        Remove-TaskTempDirectory -Path $smokeTempDirectory
    }
}
