param(
    [Parameter(Mandatory = $true)][string] $ReadyManifestPath,
    [Parameter(Mandatory = $true)][string] $DescendantManifestPath,
    [Parameter(Mandatory = $true)][string] $PortPath,
    [Parameter(Mandatory = $true)][string] $SuspendedProbeMarkerPath,
    [Parameter(Mandatory = $true)][string] $TaskTempDirectory
)

. (Join-Path $PSScriptRoot "common.ps1")
. (Join-Path $PSScriptRoot "process-ownership.ps1")

$readyPath = [System.IO.Path]::GetFullPath($ReadyManifestPath)
$descendantPath = [System.IO.Path]::GetFullPath($DescendantManifestPath)
$portFullPath = [System.IO.Path]::GetFullPath($PortPath)
$suspendedProbeMarkerFullPath = [System.IO.Path]::GetFullPath(
    $SuspendedProbeMarkerPath
)
$taskTempPath = [System.IO.Path]::GetFullPath($TaskTempDirectory)
foreach ($path in @(
    $readyPath,
    $descendantPath,
    $portFullPath,
    $suspendedProbeMarkerFullPath
)) {
    Assert-SafeMutableRepositoryFile -Path $path
    if (Test-Path -LiteralPath $path) {
        throw "A job-close canary publication path already exists."
    }
}
$readyPendingPath = [System.String]::Concat(
    $readyPath,
    ".pending-",
    [System.Guid]::NewGuid().ToString("N")
)
Assert-SafeMutableRepositoryFile -Path $readyPendingPath

function Wait-ForDescendantManifest {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][System.Diagnostics.Process] $RootProcess
    )

    $deadline = [System.DateTime]::UtcNow.AddSeconds(10)
    while (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        if ($RootProcess.HasExited) {
            throw "The job-close descendant root exited before publishing its manifest."
        }
        if ([System.DateTime]::UtcNow -ge $deadline) {
            throw "The job-close descendant manifest was not published."
        }
        Start-Sleep -Milliseconds 25
    }
}

$innerGroup = $null
$suspendedProbe = $null
try {
    $pwshCommand = Get-Command pwsh.exe -ErrorAction Stop
    $rootScript = [System.IO.Path]::GetFullPath(
        (Join-Path $PSScriptRoot "process-cleanup-canary-root.ps1")
    )
    $innerGroup = New-OwnedProcessGroup
    $probeMarkerBase64 = [System.Convert]::ToBase64String(
        [System.Text.Encoding]::UTF8.GetBytes($suspendedProbeMarkerFullPath)
    )
    $suspendedProbeCommand = @'
$markerPath = [System.Text.Encoding]::UTF8.GetString(
    [System.Convert]::FromBase64String("__PROBE_MARKER_BASE64__")
)
[System.IO.File]::WriteAllText(
    $markerPath,
    "the atomically assigned probe was unexpectedly resumed",
    [System.Text.UTF8Encoding]::new($false)
)
Start-Sleep -Seconds 300
'@.Replace("__PROBE_MARKER_BASE64__", $probeMarkerBase64)
    $suspendedProbeEncodedCommand = [System.Convert]::ToBase64String(
        [System.Text.Encoding]::Unicode.GetBytes($suspendedProbeCommand)
    )
    $suspendedProbe = $innerGroup.Job.StartAssignedSuspendedForCanary(
        $pwshCommand.Source,
        [string[]] @(
            "-NoProfile",
            "-EncodedCommand", $suspendedProbeEncodedCommand
        ),
        (Get-RepoRoot)
    )
    try {
        $innerGroup.Processes.Add($suspendedProbe)
    }
    catch {
        $suspendedProbe.Dispose()
        throw
    }

    $rootProcess = Start-OwnedProcess `
        -Group $innerGroup `
        -Name "job-close-root" `
        -FilePath $pwshCommand.Source `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", $rootScript,
            "-ManifestPath", $descendantPath,
            "-PortPath", $portFullPath
        ) `
        -WorkingDirectory (Get-RepoRoot) `
        -TaskTempDirectory $taskTempPath `
        -StandardOutputPath (Join-Path $taskTempPath "job-close-root.out.log") `
        -StandardErrorPath (Join-Path $taskTempPath "job-close-root.err.log")
    Wait-ForDescendantManifest -Path $descendantPath -RootProcess $rootProcess
    if (-not $rootProcess.WaitForExit(10000)) {
        throw "The job-close descendant root did not exit."
    }

    $descendantJson = [System.IO.File]::ReadAllText(
        $descendantPath,
        [System.Text.UTF8Encoding]::new($false, $true)
    )
    try {
        $descendants = $descendantJson | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "The job-close descendant manifest is not valid JSON."
    }
    if ($descendants.schema_version -ne 1) {
        throw "The job-close descendant manifest has an invalid schema."
    }
    if (
        $suspendedProbe.HasExited -or
        (Test-Path -LiteralPath $suspendedProbeMarkerFullPath)
    ) {
        throw "The atomically assigned owner-crash probe did not remain suspended."
    }

    $controllerProcess = [System.Diagnostics.Process]::GetCurrentProcess()
    try {
        $readyManifest = [ordered]@{
            schema_version = 2
            controller = [ordered]@{
                process_id = $controllerProcess.Id
                start_time_utc_ticks = $controllerProcess.StartTime.ToUniversalTime().Ticks
            }
            atomic_suspended_probe = [ordered]@{
                process_id = $suspendedProbe.Id
                start_time_utc_ticks = $suspendedProbe.StartTime.ToUniversalTime().Ticks
            }
            listener = $descendants.listener
            sleeper = $descendants.sleeper
        }
    }
    finally {
        $controllerProcess.Dispose()
    }
    [System.IO.File]::WriteAllText(
        $readyPendingPath,
        ($readyManifest | ConvertTo-Json -Compress -Depth 5),
        [System.Text.UTF8Encoding]::new($false)
    )
    [System.IO.File]::Move($readyPendingPath, $readyPath, $false)

    # The outer canary terminates this exact controller process. Its abrupt exit
    # must close the inner Job handle and kill the never-resumed atomic probe as
    # well as both otherwise-orphan descendants.
    Start-Sleep -Seconds 300
    throw "The job-close canary controller was not terminated by its caller."
}
finally {
    if ($null -ne $innerGroup -and -not $innerGroup.IsStopped) {
        Stop-OwnedProcessGroup -Group $innerGroup
    }
}
