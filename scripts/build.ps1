. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
$repoRoot = Get-RepoRoot
Assert-NoProjectPythonBytecode
$env:NEXT_TELEMETRY_DISABLED = "1"
$env:NPM_CONFIG_OFFLINE = "true"
$env:NEXT_IGNORE_INCORRECT_LOCKFILE = "1"
$env:NEXT_DISABLE_SWC_WASM = "1"

$runtimeDirectory = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var"))
$webRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "apps\web"))
$nextDirectory = [System.IO.Path]::GetFullPath((Join-Path $webRoot ".next"))
$nextEnvPath = [System.IO.Path]::GetFullPath((Join-Path $webRoot "next-env.d.ts"))
$tsconfigPath = [System.IO.Path]::GetFullPath((Join-Path $webRoot "tsconfig.json"))
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
$apiSourceRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "services\api\src")
)
$webSourceRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $webRoot "src")
)
$buildInputTrees = @($apiSourceRoot, $webSourceRoot)
$buildInputFiles = @(
    $offlineGuardPath,
    $nodePreflightPath,
    (Join-Path $repoRoot "package.json"),
    (Join-Path $repoRoot "package-lock.json"),
    (Join-Path $webRoot "package.json"),
    (Join-Path $webRoot "next.config.ts"),
    $tsconfigPath
)

function Assert-WebBuildInputTreeSafe {
    $excludedDirectories = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($excludedPath in @(
        $nextDirectory,
        (Join-Path $webRoot "node_modules"),
        (Join-Path $webRoot "playwright-report"),
        (Join-Path $webRoot "test-results")
    )) {
        $null = $excludedDirectories.Add(
            [System.IO.Path]::GetFullPath($excludedPath)
        )
    }
    $rootItem = Get-Item -LiteralPath $webRoot -Force
    if ($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "The web build-input root cannot be a reparse point."
    }
    $pending = [System.Collections.Generic.Stack[string]]::new()
    $pending.Push($webRoot)
    while ($pending.Count -gt 0) {
        $directory = $pending.Pop()
        foreach ($item in Get-ChildItem -LiteralPath $directory -Force -ErrorAction Stop) {
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                throw "A web build-input path is a reparse point: $($item.FullName)"
            }
            if ($item.PSIsContainer) {
                if (-not $excludedDirectories.Contains($item.FullName)) {
                    $pending.Push($item.FullName)
                }
                continue
            }
            if ([string] $item.LinkType -ceq "HardLink") {
                throw "A web build-input file is hard-linked: $($item.FullName)"
            }
        }
    }
}

function Assert-BuildInputsSafe {
    Assert-WebBuildInputTreeSafe
    foreach ($tree in $buildInputTrees) {
        Assert-NoReparsePointsInTree -Path $tree -RejectHardLinks
    }
    foreach ($file in $buildInputFiles) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "A required build input is missing: $file"
        }
        Assert-SafeMutableRepositoryFile -Path $file
    }
}

$buildIdPath = [System.IO.Path]::GetFullPath((Join-Path $nextDirectory "BUILD_ID"))
$staticDirectory = [System.IO.Path]::GetFullPath((Join-Path $nextDirectory "static"))
$serverDirectory = [System.IO.Path]::GetFullPath((Join-Path $nextDirectory "server"))
$sentinelPath = [System.IO.Path]::GetFullPath(
    (Join-Path $runtimeDirectory "phase-01-build-sentinel.txt")
)
$buildEvidencePath = [System.IO.Path]::GetFullPath(
    (Join-Path $runtimeDirectory "phase-01-build-evidence.json")
)
$staleEvidencePaths = @(
    $sentinelPath,
    $buildEvidencePath,
    (Join-Path $runtimeDirectory "logs\phase-01-e2e-api.jsonl"),
    (Join-Path $runtimeDirectory "logs\phase-01-e2e-web.log"),
    (Join-Path $webRoot "playwright-report"),
    (Join-Path $webRoot "test-results")
)
$recursiveEvidencePaths = @(
    [System.IO.Path]::GetFullPath((Join-Path $webRoot "playwright-report")),
    [System.IO.Path]::GetFullPath((Join-Path $webRoot "test-results"))
)

$mutablePaths = @(
    $runtimeDirectory,
    $nextDirectory,
    $sentinelPath,
    $buildEvidencePath
)
$mutablePaths += $staleEvidencePaths
foreach ($mutablePath in $mutablePaths) {
    Assert-SafeRepositoryPath -Path $mutablePath
}
if (Test-Path -LiteralPath $nextDirectory -PathType Container) {
    Assert-NoReparsePointsInTree -Path $nextDirectory -RejectHardLinks
}
Assert-SafeMutableRepositoryFile -Path $nextEnvPath
Assert-SafeMutableRepositoryFile -Path $tsconfigPath

