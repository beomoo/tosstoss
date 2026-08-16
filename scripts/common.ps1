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

function New-TaskTempDirectory {
    $base = Join-Path $script:RepoRoot "var\tmp\phase-01"
    [System.IO.Directory]::CreateDirectory($base) | Out-Null
    $path = Join-Path $base ([System.Guid]::NewGuid().ToString("N"))
    [System.IO.Directory]::CreateDirectory($path) | Out-Null
    return $path
}

function Remove-TaskTempDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    $base = [System.IO.Path]::GetFullPath((Join-Path $script:RepoRoot "var\tmp\phase-01"))
    $target = [System.IO.Path]::GetFullPath($Path)
    $basePrefix = $base.TrimEnd([System.IO.Path]::DirectorySeparatorChar) +
        [System.IO.Path]::DirectorySeparatorChar

    if (-not $target.StartsWith($basePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a directory outside the Phase 1 task temp root: $target"
    }
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}
