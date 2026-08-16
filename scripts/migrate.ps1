param(
    [ValidateSet("Upgrade", "Downgrade", "Test")]
    [string] $Action = "Upgrade",
    [string] $DatabasePath,
    [switch] $ConfirmDisposable
)

. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
$repoRoot = Get-RepoRoot

if ($Action -eq "Test") {
    $tempDirectory = New-TaskTempDirectory
    try {
        $testDatabase = Join-Path $tempDirectory "migration-test.db"
        $databaseUrl = Convert-ToSqliteUrl -Path $testDatabase
        Invoke-Checked -FilePath $python -ArgumentList @("-m", "alembic", "-x", "database_url=$databaseUrl", "upgrade", "head")
        Invoke-Checked -FilePath $python -ArgumentList @("-m", "alembic", "-x", "database_url=$databaseUrl", "upgrade", "head")
        Invoke-Checked -FilePath $python -ArgumentList @("-m", "alembic", "-x", "database_url=$databaseUrl", "downgrade", "base")
        Invoke-Checked -FilePath $python -ArgumentList @("-m", "alembic", "-x", "database_url=$databaseUrl", "upgrade", "head")
        Write-Host "Migration repeat/downgrade/re-upgrade test passed."
    }
    finally {
        Remove-TaskTempDirectory -Path $tempDirectory
    }
    exit 0
}

if ($Action -eq "Downgrade") {
    if ([string]::IsNullOrWhiteSpace($DatabasePath)) {
        throw "Downgrade requires an explicit -DatabasePath; the default runtime DB is protected."
    }
    if (-not $ConfirmDisposable) {
        throw "Downgrade drops Phase 1 tables. Re-run only for a disposable DB with -ConfirmDisposable."
    }
}

if ([string]::IsNullOrWhiteSpace($DatabasePath)) {
    $runtimeDirectory = Join-Path $repoRoot "var"
    [System.IO.Directory]::CreateDirectory($runtimeDirectory) | Out-Null
    $DatabasePath = Join-Path $runtimeDirectory "dashboard.db"
}
$databaseUrl = Convert-ToSqliteUrl -Path $DatabasePath
$target = if ($Action -eq "Downgrade") { "base" } else { "head" }
$verb = if ($Action -eq "Downgrade") { "downgrade" } else { "upgrade" }
Invoke-Checked -FilePath $python -ArgumentList @("-m", "alembic", "-x", "database_url=$databaseUrl", $verb, $target)
