param(
    [ValidateRange(1, 50)][int] $Iterations = 20
)

. (Join-Path $PSScriptRoot "common.ps1")
. (Join-Path $PSScriptRoot "process-ownership.ps1")

if (-not $IsWindows) {
    throw "The Phase 1 process cleanup canary requires Windows."
}

function Wait-ForCanaryManifest {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][System.Diagnostics.Process] $RootProcess
    )

    $deadline = [System.DateTime]::UtcNow.AddSeconds(10)
    while (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        if ($RootProcess.HasExited) {
            throw "The cleanup canary root exited before publishing its manifest."
        }
        if ([System.DateTime]::UtcNow -ge $deadline) {
            throw "The cleanup canary root did not publish its manifest."
        }
        Start-Sleep -Milliseconds 25
    }
}

function Wait-ForExactProcessIdentityGone {
    param(
        [Parameter(Mandatory = $true)][int] $ProcessId,
        [Parameter(Mandatory = $true)][long] $StartTimeUtcTicks
    )

    $deadline = [System.DateTime]::UtcNow.AddSeconds(10)
    while (Test-ExactProcessIdentityAlive `
            -ProcessId $ProcessId `
            -StartTimeUtcTicks $StartTimeUtcTicks) {
        if ([System.DateTime]::UtcNow -ge $deadline) {
            throw "An exact owned descendant identity survived cleanup."
        }
        Start-Sleep -Milliseconds 25
    }
}

