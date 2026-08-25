. (Join-Path $PSScriptRoot "common.ps1")

$powerShellVersion = [System.Version]::Parse($PSVersionTable.PSVersion.ToString())
if ($powerShellVersion -lt [System.Version]"7.4.0") {
    throw "PowerShell 7.4 or newer is required. Found $powerShellVersion."
}

$nodePath = Assert-PhaseNodeRuntime
$npmPath = Get-PhaseNpmCommandPath
$startupNodeOptions = Get-Item -LiteralPath Env:NODE_OPTIONS -ErrorAction SilentlyContinue
$hadStartupNodeOptions = $null -ne $startupNodeOptions
$previousStartupNodeOptions = if ($hadStartupNodeOptions) {
    $startupNodeOptions.Value
}
else {
    $null
}
try {
    $env:NODE_OPTIONS = '--require=C:\phase-01-preload-canary.cjs'
    $nodeOptionsRejected = $false
    try {
        $null = Assert-PhaseNodeRuntime
    }
    catch {
        if ($_.Exception.Message -cne "NODE_OPTIONS must be empty before a Phase 1 script starts.") {
            throw
        }
        $nodeOptionsRejected = $true
    }
    if (-not $nodeOptionsRejected) {
        throw "The inherited NODE_OPTIONS negative canary was not rejected."
    }
}
finally {
    if ($hadStartupNodeOptions) {
        $env:NODE_OPTIONS = $previousStartupNodeOptions
    }
    else {
        Remove-Item Env:NODE_OPTIONS -ErrorAction SilentlyContinue
    }
}
Write-Host "Inherited NODE_OPTIONS fail-closed guard verified."
$python = Get-VenvPython
$repoRoot = Get-RepoRoot
$pytestConfiguration = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "pyproject.toml")
)
$offlineGuardPath = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "scripts\node_offline_guard.cjs")
)
$nodePreflightPath = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "scripts\node_runtime_preflight.cjs")
)
$env:NEXT_TELEMETRY_DISABLED = "1"
$env:NPM_CONFIG_OFFLINE = "true"
$env:NEXT_IGNORE_INCORRECT_LOCKFILE = "1"
$env:NEXT_DISABLE_SWC_WASM = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
$pytestEnvironmentOverrides = @(
    "PYTEST_ADDOPTS",
    "PYTEST_PLUGINS"
)
foreach ($variableName in $pytestEnvironmentOverrides) {
    if (
        (Test-Path -LiteralPath "Env:$variableName") -and
        -not [string]::IsNullOrWhiteSpace(
            [string] [Environment]::GetEnvironmentVariable($variableName)
        )
    ) {
        throw "$variableName is prohibited for the Phase 1 test gate."
    }
    Remove-Item -LiteralPath "Env:$variableName" -ErrorAction SilentlyContinue
}
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$pytestArguments = @(Get-GuardedPythonModuleArguments -Module "pytest" -ArgumentList @(
    "-c", $pytestConfiguration,
    "--override-ini", "addopts=",
    "--override-ini", "pythonpath=services/api/src .",
    "--strict-config", "--strict-markers",
    "-p", "no:cacheprovider",
    "-p", "pytest_socket",
    "--allow-hosts=127.0.0.1,::1,localhost",
    "--confcutdir=tests/backend"
))

