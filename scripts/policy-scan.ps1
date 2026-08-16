. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-RepoRoot
$scopedRoots = @(
    (Join-Path $repoRoot "services\api"),
    (Join-Path $repoRoot "apps\web"),
    (Join-Path $repoRoot "tests"),
    (Join-Path $repoRoot "scripts")
) | Where-Object { Test-Path -LiteralPath $_ }

$sourceFiles = foreach ($root in $scopedRoots) {
    Get-ChildItem -LiteralPath $root -Recurse -File |
        Where-Object {
            $_.FullName -notmatch '[\\/](node_modules|\.next|playwright-report|test-results|__pycache__)[\\/]' -and
            $_.Name -ne "next-env.d.ts" -and
            $_.FullName -ne $PSCommandPath
        }
}

function Assert-NoPattern {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Pattern,
        [Parameter(Mandatory = $true)]
        [string] $Message,
        [System.IO.FileInfo[]] $Files = $sourceFiles
    )

    if (-not $Files -or $Files.Count -eq 0) {
        return
    }
    $hits = $Files | Select-String -Pattern $Pattern
    if ($hits) {
        $hits | Select-Object Path, LineNumber, Line | Format-Table -AutoSize | Out-Host
        throw $Message
    }
}

$manifestFiles = @(
    (Join-Path $repoRoot "package.json"),
    (Join-Path $repoRoot "apps\web\package.json"),
    (Join-Path $repoRoot "pyproject.toml"),
    (Join-Path $repoRoot "requirements.lock")
) | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { Get-Item -LiteralPath $_ }

Assert-NoPattern -Pattern '(?i)(["''=/@]|^)(openai|dart-fss|sec-edgar-downloader)(["''<>=@/]|$)' `
    -Message "A prohibited external/OpenAI dependency was found." -Files $manifestFiles
Assert-NoPattern -Pattern '(?i)https?://(?!127\.0\.0\.1|localhost|example\.invalid)[a-z0-9]' `
    -Message "A non-local URL was found in Phase 1 source."
Assert-NoPattern -Pattern '(?i)(pytest\.mark\.skip|pytest\.skip|xfail|describe\.skip|it\.skip|test\.skip|test\.todo)' `
    -Message "A skipped, todo, or xfail test was found." `
    -Files ($sourceFiles | Where-Object { $_.FullName -match '[\\/](tests?|__tests__)[\\/]|\.test\.|\.spec\.' })
Assert-NoPattern -Pattern '(?i)NEXT_PUBLIC_[A-Z0-9_]*(SECRET|TOKEN|KEY)' `
    -Message "A sensitive NEXT_PUBLIC variable was found."
Assert-NoPattern -Pattern '(?i)(--host\s+0\.0\.0\.0|host\s*=\s*["'']0\.0\.0\.0|allow_origins\s*=\s*\[\s*["'']\*)' `
    -Message "A non-local bind or wildcard CORS setting was found."
Assert-NoPattern -Pattern '(?i)(/api/[A-Za-z0-9_/-]*(orders?|accounts?)|execute[_-]?trade|place[_-]?order)' `
    -Message "A prohibited order/account execution path was found."

Write-Host "Phase 1 scope policy scan passed."
