param(
    [switch] $VerifyIdempotency,
    [string] $DatabasePath
)

. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
$repoRoot = Get-RepoRoot
Assert-NoProjectPythonBytecode
$fixtureDirectory = Join-Path $repoRoot "fixtures\phase_01"
$temporaryDirectory = $null

if ($VerifyIdempotency) {
    $temporaryDirectory = New-TaskTempDirectory
    $DatabasePath = Join-Path $temporaryDirectory "fixture-import.db"
}
elseif ([string]::IsNullOrWhiteSpace($DatabasePath)) {
    $runtimeDirectory = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var"))
    Assert-SafeRepositoryPath -Path $runtimeDirectory
    [System.IO.Directory]::CreateDirectory($runtimeDirectory) | Out-Null
    Assert-SafeRepositoryPath -Path $runtimeDirectory
    $DatabasePath = Join-Path $runtimeDirectory "dashboard.db"
}

try {
    Assert-SafeSqliteDatabaseFiles -DatabasePath $DatabasePath
    $databaseUrl = Convert-ToSqliteUrl -Path $DatabasePath
    Invoke-Checked `
        -FilePath $python `
        -ArgumentList (Get-GuardedPythonModuleArguments `
            -Module "alembic" `
            -ArgumentList @("-x", "database_url=$databaseUrl", "upgrade", "head"))
    Assert-SafeSqliteDatabaseFiles -DatabasePath $DatabasePath
    $arguments = @(
        "--database-url", $databaseUrl,
        "--fixture-dir", $fixtureDirectory
    )
    if ($VerifyIdempotency) {
        $arguments += "--verify-idempotency"
    }
    Invoke-Checked `
        -FilePath $python `
        -ArgumentList (Get-GuardedPythonModuleArguments `
            -Module "toss_dashboard_api.fixtures.importer" `
            -ArgumentList $arguments)
    Assert-SafeSqliteDatabaseFiles -DatabasePath $DatabasePath
}
finally {
    if ($null -ne $temporaryDirectory) {
        Remove-TaskTempDirectory -Path $temporaryDirectory
    }
}
