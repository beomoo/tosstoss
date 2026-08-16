. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-RepoRoot
$scanner = Join-Path $repoRoot ".venv\Scripts\detect-secrets.exe"
if (-not (Test-Path -LiteralPath $scanner -PathType Leaf)) {
    throw "detect-secrets is not installed. Run scripts/setup.ps1 first."
}

$tempDirectory = New-TaskTempDirectory
try {
    $scanPath = Join-Path $tempDirectory "scan.json"
    Push-Location -LiteralPath $repoRoot
    try {
        $scanFiles = @(& git ls-files --cached --others --exclude-standard)
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to enumerate tracked and untracked repository files."
        }
        $scanFiles = @($scanFiles | Where-Object {
            $_ -and $_ -notmatch '(^|[\\/])PACKAGE_MANIFEST\.json$'
        })
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
    foreach ($property in $scan.results.PSObject.Properties) {
        foreach ($finding in $property.Value) {
            $findings += [pscustomobject]@{
                File = $property.Name
                Line = $finding.line_number
                Type = $finding.type
            }
        }
    }
    if ($findings.Count -gt 0) {
        $findings | Format-Table -AutoSize | Out-Host
        throw "Secret scan found $($findings.Count) potential secret(s)."
    }

    $sensitivePattern = '(?i)(sk-(?:live|proj)?[_-]?[a-z0-9_-]{20,}|gh[pousr]_[a-z0-9]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._-]{20,}|eyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{10,})'
    $sourceFiles = Get-ChildItem -LiteralPath $repoRoot -Recurse -File |
        Where-Object {
            $_.FullName -notmatch '[\\/](\.git|\.venv|node_modules|\.next|playwright-report|test-results|var)[\\/]'
        }
    $artifactRoots = @(
        (Join-Path $repoRoot "apps\web\.next\static"),
        (Join-Path $repoRoot "var\logs")
    ) | Where-Object { Test-Path -LiteralPath $_ }
    $artifactFiles = foreach ($root in $artifactRoots) {
        Get-ChildItem -LiteralPath $root -Recurse -File |
            Where-Object {
                $_.Extension -notin @(".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2")
            }
    }
    $inspectionFiles = @($sourceFiles) + @($artifactFiles)
    $patternHits = $inspectionFiles | Select-String -Pattern $sensitivePattern
    if ($patternHits) {
        $patternHits | Select-Object Path, LineNumber, Line | Format-Table -AutoSize | Out-Host
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
    if ([string]::IsNullOrWhiteSpace($sentinelValue)) {
        throw "Build sentinel evidence is empty."
    }
    $serverOnlyClient = Join-Path $repoRoot "apps\web\src\lib\api.server.ts"
    if (-not (Select-String -LiteralPath $serverOnlyClient -SimpleMatch "PHASE1_SERVER_ONLY_SENTINEL")) {
        throw "The server-only API client does not consume the runtime sentinel boundary."
    }
    $sentinelLeakRoots = @(
        (Join-Path $repoRoot "apps\web\.next\static"),
        (Join-Path $repoRoot "qa"),
        (Join-Path $repoRoot "contracts"),
        (Join-Path $repoRoot "var\logs")
    ) | Where-Object { Test-Path -LiteralPath $_ }
    $sentinelLeaks = foreach ($root in $sentinelLeakRoots) {
        Get-ChildItem -LiteralPath $root -Recurse -File |
            Select-String -SimpleMatch $sentinelValue
    }
    if ($sentinelLeaks) {
        $sentinelLeaks | Select-Object Path, LineNumber | Format-Table -AutoSize | Out-Host
        throw "The runtime sentinel leaked into a browser or API artifact."
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
