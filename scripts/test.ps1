. (Join-Path $PSScriptRoot "common.ps1")

Assert-PhaseNodeRuntime
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

function Assert-PhaseOneTestInventory {
    $backendCollection = @(
        Invoke-CapturedChecked `
            -FilePath $python `
            -ArgumentList @(
                $pytestArguments +
                @("tests/backend", "--collect-only", "-q")
            )
    )
    $backendText = $backendCollection -join [Environment]::NewLine
    if ($backendText -notmatch '(?m)^172 tests collected in ') {
        throw "Backend test inventory is not exactly 172 collected tests."
    }

    $frontendCollection = @(
        Invoke-CapturedChecked `
            -FilePath "npm" `
            -ArgumentList @(
                "exec", "--workspace", "apps/web", "--",
                "vitest", "list", "--json"
            )
    )
    try {
        $frontendTests = @(
            ($frontendCollection -join [Environment]::NewLine) |
                ConvertFrom-Json -ErrorAction Stop
        )
    }
    catch {
        throw "Vitest did not emit a valid JSON test inventory."
    }
    if (
        $frontendTests.Count -ne 43 -or
        @($frontendTests | Where-Object {
            $_ -isnot [pscustomobject] -or
            [string]::IsNullOrWhiteSpace([string] $_.name) -or
            [string]::IsNullOrWhiteSpace([string] $_.file)
        }).Count -gt 0
    ) {
        throw "Frontend test inventory is not exactly 43 named tests."
    }

    $e2eCollection = @(
        Invoke-CapturedChecked `
            -FilePath "npm" `
            -ArgumentList @(
                "exec", "--workspace", "apps/web", "--",
                "playwright", "test", "--list", "--reporter=list"
            )
    )
    $e2eText = $e2eCollection -join [Environment]::NewLine
    if ($e2eText -notmatch '(?m)^Total:\s+2 tests in 1 file\s*$') {
        throw "Playwright test inventory is not exactly 2 tests in 1 file."
    }

    Write-Host "Test inventory verified: backend=172, frontend=43, e2e=2"
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
$env:NODE_OPTIONS = [System.String]::Concat(
    '--require="',
    $offlineGuardPath.Replace("\", "/"),
    '"'
)
Invoke-Checked -FilePath "node" -ArgumentList @($nodePreflightPath)
Assert-NpmDependencyTreeClean
Invoke-Checked -FilePath "npm" -ArgumentList @("ls", "--depth=0", "--workspaces", "--include-workspace-root")
Invoke-PhaseScript -Name "lint.ps1"
Invoke-PhaseScript -Name "typecheck.ps1"
Invoke-PhaseScript `
    -Name "process-cleanup-canary.ps1" `
    -ArgumentList @("-Iterations", "20")
Assert-PhaseOneTestInventory
Invoke-Checked -FilePath $python -ArgumentList @(
    $pytestArguments + @("tests/backend", "-q")
)
Invoke-PhaseScript -Name "migrate.ps1" -ArgumentList @("-Action", "Test")
Invoke-PhaseScript -Name "import-fixtures.ps1" -ArgumentList @("-VerifyIdempotency")
Invoke-Checked -FilePath "npm" -ArgumentList @("run", "test", "--workspace", "apps/web")
Invoke-PhaseScript -Name "export-openapi.ps1" -ArgumentList @("-Check")
Invoke-PhaseScript -Name "build.ps1"
Invoke-PhaseScript -Name "e2e.ps1"
Invoke-PhaseScript -Name "secret-scan.ps1"
Invoke-PhaseScript -Name "policy-scan.ps1"

Write-Host "All Phase 1 checks passed."