function Remove-StaleBuildEvidence {
    foreach ($path in $staleEvidencePaths) {
        Assert-SafeRepositoryPath -Path $path
        if (Test-Path -LiteralPath $path) {
            $resolvedPath = [System.IO.Path]::GetFullPath($path)
            if (Test-Path -LiteralPath $path -PathType Container) {
                $pathItem = Get-Item -LiteralPath $path -Force
                if ($pathItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                    throw "Refusing to recursively remove a reparse-point evidence directory."
                }
                Assert-NoReparsePointsInTree -Path $resolvedPath
                if ($resolvedPath -notin $recursiveEvidencePaths) {
                    throw "Refusing to recursively remove an unexpected evidence directory."
                }
                $expectedParent = [System.IO.Path]::GetFullPath($webRoot)
                if (
                    [System.IO.Path]::GetDirectoryName($resolvedPath) -ne $expectedParent -or
                    [System.IO.Path]::GetFileName($resolvedPath) -notin @(
                        "playwright-report", "test-results"
                    )
                ) {
                    throw "Refusing to remove an E2E artifact outside the web workspace."
                }
                Remove-Item -LiteralPath $resolvedPath -Recurse -Force
                continue
            }
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
                throw "Refusing to remove an evidence path with an unexpected type."
            }
            Remove-Item -LiteralPath $resolvedPath -Force
        }
    }
}

function Remove-ValidatedGeneratedDirectory {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $ExpectedParent,
        [Parameter(Mandatory = $true)][string] $ExpectedName
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullParent = [System.IO.Path]::GetFullPath($ExpectedParent)
    Assert-SafeRepositoryPath -Path $fullPath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        return
    }
    if (
        -not (Test-Path -LiteralPath $fullPath -PathType Container) -or
        [System.IO.Path]::GetDirectoryName($fullPath) -cne $fullParent -or
        [System.IO.Path]::GetFileName($fullPath) -cne $ExpectedName
    ) {
        throw "Refusing to remove an unexpected generated directory."
    }
    $item = Get-Item -LiteralPath $fullPath -Force
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "Refusing to remove a generated directory through a reparse point."
    }
    Assert-NoReparsePointsInTree -Path $fullPath -RejectHardLinks
    Remove-Item -LiteralPath $fullPath -Recurse -Force
}

