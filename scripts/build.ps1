. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
$repoRoot = Get-RepoRoot
$env:NEXT_TELEMETRY_DISABLED = "1"

$runtimeDirectory = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var"))
$webRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "apps\web"))
$nextDirectory = [System.IO.Path]::GetFullPath((Join-Path $webRoot ".next"))
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
    Assert-NoReparsePointsInTree -Path $nextDirectory
}

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

Remove-StaleBuildEvidence
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
foreach ($environmentFile in $nextEnvironmentFiles) {
    if (
        (Get-Content -LiteralPath $environmentFile.FullName -Raw) -match
            '(?m)^\s*(?:export\s+)?NEXT_PUBLIC_[A-Za-z0-9_]+\s*='
    ) {
        throw "A Next.js environment file contains a prohibited public variable."
    }
}

Invoke-Checked -FilePath $python -ArgumentList @(
    "-m", "compileall", "-q", "services/api/src"
)

$sentinelValue = "PHASE1_RUNTIME_" + [System.Guid]::NewGuid().ToString("N")
[System.IO.File]::WriteAllText($sentinelPath, $sentinelValue)
$env:PHASE1_SERVER_ONLY_SENTINEL = $sentinelValue
$buildSucceeded = $false

try {
    Invoke-Checked -FilePath "npm" -ArgumentList @(
        "run", "build", "--workspace", "apps/web"
    )

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
        Assert-NoReparsePointsInTree -Path $requiredDirectory
        $artifactFiles = @(Get-ChildItem -LiteralPath $requiredDirectory -Recurse -File)
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
    [System.IO.File]::WriteAllText(
        $buildEvidencePath,
        (($buildEvidence | ConvertTo-Json -Depth 4) + [Environment]::NewLine)
    )
    $buildSucceeded = $true
}
finally {
    Remove-Item Env:PHASE1_SERVER_ONLY_SENTINEL -ErrorAction SilentlyContinue
    if (-not $buildSucceeded) {
        Remove-StaleBuildEvidence
    }
}