function Invoke-CapturedChecked {
    param(
        [Parameter(Mandatory = $true)][string] $FilePath,
        [string[]] $ArgumentList = @(),
        [string] $WorkingDirectory = (Get-RepoRoot)
    )

    Push-Location -LiteralPath $WorkingDirectory
    try {
        $output = @(& $FilePath @ArgumentList 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    if ($exitCode -ne 0) {
        foreach ($line in $output) {
            Write-Host ([string] $line)
        }
        throw "Test inventory command failed with exit code $exitCode."
    }
    return $output
}

function Get-VitestInventoryFromUtf8Capture {
    param(
        [Parameter(Mandatory = $true)][string] $FilePath,
        [Parameter(Mandatory = $true)][string[]] $ArgumentList,
        [string] $WorkingDirectory = (Get-RepoRoot)
    )

    $captureId = [System.Guid]::NewGuid().ToString("N")
    $temporaryRoot = [System.IO.Path]::GetTempPath()
    $stdoutPath = Join-Path $temporaryRoot "tosstoss-vitest-$captureId.stdout.json"
    $stderrPath = Join-Path $temporaryRoot "tosstoss-vitest-$captureId.stderr.txt"
    $strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)

    try {
        Push-Location -LiteralPath $WorkingDirectory
        try {
            & $FilePath @ArgumentList 1> $stdoutPath 2> $stderrPath
            $exitCode = $LASTEXITCODE
        }
        finally {
            Pop-Location
        }

        $stderrBytes = [System.IO.File]::ReadAllBytes($stderrPath)
        if ($exitCode -ne 0) {
            throw "Vitest inventory command failed with exit code $exitCode. stderr bytes: $($stderrBytes.Length)."
        }
        if ($stderrBytes.Length -ne 0) {
            throw "Vitest inventory command emitted unexpected stderr."
        }

        $stdoutBytes = [System.IO.File]::ReadAllBytes($stdoutPath)
        try {
            $jsonText = $strictUtf8.GetString($stdoutBytes)
        }
        catch [System.Text.DecoderFallbackException] {
            throw "Vitest inventory stdout is not valid UTF-8."
        }
        $roundTripBytes = $strictUtf8.GetBytes($jsonText)
        if (-not [System.Linq.Enumerable]::SequenceEqual($stdoutBytes, $roundTripBytes)) {
            throw "Vitest inventory stdout did not round-trip as UTF-8."
        }

        try {
            $document = [System.Text.Json.JsonDocument]::Parse($jsonText)
        }
        catch [System.Text.Json.JsonException] {
            throw "Vitest did not emit a valid JSON test inventory."
        }
        try {
            if ($document.RootElement.ValueKind -ne [System.Text.Json.JsonValueKind]::Array) {
                throw "Vitest JSON test inventory root is not an array."
            }

            $tests = @()
            foreach ($item in $document.RootElement.EnumerateArray()) {
                if ($item.ValueKind -ne [System.Text.Json.JsonValueKind]::Object) {
                    throw "Vitest JSON test inventory contains a non-object item."
                }
                try {
                    $nameProperty = $item.GetProperty("name")
                    $fileProperty = $item.GetProperty("file")
                }
                catch [System.Collections.Generic.KeyNotFoundException] {
                    throw "Vitest JSON test inventory contains an item without name or file."
                }
                if (
                    $nameProperty.ValueKind -ne [System.Text.Json.JsonValueKind]::String -or
                    $fileProperty.ValueKind -ne [System.Text.Json.JsonValueKind]::String -or
                    [string]::IsNullOrWhiteSpace($nameProperty.GetString()) -or
                    [string]::IsNullOrWhiteSpace($fileProperty.GetString())
                ) {
                    throw "Vitest JSON test inventory contains an item without a non-empty name and file."
                }
                $tests += [pscustomobject]@{
                    Name = $nameProperty.GetString()
                    File = $fileProperty.GetString()
                }
            }
            return $tests
        }
        finally {
            $document.Dispose()
        }
    }
    finally {
        Remove-Item -LiteralPath $stdoutPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }
}

function Assert-PhaseTwoCP3BTestInventory {
    $backendCollection = @(
        Invoke-CapturedChecked `
            -FilePath $python `
            -ArgumentList @(
                $pytestArguments +
                @("tests/backend", "--collect-only", "-q")
            )
    )
    $backendText = $backendCollection -join [Environment]::NewLine
    if ($backendText -notmatch '(?m)^509 tests collected in ') {
        throw "Backend test inventory is not exactly 509 collected tests."
    }

    $frontendTests = @(
        Get-VitestInventoryFromUtf8Capture `
            -FilePath $npmPath `
            -ArgumentList @(
                "exec", "--workspace", "apps/web", "--",
                "vitest", "list", "--json"
            )
    )
    if (
        $frontendTests.Count -ne 43 -or
        @($frontendTests | Where-Object { $_.Name -match '[가-힣]' }).Count -eq 0
    ) {
        throw "Frontend test inventory is not exactly 43 named tests including UTF-8 Korean names."
    }

    $e2eCollection = @(
        Invoke-CapturedChecked `
            -FilePath $npmPath `
            -ArgumentList @(
                "exec", "--workspace", "apps/web", "--",
                "playwright", "test", "--list", "--reporter=list"
            )
    )
    $e2eText = $e2eCollection -join [Environment]::NewLine
    if ($e2eText -notmatch '(?m)^Total:\s+2 tests in 1 file\s*$') {
        throw "Playwright test inventory is not exactly 2 tests in 1 file."
    }

    Write-Host "Test inventory verified: backend=509, frontend=43, e2e=2"
}

function Clear-StaleBackendTestDirectories {
    $testTempRoot = [System.IO.Path]::GetFullPath(
        (Join-Path $repoRoot "var\tmp\backend-tests")
    )
    Assert-SafeRepositoryPath -Path $testTempRoot
    if (-not (Test-Path -LiteralPath $testTempRoot)) {
        return
    }
    if (-not (Test-Path -LiteralPath $testTempRoot -PathType Container)) {
        throw "The backend test temp root has an unexpected type."
    }
    $rootItem = Get-Item -LiteralPath $testTempRoot -Force
    if ($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "The backend test temp root cannot be a reparse point."
    }
    $removedCount = 0
    foreach ($child in Get-ChildItem -LiteralPath $testTempRoot -Force) {
        if (
            -not $child.PSIsContainer -or
            $child.Name -cnotmatch '^[0-9a-f]{32}$' -or
            ($child.Attributes -band [System.IO.FileAttributes]::ReparsePoint)
        ) {
            throw "The backend test temp root contains an unexpected entry."
        }
        Assert-NoReparsePointsInTree -Path $child.FullName -RejectHardLinks
        Remove-Item -LiteralPath $child.FullName -Recurse -Force
        $removedCount += 1
    }
    if ($removedCount -gt 0) {
        Write-Host "Removed $removedCount stale backend test directories."
    }
}

function Invoke-WithPhaseNodeOfflineGuard {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock] $Action
    )

    $previousNodeOptionsEntry = Get-Item `
        -LiteralPath Env:NODE_OPTIONS `
        -ErrorAction SilentlyContinue
    $hadPreviousNodeOptionsEntry = $null -ne $previousNodeOptionsEntry
    $previousNodeOptionsValue = if ($hadPreviousNodeOptionsEntry) {
        $previousNodeOptionsEntry.Value
    }
    else {
        $null
    }
    if (-not [System.String]::IsNullOrWhiteSpace($previousNodeOptionsValue)) {
        throw "NODE_OPTIONS must be empty before the offline guard is installed."
    }

    $env:NODE_OPTIONS = [System.String]::Concat(
        '--require="',
        $offlineGuardPath.Replace("\", "/"),
        '"'
    )
    try {
        & $Action
    }
    finally {
        if ($hadPreviousNodeOptionsEntry) {
            $env:NODE_OPTIONS = $previousNodeOptionsValue
        }
        else {
            Remove-Item Env:NODE_OPTIONS -ErrorAction SilentlyContinue
        }
    }
}

