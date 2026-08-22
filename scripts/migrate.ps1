param(
    [ValidateSet("Upgrade", "Downgrade", "Test")]
    [string] $Action = "Upgrade",
    [string] $DatabasePath,
    [switch] $ConfirmDisposable
)

. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
$repoRoot = Get-RepoRoot
Assert-NoProjectPythonBytecode

if ($Action -eq "Test") {
    $tempDirectory = New-TaskTempDirectory
    try {
        $testDatabase = Join-Path $tempDirectory "migration-test.db"
        $databaseUrl = Convert-ToSqliteUrl -Path $testDatabase
        foreach ($migrationArguments in @(
            @("-x", "database_url=$databaseUrl", "upgrade", "head"),
            @("-x", "database_url=$databaseUrl", "upgrade", "head"),
            @("-x", "database_url=$databaseUrl", "downgrade", "base"),
            @("-x", "database_url=$databaseUrl", "upgrade", "head")
        )) {
            Invoke-Checked `
                -FilePath $python `
                -ArgumentList (Get-GuardedPythonModuleArguments `
                    -Module "alembic" `
                    -ArgumentList $migrationArguments)
        }
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
    $runtimeDirectory = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var"))
    Assert-SafeRepositoryPath -Path $runtimeDirectory
    [System.IO.Directory]::CreateDirectory($runtimeDirectory) | Out-Null
    Assert-SafeRepositoryPath -Path $runtimeDirectory
    $DatabasePath = Join-Path $runtimeDirectory "dashboard.db"
}
Assert-SafeSqliteDatabaseFiles -DatabasePath $DatabasePath
$databaseUrl = Convert-ToSqliteUrl -Path $DatabasePath
$target = if ($Action -eq "Downgrade") { "base" } else { "head" }
$verb = if ($Action -eq "Downgrade") { "downgrade" } else { "upgrade" }
Invoke-Checked `
    -FilePath $python `
    -ArgumentList (Get-GuardedPythonModuleArguments `
        -Module "alembic" `
        -ArgumentList @("-x", "database_url=$databaseUrl", $verb, $target))
Assert-SafeSqliteDatabaseFiles -DatabasePath $DatabasePath
