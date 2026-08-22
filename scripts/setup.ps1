. (Join-Path $PSScriptRoot "common.ps1")

$powerShellVersion = [System.Version]::Parse($PSVersionTable.PSVersion.ToString())
if ($powerShellVersion -lt [System.Version]"7.4.0") {
    throw "PowerShell 7.4 or newer is required. Found $powerShellVersion."
}

Assert-CommandAvailable -Name "node"
Assert-CommandAvailable -Name "npm"
Assert-CommandAvailable -Name "py"

$nodeVersionText = (& node -p "process.versions.node").Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read Node.js version."
}
$nodeVersion = [System.Version]::Parse($nodeVersionText)
if ($nodeVersion -lt [System.Version]"24.15.0" -or $nodeVersion.Major -ge 25) {
    throw "Node.js 24.15.x is required. Found $nodeVersionText."
}

$npmVersionText = (& npm --version).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read npm version."
}
$npmVersion = [System.Version]::Parse($npmVersionText)
if ($npmVersion.Major -ne 11) {
    throw "npm 11 is required. Found $npmVersionText."
}

$pythonVersionText = (& py -3.13 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))").Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.13 is required and must be available through the py launcher."
}
$pythonVersion = [System.Version]::Parse($pythonVersionText)
if ($pythonVersion -lt [System.Version]"3.13.1" -or $pythonVersion.Major -ne 3 -or $pythonVersion.Minor -ne 13) {
    throw "Python 3.13.1 or newer within the 3.13 line is required. Found $pythonVersionText."
}
Write-Host "Python $pythonVersionText"

$repoRoot = Get-RepoRoot
$tempRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var\tmp"))
Assert-SafeRepositoryPath -Path $tempRoot
[System.IO.Directory]::CreateDirectory($tempRoot) | Out-Null
Assert-SafeRepositoryPath -Path $tempRoot
Assert-NoReparsePointsInTree -Path $tempRoot -RejectHardLinks
$nodeCompileCacheRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $tempRoot "node-compile-cache")
)
Assert-SafeRepositoryPath -Path $nodeCompileCacheRoot
if (Test-Path -LiteralPath $nodeCompileCacheRoot) {
    if (-not (Test-Path -LiteralPath $nodeCompileCacheRoot -PathType Container)) {
        throw "The Node compile-cache path has an unexpected type."
    }
    $nodeCompileCacheItem = Get-Item -LiteralPath $nodeCompileCacheRoot -Force
    if ($nodeCompileCacheItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "The Node compile-cache path cannot be a reparse point."
    }
    Assert-NoReparsePointsInTree -Path $nodeCompileCacheRoot -RejectHardLinks
    Remove-Item -LiteralPath $nodeCompileCacheRoot -Recurse -Force
    Write-Host "Removed the generated Node compile cache."
}
$env:TEMP = $tempRoot
$env:TMP = $tempRoot
$env:TMPDIR = $tempRoot
$env:PYTHONUTF8 = "1"
$venvRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot ".venv"))
$venvPython = [System.IO.Path]::GetFullPath(
    (Join-Path $venvRoot "Scripts\python.exe")
)
Assert-SafeRepositoryPath -Path $venvRoot
if (Test-Path -LiteralPath $venvRoot) {
    if (-not (Test-Path -LiteralPath $venvRoot -PathType Container)) {
        throw ".venv must be a directory when it already exists."
    }
    Assert-NoReparsePointsInTree -Path $venvRoot -RejectHardLinks
}
if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    Invoke-Checked -FilePath "py" -ArgumentList @("-3.13", "-m", "venv", "--without-pip", ".venv")
}
if (-not (Test-Path -LiteralPath $venvRoot -PathType Container)) {
    throw "The Python virtual environment was not created as a directory."
}
Assert-NoReparsePointsInTree -Path $venvRoot -RejectHardLinks
Assert-SafeRepositoryPath -Path $venvPython

& $venvPython -m pip --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Invoke-Checked -FilePath $venvPython -ArgumentList @("-m", "ensurepip", "--upgrade", "--default-pip")
}

$lockPath = Join-Path $repoRoot "requirements.lock"
if (-not (Test-Path -LiteralPath $lockPath -PathType Leaf)) {
    throw "requirements.lock is missing."
}

Invoke-Checked -FilePath $venvPython -ArgumentList @(
    "-m", "pip", "install", "--disable-pip-version-check",
    "--require-hashes", "-r", $lockPath
)
Invoke-Checked -FilePath $venvPython -ArgumentList @(
    "-m", "pip", "install", "--disable-pip-version-check",
    "--no-deps", "--no-build-isolation", "-e", "."
)
Assert-NoReparsePointsInTree -Path $venvRoot -RejectHardLinks

