. (Join-Path $PSScriptRoot "common.ps1")

$nodePath = Assert-PhaseNodeRuntime
$npmPath = Get-PhaseNpmCommandPath
$python = Get-VenvPython
$repoRoot = Get-RepoRoot
$nextDirectory = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "apps\web\.next")
)
$nextEnvPath = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "apps\web\next-env.d.ts")
)
$tsconfigPath = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "apps\web\tsconfig.json")
)
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
Assert-SafeRepositoryPath -Path $nextDirectory
Assert-SafeMutableRepositoryFile -Path $nextEnvPath
Assert-SafeMutableRepositoryFile -Path $tsconfigPath
if (Test-Path -LiteralPath $nextDirectory -PathType Container) {
    Assert-NoReparsePointsInTree -Path $nextDirectory -RejectHardLinks
}
$tempDirectory = New-TaskTempDirectory
try {
    $mypyCache = Join-Path $tempDirectory "mypy-cache"
    Invoke-Checked `
        -FilePath $python `
        -ArgumentList (Get-GuardedPythonModuleArguments `
            -Module "mypy" `
            -ArgumentList @("--cache-dir", $mypyCache, "services/api/src"))
}
finally {
    Remove-TaskTempDirectory -Path $tempDirectory
}
$hadNodeOptions = Test-Path -LiteralPath Env:NODE_OPTIONS
$previousNodeOptions = $env:NODE_OPTIONS
$env:NODE_OPTIONS = [System.String]::Concat(
    '--require="',
    $offlineGuardPath.Replace("\", "/"),
    '"'
)
$env:NPM_CONFIG_OFFLINE = "true"
$env:NEXT_IGNORE_INCORRECT_LOCKFILE = "1"
$env:NEXT_DISABLE_SWC_WASM = "1"
try {
    Assert-NpmDependencyTreeClean
    Invoke-Checked -FilePath $nodePath -ArgumentList @($nodePreflightPath)
    Invoke-Checked -FilePath $npmPath -ArgumentList @(
        "run", "typecheck", "--workspace", "apps/web"
    )
}
finally {
    if ($hadNodeOptions) {
        $env:NODE_OPTIONS = $previousNodeOptions
    }
    else {
        Remove-Item Env:NODE_OPTIONS -ErrorAction SilentlyContinue
    }
}
Assert-SafeMutableRepositoryFile -Path $nextEnvPath
Assert-SafeMutableRepositoryFile -Path $tsconfigPath
if (Test-Path -LiteralPath $nextDirectory -PathType Container) {
    Assert-NoReparsePointsInTree -Path $nextDirectory -RejectHardLinks
}
