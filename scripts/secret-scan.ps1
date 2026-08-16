. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-RepoRoot
$scanner = Join-Path $repoRoot ".venv\Scripts\detect-secrets.exe"
if (-not (Test-Path -LiteralPath $scanner -PathType Leaf)) {
    throw "detect-secrets is not installed. Run scripts/setup.ps1 first."
}
$playwrightArtifactRoots = @(
    (Join-Path $repoRoot "apps\web\playwright-report"),
    (Join-Path $repoRoot "apps\web\test-results")
) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
$textArtifactExtensions = @(
    ".js", ".mjs", ".cjs", ".json", ".jsonl", ".map", ".html", ".txt", ".log", ".css", ".xml"
)

$tempDirectory = New-TaskTempDirectory
try {
    $scanPath = Join-Path $tempDirectory "scan.json"
    Push-Location -LiteralPath $repoRoot
    try {
        $scanFiles = @(& git ls-files --cached --others --exclude-standard)
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to enumerate tracked and untracked repository files."
        }
        $playwrightTextFiles = foreach ($root in $playwrightArtifactRoots) {
            Get-ChildItem -LiteralPath $root -Recurse -File |
                Where-Object { $_.Extension.ToLowerInvariant() -in $textArtifactExtensions } |
                ForEach-Object {
                    [System.IO.Path]::GetRelativePath($repoRoot, $_.FullName).Replace("\", "/")
                }
        }
        $scanFiles = @($scanFiles + $playwrightTextFiles | Where-Object { $_ } | Sort-Object -Unique)
        $scanFiles = @($scanFiles | Where-Object { $_ })
        if ($scanFiles.Count -eq 0) {
            throw "No repository files were selected for secret scanning."
        }
        $scanOutput = & $scanner -c 1 scan --force-use-all-plugins --no-verify @scanFiles
        if ($LASTEXITCODE -ne 0) {
            throw "detect-secrets scan failed with exit code $LASTEXITCODE."
        }
        [System.IO.File]::WriteAllText($scanPath, ($scanOutput -join [Environment]::NewLine))
    }
    finally {
        Pop-Location
    }

    $scan = Get-Content -LiteralPath $scanPath -Raw | ConvertFrom-Json
    $findings = @()
    $allowedPackageManifestHashes = @()
    $packageManifestLines = @(Get-Content -LiteralPath (Join-Path $repoRoot "PACKAGE_MANIFEST.json"))
    foreach ($property in $scan.results.PSObject.Properties) {
        foreach ($finding in $property.Value) {
            $candidate = [pscustomobject]@{
                File = $property.Name
                Line = $finding.line_number
                Type = $finding.type
            }
            $normalizedFile = $candidate.File.Replace("\", "/")
            $lineIndex = [int] $candidate.Line - 1
            $isDeclaredPackageHash = (
                $normalizedFile -eq "PACKAGE_MANIFEST.json" -and
                $candidate.Type -eq "Hex High Entropy String" -and
                $lineIndex -ge 0 -and
                $lineIndex -lt $packageManifestLines.Count -and
                $packageManifestLines[$lineIndex].Trim() -match '^"sha256": "[0-9a-f]{64}"[,]?$'
            )
            if ($isDeclaredPackageHash) {
                # Narrow false-positive exception: only the exact SHA-256 value lines in the
                # immutable delivery integrity manifest are hashes rather than credentials.
                $allowedPackageManifestHashes += $candidate
            }
            else {
                $findings += $candidate
            }
        }
    }
    if ($findings.Count -gt 0) {
        $findings | Format-Table -AutoSize | Out-Host
        throw "Secret scan found $($findings.Count) potential secret(s)."
    }
    Write-Host (
        "Validated PACKAGE_MANIFEST.json SHA-256 false-positive lines: " +
        $allowedPackageManifestHashes.Count
    )

    $e2eApiLog = Join-Path $repoRoot "var\logs\phase-01-e2e-api.jsonl"
    if (-not (Test-Path -LiteralPath $e2eApiLog -PathType Leaf)) {
        throw "E2E API JSONL evidence is missing. Run scripts/e2e.ps1 first."
    }
    $e2eApiLogLines = @(Get-Content -LiteralPath $e2eApiLog |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($e2eApiLogLines.Count -eq 0) {
        throw "E2E API JSONL evidence is empty."
    }
    foreach ($line in $e2eApiLogLines) {
        try {
            $parsedLogLine = $line | ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            throw "E2E API log contains a non-JSON line."
        }
        if ($null -eq $parsedLogLine -or $parsedLogLine -isnot [pscustomobject]) {
            throw "E2E API log lines must be JSON objects."
        }
    }

    $sensitivePattern = '(?i)(sk-(?:live|proj)?[_-]?[a-z0-9_-]{20,}|gh[pousr]_[a-z0-9]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._-]{20,}|eyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{10,})'
    $sourceFiles = Get-ChildItem -LiteralPath $repoRoot -Recurse -File |
        Where-Object {
            $_.FullName -notmatch '[\\/](\.git|\.venv|node_modules|\.next|playwright-report|test-results|var)[\\/]'
        }
    $artifactRoots = @(
        (Join-Path $repoRoot "apps\web\.next\static"),
        (Join-Path $repoRoot "apps\web\.next\server"),
        (Join-Path $repoRoot "var\logs")
    ) + $playwrightArtifactRoots
    $artifactRoots = @(
        $artifactRoots | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
    )
    $artifactFiles = foreach ($root in $artifactRoots) {
        Get-ChildItem -LiteralPath $root -Recurse -File |
            Where-Object {
                $_.Extension.ToLowerInvariant() -in $textArtifactExtensions
            }
    }
    $inspectionFiles = @($sourceFiles) + @($artifactFiles)
    $patternHits = $inspectionFiles | Select-String -Pattern $sensitivePattern
    if ($patternHits) {
        $patternHits | Select-Object Path, LineNumber | Format-Table -AutoSize | Out-Host
        throw "High-confidence secret pattern detected."
    }

    $bundleRoot = Join-Path $repoRoot "apps\web\.next\static"
    if (Test-Path -LiteralPath $bundleRoot) {
        $bundleHits = Get-ChildItem -LiteralPath $bundleRoot -Recurse -File |
            Select-String -Pattern '(?i)(CLIENT_SECRET|ACCESS_TOKEN|AUTHORIZATION|PHASE1_SERVER_ONLY_SENTINEL|NEXT_PUBLIC_[A-Z0-9_]*(?:SECRET|TOKEN|KEY))'
        if ($bundleHits) {
            $bundleHits | Select-Object Path, LineNumber | Format-Table -AutoSize | Out-Host
            throw "Sensitive identifier found in browser bundle."
        }
    }

    $sentinelPath = Join-Path $repoRoot "var\phase-01-build-sentinel.txt"
    if (-not (Test-Path -LiteralPath $sentinelPath -PathType Leaf)) {
        throw "Build sentinel evidence is missing. Run scripts/build.ps1 first."
    }
    $sentinelValue = (Get-Content -LiteralPath $sentinelPath -Raw).Trim()
    if ($sentinelValue -notmatch '^PHASE1_RUNTIME_[0-9a-f]{32}$') {
        throw "Build sentinel evidence is empty or invalid."
    }
    $serverOnlyClient = Join-Path $repoRoot "apps\web\src\lib\api.server.ts"
    if (-not (Select-String -LiteralPath $serverOnlyClient -SimpleMatch "PHASE1_SERVER_ONLY_SENTINEL")) {
        throw "The server-only API client does not consume the runtime sentinel boundary."
    }
    $nextArtifactRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "apps\web\.next"))
    $nextCacheRoot = [System.IO.Path]::GetFullPath((Join-Path $nextArtifactRoot "cache"))
    $sentinelLeakFiles = @()
    if (Test-Path -LiteralPath $nextArtifactRoot -PathType Container) {
        $sentinelLeakFiles += @(Get-ChildItem -LiteralPath $nextArtifactRoot -Recurse -File |
            Where-Object {
                -not $_.FullName.StartsWith(
                    $nextCacheRoot + [System.IO.Path]::DirectorySeparatorChar,
                    [System.StringComparison]::OrdinalIgnoreCase
                )
            })
    }
    $sentinelLeakRoots = @(
        (Join-Path $repoRoot "qa"),
        (Join-Path $repoRoot "contracts"),
        (Join-Path $repoRoot "var\logs")
    ) + $playwrightArtifactRoots
    $sentinelLeakRoots = @(
        $sentinelLeakRoots | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
    )
    foreach ($root in $sentinelLeakRoots) {
        $sentinelLeakFiles += @(Get-ChildItem -LiteralPath $root -Recurse -File)
    }
    $sentinelLeaks = $sentinelLeakFiles | Select-String -SimpleMatch $sentinelValue
    if ($sentinelLeaks) {
        $sentinelLeaks | Select-Object Path, LineNumber | Format-Table -AutoSize | Out-Host
        throw "The runtime sentinel leaked into a browser or API artifact."
    }

    $traceArchives = foreach ($root in $playwrightArtifactRoots) {
        Get-ChildItem -LiteralPath $root -Recurse -File -Filter "*.zip"
    }
    foreach ($traceArchive in $traceArchives) {
        $archive = [System.IO.Compression.ZipFile]::OpenRead($traceArchive.FullName)
        try {
            foreach ($entry in $archive.Entries) {
                if ([string]::IsNullOrEmpty($entry.Name)) {
                    continue
                }
                $reader = [System.IO.StreamReader]::new(
                    $entry.Open(),
                    [System.Text.Encoding]::UTF8,
                    $true,
                    4096,
                    $false
                )
                try {
                    $entryText = $reader.ReadToEnd()
                }
                finally {
                    $reader.Dispose()
                }
                if ($entryText.Contains($sentinelValue)) {
                    throw "The runtime sentinel leaked into a Playwright trace archive."
                }
                if ($entryText -match $sensitivePattern) {
                    throw "A high-confidence secret pattern was found in a Playwright trace archive."
                }
            }
        }
        finally {
            $archive.Dispose()
        }
    }

    $ignored = git check-ignore .env 2>$null
    if ($LASTEXITCODE -ne 0 -or $ignored -notcontains ".env") {
        throw ".env is not ignored by Git."
    }
    $trackedEnv = git ls-files --error-unmatch .env 2>$null
    if ($LASTEXITCODE -eq 0 -or $trackedEnv) {
        throw ".env is tracked by Git."
    }

    Write-Host "Secret scan passed."
}
finally {
    Remove-TaskTempDirectory -Path $tempDirectory
}