function Test-LoopbackConnection {
    param([Parameter(Mandatory = $true)][int] $Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connectTask = $client.ConnectAsync("127.0.0.1", $Port)
        if (-not $connectTask.Wait(1000)) {
            return $false
        }
        return $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Wait-ForLoopbackConnectionRejected {
    param([Parameter(Mandatory = $true)][int] $Port)

    $deadline = [System.DateTime]::UtcNow.AddSeconds(10)
    while (Test-LoopbackConnection -Port $Port) {
        if ([System.DateTime]::UtcNow -ge $deadline) {
            throw "The owned cleanup canary listener remained reachable."
        }
        Start-Sleep -Milliseconds 25
    }
}

function Invoke-KillOnJobCloseCanary {
    param(
        [Parameter(Mandatory = $true)][string] $TaskTempDirectory,
        [Parameter(Mandatory = $true)][string] $PwshPath
    )

    $controllerScript = [System.IO.Path]::GetFullPath(
        (Join-Path $PSScriptRoot "process-job-close-canary-controller.ps1")
    )
    if (-not (Test-Path -LiteralPath $controllerScript -PathType Leaf)) {
        throw "The job-close canary controller is missing."
    }
    $readyPath = Join-Path $TaskTempDirectory "job-close-ready.json"
    $descendantPath = Join-Path $TaskTempDirectory "job-close-descendants.json"
    $portPath = Join-Path $TaskTempDirectory "job-close-port.txt"
    $suspendedProbeMarkerPath = Join-Path `
        $TaskTempDirectory `
        "job-close-suspended-probe-ran.txt"
    $safetyGroup = $null
    $controllerWrapper = $null
    $wrapperId = 0
    $wrapperTicks = 0
    $controllerId = 0
    $controllerTicks = 0
    $suspendedProbeId = 0
    $suspendedProbeTicks = 0
    $listenerId = 0
    $listenerTicks = 0
    $listenerPort = 0
    $sleeperId = 0
    $sleeperTicks = 0
    $primaryFailure = $null
    try {
        $safetyGroup = New-OwnedProcessGroup
        $controllerWrapper = Start-OwnedProcess `
            -Group $safetyGroup `
            -Name "job-close-controller" `
            -FilePath $PwshPath `
            -ArgumentList @(
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", $controllerScript,
                "-ReadyManifestPath", $readyPath,
                "-DescendantManifestPath", $descendantPath,
                "-PortPath", $portPath,
                "-SuspendedProbeMarkerPath", $suspendedProbeMarkerPath,
                "-TaskTempDirectory", $TaskTempDirectory
            ) `
            -WorkingDirectory (Get-RepoRoot) `
            -TaskTempDirectory $TaskTempDirectory `
            -StandardOutputPath (Join-Path $TaskTempDirectory "job-close-controller.out.log") `
            -StandardErrorPath (Join-Path $TaskTempDirectory "job-close-controller.err.log")
        $wrapperId = $controllerWrapper.Id
        $wrapperTicks = $controllerWrapper.StartTime.ToUniversalTime().Ticks
        Wait-ForCanaryManifest -Path $readyPath -RootProcess $controllerWrapper
        $readyJson = [System.IO.File]::ReadAllText(
            $readyPath,
            [System.Text.UTF8Encoding]::new($false, $true)
        )
        try {
            $readyManifest = $readyJson | ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            throw "The job-close canary manifest is not valid JSON."
        }
        if ($readyManifest.schema_version -ne 2) {
            throw "The job-close canary manifest has an invalid schema."
        }
        $controllerId = [int] $readyManifest.controller.process_id
        $controllerTicks = [long] $readyManifest.controller.start_time_utc_ticks
        $suspendedProbeId = [int] $readyManifest.atomic_suspended_probe.process_id
        $suspendedProbeTicks = [long] (
            $readyManifest.atomic_suspended_probe.start_time_utc_ticks
        )
        $listenerId = [int] $readyManifest.listener.process_id
        $listenerTicks = [long] $readyManifest.listener.start_time_utc_ticks
        $listenerPort = [int] $readyManifest.listener.port
        $sleeperId = [int] $readyManifest.sleeper.process_id
        $sleeperTicks = [long] $readyManifest.sleeper.start_time_utc_ticks
        if (
            -not (Test-ExactProcessIdentityAlive $controllerId $controllerTicks) -or
            -not (Test-ExactProcessIdentityAlive `
                $suspendedProbeId `
                $suspendedProbeTicks) -or
            -not (Test-ExactProcessIdentityAlive $listenerId $listenerTicks) -or
            -not (Test-ExactProcessIdentityAlive $sleeperId $sleeperTicks) -or
            -not (Test-LoopbackConnection -Port $listenerPort) -or
            (Test-Path -LiteralPath $suspendedProbeMarkerPath)
        ) {
            throw "The job-close canary was not fully alive before owner termination."
        }

        Stop-ExactProcessIdentity $controllerId $controllerTicks
        Wait-ForExactProcessIdentityGone $controllerId $controllerTicks
        Wait-ForExactProcessIdentityGone $suspendedProbeId $suspendedProbeTicks
        Wait-ForExactProcessIdentityGone $listenerId $listenerTicks
        Wait-ForExactProcessIdentityGone $sleeperId $sleeperTicks
        Wait-ForLoopbackConnectionRejected -Port $listenerPort
        if (Test-Path -LiteralPath $suspendedProbeMarkerPath) {
            throw "The atomic owner-crash probe executed instead of remaining suspended."
        }
        if (-not $controllerWrapper.WaitForExit(10000)) {
            throw "The job-close controller wrapper did not exit."
        }
    }
    catch {
        $primaryFailure = $_
        throw
    }
    finally {
        $cleanupErrors = [System.Collections.Generic.List[string]]::new()
        if ($null -ne $safetyGroup -and -not $safetyGroup.IsStopped) {
            try {
                Stop-OwnedProcessGroup -Group $safetyGroup
            }
            catch {
                $cleanupErrors.Add($_.Exception.Message)
            }
        }
        foreach ($identity in @(
            [pscustomobject]@{ProcessId = $controllerId; StartTicks = $controllerTicks},
            [pscustomobject]@{
                ProcessId = $suspendedProbeId
                StartTicks = $suspendedProbeTicks
            },
            [pscustomobject]@{ProcessId = $listenerId; StartTicks = $listenerTicks},
            [pscustomobject]@{ProcessId = $sleeperId; StartTicks = $sleeperTicks},
            [pscustomobject]@{ProcessId = $wrapperId; StartTicks = $wrapperTicks}
        )) {
            if ($identity.ProcessId -gt 0 -and $identity.StartTicks -gt 0) {
                try {
                    Stop-ExactProcessIdentity `
                        -ProcessId $identity.ProcessId `
                        -StartTimeUtcTicks $identity.StartTicks `
                        -IncludeDescendants
                }
                catch {
                    $cleanupErrors.Add($_.Exception.Message)
                }
            }
        }
        if ($cleanupErrors.Count -gt 0) {
            $cleanupMessage = $cleanupErrors -join [Environment]::NewLine
            if ($null -ne $primaryFailure) {
                Write-Warning "Job-close canary cleanup also failed: $cleanupMessage"
            }
            else {
                throw $cleanupMessage
            }
        }
    }
}

$taskTempDirectory = New-TaskTempDirectory
$controlGroup = $null
$controlProcess = $null
$controlProcessId = 0
$controlStartTimeUtcTicks = 0
$primaryFailure = $null
try {
    $pwshCommand = Get-Command pwsh.exe -ErrorAction Stop
    $controlGroup = New-OwnedProcessGroup
    $controlProcess = Start-OwnedProcess `
        -Group $controlGroup `
        -Name "unrelated-control" `
        -FilePath $pwshCommand.Source `
        -ArgumentList @("-NoProfile", "-Command", "Start-Sleep -Seconds 300") `
        -WorkingDirectory (Get-RepoRoot) `
        -TaskTempDirectory $taskTempDirectory `
        -StandardOutputPath (Join-Path $taskTempDirectory "control.out.log") `
        -StandardErrorPath (Join-Path $taskTempDirectory "control.err.log")
    $controlProcessId = $controlProcess.Id
    $controlStartTimeUtcTicks = $controlProcess.StartTime.ToUniversalTime().Ticks
    $rootScript = [System.IO.Path]::GetFullPath(
        (Join-Path $PSScriptRoot "process-cleanup-canary-root.ps1")
    )
    if (-not (Test-Path -LiteralPath $rootScript -PathType Leaf)) {
        throw "The cleanup canary root script is missing."
    }
    Invoke-KillOnJobCloseCanary `
        -TaskTempDirectory $taskTempDirectory `
        -PwshPath $pwshCommand.Source

    for ($iteration = 1; $iteration -le $Iterations; $iteration += 1) {
        $group = $null
        $listenerId = 0
        $listenerTicks = 0
        $sleeperId = 0
        $sleeperTicks = 0
        $iterationFailure = $null
        try {
            $manifestPath = Join-Path $taskTempDirectory "manifest-$iteration.json"
            $portPath = Join-Path $taskTempDirectory "port-$iteration.txt"
            $stdoutPath = Join-Path $taskTempDirectory "root-$iteration.out.log"
            $stderrPath = Join-Path $taskTempDirectory "root-$iteration.err.log"
            foreach ($path in @($manifestPath, $portPath, $stdoutPath, $stderrPath)) {
                Assert-SafeMutableRepositoryFile -Path $path
            }
            $group = New-OwnedProcessGroup
            $rootProcess = Start-OwnedProcess `
                -Group $group `
                -Name "cleanup-canary" `
                -FilePath $pwshCommand.Source `
                -ArgumentList @(
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-File", $rootScript,
                    "-ManifestPath", $manifestPath,
                    "-PortPath", $portPath
                ) `
                -WorkingDirectory (Get-RepoRoot) `
                -TaskTempDirectory $taskTempDirectory `
                -StandardOutputPath $stdoutPath `
                -StandardErrorPath $stderrPath
            Wait-ForCanaryManifest -Path $manifestPath -RootProcess $rootProcess
            if (-not $rootProcess.WaitForExit(10000)) {
                throw "The cleanup canary root did not exit before cleanup."
            }
            if (-not $rootProcess.HasExited) {
                throw "The cleanup canary root must exit before cleanup."
            }

            $manifestJson = [System.IO.File]::ReadAllText(
                $manifestPath,
                [System.Text.UTF8Encoding]::new($false, $true)
            )
            try {
                $manifest = $manifestJson | ConvertFrom-Json -ErrorAction Stop
            }
            catch {
                throw "The cleanup canary manifest is not valid JSON."
            }
            if ($manifest.schema_version -ne 1) {
                throw "The cleanup canary manifest has an invalid schema."
            }
            $listenerId = [int] $manifest.listener.process_id
            $listenerTicks = [long] $manifest.listener.start_time_utc_ticks
            $listenerPort = [int] $manifest.listener.port
            $sleeperId = [int] $manifest.sleeper.process_id
            $sleeperTicks = [long] $manifest.sleeper.start_time_utc_ticks
            if (
                -not (Test-ExactProcessIdentityAlive $listenerId $listenerTicks) -or
                -not (Test-ExactProcessIdentityAlive $sleeperId $sleeperTicks) -or
                -not (Test-LoopbackConnection -Port $listenerPort)
            ) {
                throw "An owned cleanup canary descendant was not alive before cleanup."
            }

            Stop-OwnedProcessGroup -Group $group
            Stop-OwnedProcessGroup -Group $group
            Wait-ForExactProcessIdentityGone $listenerId $listenerTicks
            Wait-ForExactProcessIdentityGone $sleeperId $sleeperTicks
            Wait-ForLoopbackConnectionRejected -Port $listenerPort
            if (-not (Test-ExactProcessIdentityAlive `
                    -ProcessId $controlProcessId `
                    -StartTimeUtcTicks $controlStartTimeUtcTicks)) {
                throw "Owned cleanup terminated an unrelated control process."
            }
        }
        catch {
            $iterationFailure = $_
            throw
        }
        finally {
            $iterationCleanupErrors = [System.Collections.Generic.List[string]]::new()
            if ($null -ne $group -and -not $group.IsStopped) {
                try {
                    Stop-OwnedProcessGroup -Group $group
                }
                catch {
                    $iterationCleanupErrors.Add($_.Exception.Message)
                }
            }
            foreach ($identity in @(
                [pscustomobject]@{ProcessId = $listenerId; StartTicks = $listenerTicks},
                [pscustomobject]@{ProcessId = $sleeperId; StartTicks = $sleeperTicks}
            )) {
                if ($identity.ProcessId -gt 0 -and $identity.StartTicks -gt 0) {
                    try {
                        Stop-ExactProcessIdentity `
                            -ProcessId $identity.ProcessId `
                            -StartTimeUtcTicks $identity.StartTicks `
                            -IncludeDescendants
                    }
                    catch {
                        $iterationCleanupErrors.Add($_.Exception.Message)
                    }
                }
            }
            if ($iterationCleanupErrors.Count -gt 0) {
                $cleanupMessage = $iterationCleanupErrors -join [Environment]::NewLine
                if ($null -ne $iterationFailure) {
                    Write-Warning "Iteration cleanup also failed: $cleanupMessage"
                }
                else {
                    throw $cleanupMessage
                }
            }
        }
    }

    Write-Host (
        "Owned process cleanup canary passed: iterations=$Iterations, " +
        "root-exited-before-cleanup=true, owned-descendants-removed=2, " +
        "unrelated-survived=true, owner-crash-kill-on-close=true, " +
        "atomic-pre-resume-probe-removed=true"
    )
}
catch {
    $primaryFailure = $_
    throw
}
finally {
    $cleanupErrors = [System.Collections.Generic.List[string]]::new()
    if ($null -ne $controlGroup -and -not $controlGroup.IsStopped) {
        try {
            Stop-OwnedProcessGroup -Group $controlGroup
        }
        catch {
            $cleanupErrors.Add($_.Exception.Message)
        }
    }
    if ($controlProcessId -gt 0 -and $controlStartTimeUtcTicks -gt 0) {
        try {
            Stop-ExactProcessIdentity `
                -ProcessId $controlProcessId `
                -StartTimeUtcTicks $controlStartTimeUtcTicks `
                -IncludeDescendants
        }
        catch {
            $cleanupErrors.Add($_.Exception.Message)
        }
    }
    try {
        Remove-TaskTempDirectory -Path $taskTempDirectory
    }
    catch {
        $cleanupErrors.Add($_.Exception.Message)
    }
    if ($cleanupErrors.Count -gt 0) {
        $cleanupMessage = $cleanupErrors -join [Environment]::NewLine
        if ($null -ne $primaryFailure) {
            Write-Warning "Process canary cleanup also failed: $cleanupMessage"
        }
        else {
            throw $cleanupMessage
        }
    }
}