$env:NEXT_TELEMETRY_DISABLED = "1"
$nodeModulesRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "node_modules")
)
$allowedWorkspaceLink = [System.IO.Path]::GetFullPath(
    (Join-Path $nodeModulesRoot "@toss-dashboard\web")
)
function Assert-NodeModulesTreeSafe {
    if (-not (Test-Path -LiteralPath $nodeModulesRoot)) {
        Assert-SafeRepositoryPath -Path $nodeModulesRoot
        return
    }
    if (-not (Test-Path -LiteralPath $nodeModulesRoot -PathType Container)) {
        throw "node_modules must be a directory when it exists."
    }
    Assert-SafeRepositoryPath -Path $nodeModulesRoot
    $pending = [System.Collections.Generic.Queue[string]]::new()
    $pending.Enqueue($nodeModulesRoot)
    while ($pending.Count -gt 0) {
        $directory = $pending.Dequeue()
        foreach ($item in @(Get-ChildItem -LiteralPath $directory -Force)) {
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                if ($item.FullName -cne $allowedWorkspaceLink) {
                    throw "An unexpected reparse point exists in node_modules."
                }
                $target = $item.ResolveLinkTarget($true)
                $expectedTarget = [System.IO.Path]::GetFullPath(
                    (Join-Path $repoRoot "apps\web")
                )
                if (
                    $null -eq $target -or
                    [System.IO.Path]::GetFullPath($target.FullName) -cne $expectedTarget
                ) {
                    throw "The npm workspace link does not resolve to apps/web."
                }
                continue
            }
            if (-not $item.PSIsContainer -and [string] $item.LinkType -ceq "HardLink") {
                throw "A hard-linked file exists in node_modules."
            }
            if ($item.PSIsContainer) {
                $pending.Enqueue($item.FullName)
            }
        }
    }
}

function Remove-KnownNpmOptionalOrphans {
    $records = @(Get-NpmQueryRecords -Selector ':extraneous')
    if ($records.Count -eq 0) {
        return
    }
    $expected = [ordered]@{
        "@img/sharp-wasm32" = [ordered]@{
            version = "0.35.3"
            location = "node_modules/@img/sharp-wasm32"
        }
        "@emnapi/runtime" = [ordered]@{
            version = "1.11.3"
            location = "node_modules/@emnapi/runtime"
        }
    }
    if ($records.Count -ne $expected.Count) {
        throw "npm ci produced an unexpected set of extraneous packages."
    }
    foreach ($record in $records) {
        if (-not $expected.Contains([string] $record.name)) {
            throw "npm ci produced an unapproved extraneous package."
        }
        $approved = $expected[[string] $record.name]
        $target = [System.IO.Path]::GetFullPath(
            (Join-Path $repoRoot ([string] $approved.location))
        )
        if (
            [string] $record.version -cne [string] $approved.version -or
            [string] $record.location -cne [string] $approved.location -or
            [System.IO.Path]::GetFullPath([string] $record.path) -cne $target -or
            [System.IO.Path]::GetFullPath([string] $record.realpath) -cne $target
        ) {
            throw "An npm optional orphan did not match its exact approved identity."
        }
    }
    foreach ($approved in $expected.Values) {
        $target = [System.IO.Path]::GetFullPath(
            (Join-Path $repoRoot ([string] $approved.location))
        )
        Assert-SafeRepositoryPath -Path $target
        if (-not (Test-Path -LiteralPath $target -PathType Container)) {
            throw "An approved npm optional orphan directory is missing: $target"
        }
        Assert-NoReparsePointsInTree -Path $target -RejectHardLinks
        Remove-Item -LiteralPath $target -Recurse -Force
        if (Test-Path -LiteralPath $target) {
            throw "An approved npm optional orphan directory was not removed: $target"
        }
    }
}

Assert-NodeModulesTreeSafe
Invoke-Checked -FilePath "npm" -ArgumentList @("ci", "--no-audit", "--no-fund")
Assert-NodeModulesTreeSafe
Remove-KnownNpmOptionalOrphans
Assert-NpmDependencyTreeClean
Assert-NodeModulesTreeSafe
Invoke-Checked -FilePath "npm" -ArgumentList @(
    "exec", "--workspace", "apps/web", "--", "playwright", "install", "chromium"
)
Assert-NoReparsePointsInTree -Path $tempRoot -RejectHardLinks

Write-Host "Setup completed. No external API credentials were requested."
