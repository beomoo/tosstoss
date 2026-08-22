. (Join-Path $PSScriptRoot "common.ps1")

Assert-PhaseNodeRuntime
$python = Get-VenvPython
$repoRoot = Get-RepoRoot

$parseErrors = @()
Get-ChildItem -LiteralPath (Join-Path $repoRoot "scripts") -Filter "*.ps1" -File -Force |
    ForEach-Object {
        $tokens = $null
        $fileErrors = $null
        [System.Management.Automation.Language.Parser]::ParseFile(
            $_.FullName,
            [ref] $tokens,
            [ref] $fileErrors
        ) | Out-Null
        $parseErrors += @($fileErrors)
    }
if ($parseErrors.Count -gt 0) {
    $parseErrors | Format-List | Out-Host
    throw "PowerShell parser found $($parseErrors.Count) error(s)."
}

Invoke-Checked -FilePath $python -ArgumentList @(
    Get-GuardedPythonModuleArguments `
        -Module "ruff" `
        -ArgumentList @(
            "format", "--check", "--no-cache",
            "services/api/src", "tests/backend",
            "scripts/python_runtime_guard.py", "scripts/secret_scan_driver.py"
        )
)
Invoke-Checked -FilePath $python -ArgumentList @(
    Get-GuardedPythonModuleArguments `
        -Module "ruff" `
        -ArgumentList @(
            "check", "--no-cache",
            "services/api/src", "tests/backend",
            "scripts/python_runtime_guard.py", "scripts/secret_scan_driver.py"
        )
)
foreach ($nodeScript in @(
    "scripts/node_offline_guard.cjs",
    "scripts/node_runtime_preflight.cjs"
)) {
    Invoke-Checked -FilePath "node" -ArgumentList @("--check", $nodeScript)
}
Assert-NpmDependencyTreeClean
Invoke-Checked -FilePath "npm" -ArgumentList @(
    "run", "lint", "--workspace", "apps/web"
)
