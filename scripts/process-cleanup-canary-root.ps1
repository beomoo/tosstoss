param(
    [Parameter(Mandatory = $true)][string] $ManifestPath,
    [Parameter(Mandatory = $true)][string] $PortPath
)

. (Join-Path $PSScriptRoot "common.ps1")

$manifestFullPath = [System.IO.Path]::GetFullPath($ManifestPath)
$portFullPath = [System.IO.Path]::GetFullPath($PortPath)
foreach ($path in @($manifestFullPath, $portFullPath)) {
    Assert-SafeMutableRepositoryFile -Path $path
    if (Test-Path -LiteralPath $path) {
        throw "A cleanup canary publication path already exists."
    }
}
$portPendingPath = [System.String]::Concat(
    $portFullPath,
    ".pending-",
    [System.Guid]::NewGuid().ToString("N")
)
$manifestPendingPath = [System.String]::Concat(
    $manifestFullPath,
    ".pending-",
    [System.Guid]::NewGuid().ToString("N")
)
foreach ($path in @($portPendingPath, $manifestPendingPath)) {
    Assert-SafeMutableRepositoryFile -Path $path
}

$pwshCommand = Get-Command pwsh.exe -ErrorAction Stop
function Start-HiddenCanaryProcess {
    param(
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [hashtable] $Environment = @{}
    )

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $pwshCommand.Source
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    foreach ($argument in $Arguments) {
        $startInfo.ArgumentList.Add($argument)
    }
    foreach ($entry in $Environment.GetEnumerator()) {
        $startInfo.Environment[[string] $entry.Key] = [string] $entry.Value
    }
    return [System.Diagnostics.Process]::Start($startInfo)
}

$listenerCommand = @'
$listener = [System.Net.Sockets.TcpListener]::new(
    [System.Net.IPAddress]::Loopback,
    0
)
$listener.Start()
try {
    $port = ([System.Net.IPEndPoint] $listener.LocalEndpoint).Port
    [System.IO.File]::WriteAllText(
        $env:PHASE1_CANARY_PORT_PENDING_PATH,
        [string] $port,
        [System.Text.UTF8Encoding]::new($false)
    )
    [System.IO.File]::Move(
        $env:PHASE1_CANARY_PORT_PENDING_PATH,
        $env:PHASE1_CANARY_PORT_PATH,
        $false
    )
    Start-Sleep -Seconds 120
}
finally {
    $listener.Stop()
}
'@
$listenerEncodedCommand = [System.Convert]::ToBase64String(
    [System.Text.Encoding]::Unicode.GetBytes($listenerCommand)
)
$listenerProcess = Start-HiddenCanaryProcess `
    -Arguments @("-NoProfile", "-EncodedCommand", $listenerEncodedCommand) `
    -Environment @{
        PHASE1_CANARY_PORT_PATH = $portFullPath
        PHASE1_CANARY_PORT_PENDING_PATH = $portPendingPath
    }
$sleeperProcess = Start-HiddenCanaryProcess `
    -Arguments @("-NoProfile", "-Command", "Start-Sleep -Seconds 120")

$deadline = [System.DateTime]::UtcNow.AddSeconds(10)
while (-not (Test-Path -LiteralPath $portFullPath -PathType Leaf)) {
    if ($listenerProcess.HasExited) {
        throw "The listener canary exited before publishing its port."
    }
    if ([System.DateTime]::UtcNow -ge $deadline) {
        throw "The listener canary did not publish its port."
    }
    Start-Sleep -Milliseconds 25
}
$portText = [System.IO.File]::ReadAllText(
    $portFullPath,
    [System.Text.UTF8Encoding]::new($false, $true)
)
$listenerPort = 0
if (
    -not [int]::TryParse($portText, [ref] $listenerPort) -or
    $listenerPort -lt 1 -or
    $listenerPort -gt 65535
) {
    throw "The listener canary published an invalid port."
}

$manifest = [ordered]@{
    schema_version = 1
    listener = [ordered]@{
        process_id = $listenerProcess.Id
        start_time_utc_ticks = $listenerProcess.StartTime.ToUniversalTime().Ticks
        port = $listenerPort
    }
    sleeper = [ordered]@{
        process_id = $sleeperProcess.Id
        start_time_utc_ticks = $sleeperProcess.StartTime.ToUniversalTime().Ticks
    }
}
[System.IO.File]::WriteAllText(
    $manifestPendingPath,
    ($manifest | ConvertTo-Json -Compress -Depth 4),
    [System.Text.UTF8Encoding]::new($false)
)
[System.IO.File]::Move($manifestPendingPath, $manifestFullPath, $false)

# Intentionally leave both descendants running and exit first. The caller must
# prove that the shared owned-process group removes them without touching others.
