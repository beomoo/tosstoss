Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$env:NODE_DISABLE_COMPILE_CACHE = "1"

$script:RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Get-RepoRoot {
    return $script:RepoRoot
}

function Test-IsSupportedPhaseNodeVersion {
    param(
        [Parameter(Mandatory = $true)]
        [System.Version] $Version
    )

    return $Version.Major -eq 24 -and $Version -ge [System.Version]"24.16.0"
}

function Assert-PhaseNodeRuntime {
    $inheritedNodeOptions = Get-Item `
        -LiteralPath Env:NODE_OPTIONS `
        -ErrorAction SilentlyContinue
    if (
        $null -ne $inheritedNodeOptions -and
        -not [System.String]::IsNullOrWhiteSpace($inheritedNodeOptions.Value)
    ) {
        throw "NODE_OPTIONS must be empty before a Phase 1 script starts."
    }

    $nodeCommand = Get-Command `
        -Name "node.exe" `
        -CommandType Application `
        -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $nodeCommand) {
        throw "Required command 'node.exe' was not found."
    }
    $nodePath = [System.IO.Path]::GetFullPath($nodeCommand.Source)
    if (
        -not (Test-Path -LiteralPath $nodePath -PathType Leaf) -or
        [System.IO.Path]::GetExtension($nodePath) -cne ".exe"
    ) {
        throw "The resolved Node.js runtime is not an executable file."
    }

    foreach ($canary in @(
        [pscustomobject]@{ Version = [System.Version]"24.15.0"; Supported = $false },
        [pscustomobject]@{ Version = [System.Version]"24.16.0"; Supported = $true },
        [pscustomobject]@{ Version = [System.Version]"24.19.0"; Supported = $true },
        [pscustomobject]@{ Version = [System.Version]"25.0.0"; Supported = $false }
    )) {
        if ((Test-IsSupportedPhaseNodeVersion -Version $canary.Version) -ne $canary.Supported) {
            throw "The Phase 1 Node.js version classifier failed its self-canary."
        }
    }

    $nodeVersionText = (& $nodePath -p "process.versions.node").Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read Node.js version."
    }
    try {
        $nodeVersion = [System.Version]::Parse($nodeVersionText)
    }
    catch {
        throw "Node.js emitted an invalid version: $nodeVersionText"
    }
    if (-not (Test-IsSupportedPhaseNodeVersion -Version $nodeVersion)) {
        throw (
            "Node.js 24.16.0 or newer within the 24.x line is required. " +
            "Node.js 24.15 and older are blocked because of a Windows native " +
            "TCP crash. Found $nodeVersionText."
        )
    }
}

function Get-VenvPython {
    $pythonPath = Join-Path $script:RepoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Python virtual environment not found. Run scripts/setup.ps1 first."
    }
    return $pythonPath
}

function Get-GuardedPythonModuleArguments {
    param(
        [Parameter(Mandatory = $true)]
        [ValidatePattern('^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*$')]
        [string] $Module,
        [string[]] $ArgumentList = @()
    )

    $guardPath = [System.IO.Path]::GetFullPath(
        (Join-Path $script:RepoRoot "scripts\python_runtime_guard.py")
    )
    if (-not (Test-Path -LiteralPath $guardPath -PathType Leaf)) {
        throw "The Python runtime offline guard is missing."
    }
    Assert-SafeMutableRepositoryFile -Path $guardPath
    return @("-I", "-B", "-S", $guardPath, "--module", $Module, "--") + $ArgumentList
}

function Get-GuardedPythonScriptArguments {
    param(
        [Parameter(Mandatory = $true)][string] $ScriptPath,
        [string[]] $ArgumentList = @()
    )

    $guardPath = [System.IO.Path]::GetFullPath(
        (Join-Path $script:RepoRoot "scripts\python_runtime_guard.py")
    )
    $approvedScriptPath = [System.IO.Path]::GetFullPath(
        (Join-Path $script:RepoRoot "scripts\secret_scan_driver.py")
    )
    $fullScriptPath = [System.IO.Path]::GetFullPath($ScriptPath)
    if (-not (Test-Path -LiteralPath $guardPath -PathType Leaf)) {
        throw "The Python runtime offline guard is missing."
    }
    if ($fullScriptPath -cne $approvedScriptPath) {
        throw "The guarded Python script is not the exact approved Phase 1 driver."
    }
    foreach ($requiredFile in @($guardPath, $fullScriptPath)) {
        Assert-SafeMutableRepositoryFile -Path $requiredFile
    }
    return @(
        "-I", "-B", "-S", "-X", "utf8", $guardPath,
        "--script", $fullScriptPath, "--"
    ) + $ArgumentList
}

function Assert-CommandAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found."
    }
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string] $FilePath,
        [string[]] $ArgumentList = @(),
        [string] $WorkingDirectory = $script:RepoRoot
    )

    Push-Location -LiteralPath $WorkingDirectory
    try {
        & $FilePath @ArgumentList
        $exitCode = $LASTEXITCODE
        if ($null -ne $exitCode -and $exitCode -ne 0) {
            throw "Command failed with exit code $($exitCode): $FilePath $($ArgumentList -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-PhaseScript {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,
        [string[]] $ArgumentList = @()
    )

    $path = Join-Path $PSScriptRoot $Name
    Invoke-Checked -FilePath "pwsh" -ArgumentList (@(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $path
    ) + $ArgumentList)
}

function Convert-ToSqliteUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    $absolutePath = [System.IO.Path]::GetFullPath($Path).Replace("\", "/")
    return "sqlite:///$absolutePath"
}

function Assert-NoReparsePointInPath {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $pathRoot = [System.IO.Path]::GetPathRoot($fullPath)
    if ([string]::IsNullOrEmpty($pathRoot)) {
        throw "A filesystem path must have an absolute root: $fullPath"
    }

    $current = $pathRoot
    $rootItem = Get-Item -LiteralPath $current -Force -ErrorAction Stop
    if ($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "Refusing a filesystem path whose root is a reparse point: $fullPath"
    }

    $relative = $fullPath.Substring($pathRoot.Length)
    foreach ($segment in @(
        $relative.Split(
            @(
                [System.IO.Path]::DirectorySeparatorChar,
                [System.IO.Path]::AltDirectorySeparatorChar
            ),
            [System.StringSplitOptions]::RemoveEmptyEntries
        )
    )) {
        $current = Join-Path $current $segment
        $item = Get-Item -LiteralPath $current -Force -ErrorAction SilentlyContinue
        if ($null -eq $item) {
            break
        }
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "Refusing a filesystem path with a reparse-point ancestor: $fullPath"
        }
    }
}

function Assert-SafeRepositoryPath {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    $repoRoot = [System.IO.Path]::GetFullPath($script:RepoRoot)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $repoPrefix = $repoRoot.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    if (
        $fullPath -cne $repoRoot -and
        -not $fullPath.StartsWith(
            $repoPrefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw "Refusing a mutable path outside the repository: $fullPath"
    }
    Assert-NoReparsePointInPath -Path $fullPath
}

function Assert-SafeMutableRepositoryFile {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    Assert-SafeRepositoryPath -Path $fullPath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        return
    }
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        throw "A mutable repository file path has an unexpected type: $fullPath"
    }
    $item = Get-Item -LiteralPath $fullPath -Force
    if ([string] $item.LinkType -ceq "HardLink") {
        throw "Refusing to modify a hard-linked repository file: $fullPath"
    }
}

function Assert-SafeSqliteDatabaseFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string] $DatabasePath
    )

    $fullDatabasePath = [System.IO.Path]::GetFullPath($DatabasePath)
    foreach ($candidate in @(
        $fullDatabasePath,
        "$fullDatabasePath-journal",
        "$fullDatabasePath-wal",
        "$fullDatabasePath-shm"
    )) {
        Assert-SafeMutableRepositoryFile -Path $candidate
    }
}

function Assert-NoReparsePointsInTree {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path,
        [switch] $RejectHardLinks
    )

    $root = [System.IO.Path]::GetFullPath($Path)
    Assert-SafeRepositoryPath -Path $root
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        throw "A reparse-point tree check requires an existing directory: $root"
    }

    $pending = [System.Collections.Generic.Queue[string]]::new()
    $pending.Enqueue($root)
    while ($pending.Count -gt 0) {
        $directory = $pending.Dequeue()
        foreach ($item in @(Get-ChildItem -LiteralPath $directory -Force)) {
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                throw "Refusing a recursive operation over a reparse point: $($item.FullName)"
            }
            if (
                $RejectHardLinks -and
                -not $item.PSIsContainer -and
                [string] $item.LinkType -ceq "HardLink"
            ) {
                throw "Refusing a mutable tree containing a hard-linked file: $($item.FullName)"
            }
            if ($item.PSIsContainer) {
                $pending.Enqueue($item.FullName)
            }
        }
    }
}

function Assert-NoProjectPythonBytecode {
    $bytecodeRoots = @(
        (Join-Path $script:RepoRoot "services\api"),
        (Join-Path $script:RepoRoot "tests"),
        (Join-Path $script:RepoRoot "scripts"),
        (Join-Path $script:RepoRoot "apps\web\src"),
        (Join-Path $script:RepoRoot "apps\web\tests")
    )
    foreach ($root in $bytecodeRoots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) {
            throw "A Python source scope is missing: $root"
        }
        Assert-NoReparsePointsInTree -Path $root -RejectHardLinks
        $bytecodeFiles = @(
            Get-ChildItem -LiteralPath $root -Recurse -File -Force |
                Where-Object { $_.Extension -in @(".pyc", ".pyo") }
        )
        if ($bytecodeFiles.Count -gt 0) {
            throw "Generated Python bytecode is prohibited in project source scopes."
        }
    }
    $rootBytecodeFiles = @(
        Get-ChildItem -LiteralPath $script:RepoRoot -File -Force |
            Where-Object { $_.Extension -in @(".pyc", ".pyo") }
    )
    if ($rootBytecodeFiles.Count -gt 0) {
        throw "Root-level Python bytecode is prohibited."
    }
}

function Get-NpmQueryRecords {
    param([Parameter(Mandatory = $true)][string] $Selector)

    Push-Location -LiteralPath $script:RepoRoot
    try {
        $queryOutput = @(& npm query $Selector --json 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    if ($exitCode -ne 0) {
        $queryOutput | ForEach-Object { Write-Host ([string] $_) }
        throw "npm query failed for selector '$Selector'."
    }
    try {
        return @(
            ($queryOutput -join [Environment]::NewLine) |
                ConvertFrom-Json -ErrorAction Stop
        )
    }
    catch {
        throw "npm query did not emit valid JSON for selector '$Selector'."
    }
}

function Assert-NpmDependencyTreeClean {
    foreach ($selector in @(':extraneous', ':invalid', ':missing')) {
        $records = @(Get-NpmQueryRecords -Selector $selector)
        if ($records.Count -eq 0) {
            continue
        }
        $records |
            Select-Object name, version, location |
            Format-Table -AutoSize |
            Out-Host
        throw "The npm dependency tree contains $selector package records."
    }
}

function New-TaskTempDirectory {
    $base = [System.IO.Path]::GetFullPath(
        (Join-Path $script:RepoRoot "var\tmp\phase-01")
    )
    Assert-SafeRepositoryPath -Path $base
    [System.IO.Directory]::CreateDirectory($base) | Out-Null
    Assert-SafeRepositoryPath -Path $base
    $path = Join-Path $base ([System.Guid]::NewGuid().ToString("N"))
    [System.IO.Directory]::CreateDirectory($path) | Out-Null
    Assert-SafeRepositoryPath -Path $path
    return $path
}

function Remove-TaskTempDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    $base = [System.IO.Path]::GetFullPath((Join-Path $script:RepoRoot "var\tmp\phase-01"))
    $target = [System.IO.Path]::GetFullPath($Path)
    $relativeTarget = [System.IO.Path]::GetRelativePath($base, $target)
    if ($relativeTarget -cnotmatch '^[0-9a-f]{32}$') {
        throw "Refusing to remove a directory outside the Phase 1 task temp root: $target"
    }
    Assert-SafeRepositoryPath -Path $base
    Assert-SafeRepositoryPath -Path $target
    if (Test-Path -LiteralPath $target) {
        if (-not (Test-Path -LiteralPath $target -PathType Container)) {
            throw "Refusing to recursively remove a non-directory task temp path: $target"
        }
        Assert-NoReparsePointsInTree -Path $target
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}