Invoke-PhaseScript -Name "policy-scan.ps1"
Clear-StaleBackendTestDirectories
Invoke-Checked `
    -FilePath $python `
    -ArgumentList (Get-GuardedPythonModuleArguments `
        -Module "pip" `
        -ArgumentList @("check"))
$pythonRuntimeGuard = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "scripts\python_runtime_guard.py")
)
Invoke-Checked `
    -FilePath $python `
    -ArgumentList @("-I", "-B", "-S", $pythonRuntimeGuard, "--self-test")
foreach ($requiredNodeScript in @($offlineGuardPath, $nodePreflightPath)) {
    if (-not (Test-Path -LiteralPath $requiredNodeScript -PathType Leaf)) {
        throw "A required offline Node.js guard is missing: $requiredNodeScript"
    }
    Assert-SafeMutableRepositoryFile -Path $requiredNodeScript
}
Invoke-WithPhaseNodeOfflineGuard -Action {
    Invoke-Checked -FilePath $nodePath -ArgumentList @($nodePreflightPath)
    Assert-NpmDependencyTreeClean
    Invoke-Checked `
        -FilePath $npmPath `
        -ArgumentList @("ls", "--depth=0", "--workspaces", "--include-workspace-root")
}
Invoke-PhaseScript -Name "lint.ps1"
Invoke-PhaseScript -Name "typecheck.ps1"
Invoke-PhaseScript `
    -Name "process-cleanup-canary.ps1" `
    -ArgumentList @("-Iterations", "20")
Invoke-PhaseScript -Name "toss-live-preflight.ps1"
Invoke-PhaseScript -Name "toss-live-preflight.ps1" -ArgumentList @("-SelfTest")
Assert-PhaseTwoCP3BTestInventory
Invoke-Checked -FilePath $python -ArgumentList @(
    $pytestArguments + @("tests/backend", "-q")
)
Invoke-PhaseScript -Name "migrate.ps1" -ArgumentList @("-Action", "Test")
Invoke-PhaseScript -Name "import-fixtures.ps1" -ArgumentList @("-VerifyIdempotency")
Invoke-WithPhaseNodeOfflineGuard -Action {
    Invoke-Checked `
        -FilePath $npmPath `
        -ArgumentList @("run", "test", "--workspace", "apps/web")
}
Invoke-PhaseScript -Name "export-openapi.ps1" -ArgumentList @("-Check")
Invoke-PhaseScript -Name "build.ps1"
Invoke-PhaseScript -Name "e2e.ps1"
Invoke-PhaseScript -Name "secret-scan.ps1"
Invoke-PhaseScript -Name "policy-scan.ps1"

Write-Host "All Phase 2 CP3-B checks passed."