Remove-StaleBuildEvidence
Remove-ValidatedGeneratedDirectory `
    -Path $nextDirectory `
    -ExpectedParent $webRoot `
    -ExpectedName ".next"
[System.IO.Directory]::CreateDirectory($runtimeDirectory) | Out-Null
Assert-SafeRepositoryPath -Path $runtimeDirectory

$publicEnvironmentVariables = @(
    Get-ChildItem Env: | Where-Object { $_.Name -like "NEXT_PUBLIC_*" }
)
if ($publicEnvironmentVariables.Count -gt 0) {
    throw "NEXT_PUBLIC environment variables are prohibited in the Phase 1 build."
}
$nextEnvironmentFiles = @(
    Get-ChildItem -LiteralPath $repoRoot -Force -File -Filter ".env*"
    Get-ChildItem -LiteralPath $webRoot -Force -File -Filter ".env*"
)
$publicEnvironmentFilePattern = [string]::Concat(
    '(?m)^(?:',
    ([string] [char] 0xFEFF),
    ')?\s*(?:export\s+)?NEXT_PUBLIC_[A-Za-z0-9_]+\s*(?:=\s*|:\s+)'
)
$publicEnvironmentCanaries = @(
    [string]::Concat("NEXT_", "PUBLIC_CANARY=value"),
    [string]::Concat("NEXT_", "PUBLIC_CANARY: value"),
    [string]::Concat(
        ([string] [char] 0xFEFF),
        "NEXT_",
        "PUBLIC_CANARY=value"
    )
)
if (@($publicEnvironmentCanaries | Where-Object {
    $_ -notmatch $publicEnvironmentFilePattern
}).Count -gt 0) {
    throw "The Next.js public-environment detector missed a negative canary."
}
foreach ($environmentFile in $nextEnvironmentFiles) {
    Assert-SafeMutableRepositoryFile -Path $environmentFile.FullName
    if (
        (Get-Content -LiteralPath $environmentFile.FullName -Raw) -match
            $publicEnvironmentFilePattern
    ) {
        throw "A Next.js environment file contains a prohibited public variable."
    }
}

Assert-BuildInputsSafe
$pythonSyntaxCheck = @'
import ast
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve(strict=True)
for path in sorted(root.rglob("*.py")):
    source = path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(path))
'@
Invoke-Checked -FilePath $python -ArgumentList @(
    "-I", "-B", "-c", $pythonSyntaxCheck, $apiSourceRoot
)
Assert-BuildInputsSafe

$sentinelValue = "PHASE1_RUNTIME_" + [System.Guid]::NewGuid().ToString("N")
Assert-SafeMutableRepositoryFile -Path $sentinelPath
[System.IO.File]::WriteAllText($sentinelPath, $sentinelValue)
Assert-SafeMutableRepositoryFile -Path $sentinelPath
$env:PHASE1_SERVER_ONLY_SENTINEL = $sentinelValue
$buildSucceeded = $false
$hadNodeOptions = Test-Path -LiteralPath Env:NODE_OPTIONS
$previousNodeOptions = $env:NODE_OPTIONS
$env:NODE_OPTIONS = [System.String]::Concat(
    '--require="',
    $offlineGuardPath.Replace("\", "/"),
    '"'
)

try {
    Assert-NpmDependencyTreeClean
    Invoke-Checked -FilePath "node" -ArgumentList @($nodePreflightPath)
    Invoke-Checked -FilePath "npm" -ArgumentList @(
        "run", "build", "--workspace", "apps/web"
    )
    Assert-BuildInputsSafe
    foreach ($generatedCacheName in @("cache", "dev")) {
        Remove-ValidatedGeneratedDirectory `
            -Path (Join-Path $nextDirectory $generatedCacheName) `
            -ExpectedParent $nextDirectory `
            -ExpectedName $generatedCacheName
    }
    Assert-SafeMutableRepositoryFile -Path $nextEnvPath
    Assert-SafeMutableRepositoryFile -Path $tsconfigPath
    Assert-NoReparsePointsInTree -Path $nextDirectory -RejectHardLinks
    foreach ($unexpectedSwcDirectory in @(
        (Join-Path $repoRoot "node_modules\next\next-swc-fallback"),
        (Join-Path $repoRoot "node_modules\next\wasm")
    )) {
        if (Test-Path -LiteralPath $unexpectedSwcDirectory) {
            throw "Next.js created an unexpected SWC fallback directory."
        }
    }
    Assert-NpmDependencyTreeClean

    if (-not (Test-Path -LiteralPath $buildIdPath -PathType Leaf)) {
        throw "The production BUILD_ID is missing after the Next.js build."
    }
    $sentinelItem = Get-Item -LiteralPath $sentinelPath
    foreach ($requiredDirectory in @($staticDirectory, $serverDirectory)) {
        if (-not (Test-Path -LiteralPath $requiredDirectory -PathType Container)) {
            throw "A required production build directory is missing: $requiredDirectory"
        }
        $directoryItem = Get-Item -LiteralPath $requiredDirectory -Force
        if ($directoryItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "A required production build directory cannot be a reparse point."
        }
        Assert-NoReparsePointsInTree -Path $requiredDirectory -RejectHardLinks
        $artifactFiles = @(
            Get-ChildItem -LiteralPath $requiredDirectory -Recurse -File -Force
        )
        if ($artifactFiles.Count -eq 0) {
            throw "A required production build directory is empty: $requiredDirectory"
        }
        if (@($artifactFiles | Where-Object {
            $_.LastWriteTimeUtc -lt $sentinelItem.LastWriteTimeUtc
        }).Count -gt 0) {
            throw "A required production build directory contains stale artifacts."
        }
    }

    $buildId = [System.IO.File]::ReadAllText($buildIdPath).Trim()
    if ($buildId -notmatch '^[A-Za-z0-9_-]{8,128}$') {
        throw "The production BUILD_ID is empty or invalid."
    }
    $buildIdItem = Get-Item -LiteralPath $buildIdPath
    if ($buildIdItem.LastWriteTimeUtc -lt $sentinelItem.LastWriteTimeUtc) {
        throw "The production BUILD_ID predates the current build sentinel."
    }

    $sentinelSha256 = (Get-FileHash -LiteralPath $sentinelPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $buildEvidence = [ordered]@{
        schema_version = 1
        build_id = $buildId
        sentinel_sha256 = $sentinelSha256
        sentinel_written_at_utc = $sentinelItem.LastWriteTimeUtc.ToString("O")
        build_id_written_at_utc = $buildIdItem.LastWriteTimeUtc.ToString("O")
        completed_at_utc = [System.DateTime]::UtcNow.ToString("O")
    }
    Assert-SafeMutableRepositoryFile -Path $buildEvidencePath
    [System.IO.File]::WriteAllText(
        $buildEvidencePath,
        (($buildEvidence | ConvertTo-Json -Depth 4) + [Environment]::NewLine)
    )
    Assert-SafeMutableRepositoryFile -Path $buildEvidencePath
    $buildSucceeded = $true
}
finally {
    if ($hadNodeOptions) {
        $env:NODE_OPTIONS = $previousNodeOptions
    }
    else {
        Remove-Item Env:NODE_OPTIONS -ErrorAction SilentlyContinue
    }
    Remove-Item Env:PHASE1_SERVER_ONLY_SENTINEL -ErrorAction SilentlyContinue
    if (-not $buildSucceeded) {
        Remove-StaleBuildEvidence
    }
}
