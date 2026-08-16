param(
    [switch] $VerifyIdempotency,
    [string] $DatabasePath
)

. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
$repoRoot = Get-RepoRoot
$fixtureDirectory = Join-Path $repoRoot "fixtures\phase_01"
$temporaryDirectory = $null

if ($VerifyIdempotency) {
    $temporaryDirectory = New-TaskTempDirectory
    $DatabasePath = Join-Path $temporaryDirectory "fixture-import.db"
}
elseif ([string]::IsNullOrWhiteSpace($DatabasePath)) {
    $runtimeDirectory = Join-Path $repoRoot "var"
    [System.IO.Directory]::CreateDirectory($runtimeDirectory) | Out-Null
    $DatabasePath = Join-Path $runtimeDirectory "dashboard.db"
}

try {
    $databaseUrl = Convert-ToSqliteUrl -Path $DatabasePath
    Invoke-Checked -FilePath $python -ArgumentList @("-m", "alembic", "-x", "database_url=$databaseUrl", "upgrade", "head")
    $arguments = @(
        "-m", "toss_dashboard_api.fixtures.importer",
        "--database-url", $databaseUrl,
        "--fixture-dir", $fixtureDirectory
    )
    if ($VerifyIdempotency) {
        $arguments += "--verify-idempotency"
    }
    Invoke-Checked -FilePath $python -ArgumentList $arguments
}
finally {
    if ($null -ne $temporaryDirectory) {
        Remove-TaskTempDirectory -Path $temporaryDirectory
    }
}
