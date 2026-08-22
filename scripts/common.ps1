Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Get-RepoRoot {
    return $script:RepoRoot
}

function Get-VenvPython {
    $pythonPath = Join-Path $script:RepoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Python virtual environment not found. Run scripts/setup.ps1 first."
    }
    return $pythonPath
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

function Assert-NoReparsePointsInTree {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
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
            if ($item.PSIsContainer) {
                $pending.Enqueue($item.FullName)
            }
        }
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
