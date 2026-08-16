. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
$repoRoot = Get-RepoRoot

$parseErrors = @()
Get-ChildItem -LiteralPath (Join-Path $repoRoot "scripts") -Filter "*.ps1" -File |
    ForEach-Object {
        $tokens = $null
        $fileErrors = $null
        [System.Management.Automation.Language.Parser]::ParseFile(
            $_.FullName,
            [ref] $tokens,
            [ref] $fileErrors
        ) | Out-Null
        $parseErrors += @($fileErrors)
    }
if ($parseErrors.Count -gt 0) {
    $parseErrors | Format-List | Out-Host
    throw "PowerShell parser found $($parseErrors.Count) error(s)."
}

Invoke-Checked -FilePath $python -ArgumentList @(
    "-m", "ruff", "format", "--check", "services/api/src", "tests/backend"
)
Invoke-Checked -FilePath $python -ArgumentList @(
    "-m", "ruff", "check", "services/api/src", "tests/backend"
)
Invoke-Checked -FilePath "npm" -ArgumentList @(
    "run", "lint", "--workspace", "apps/web"
)
