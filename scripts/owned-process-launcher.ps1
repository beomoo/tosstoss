param(
    [Parameter(Mandatory = $true)][string] $LaunchSpecPath,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{64}$')]
    [string] $ExpectedSha256
)

. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-RepoRoot
$specificationPath = [System.IO.Path]::GetFullPath($LaunchSpecPath)
$taskTempRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "var\tmp\phase-01")
)
$relativeSpecificationPath = [System.IO.Path]::GetRelativePath(
    $taskTempRoot,
    $specificationPath
).Replace("\", "/")
if (
    $relativeSpecificationPath -cnotmatch
        '^[0-9a-f]{32}/owned-launch-[a-z][a-z0-9-]{0,31}-[0-9a-f]{32}\.json$'
) {
    throw "The owned process launch specification is outside its exact temp scope."
}
Assert-SafeMutableRepositoryFile -Path $specificationPath
if (-not (Test-Path -LiteralPath $specificationPath -PathType Leaf)) {
    throw "The owned process launch specification is missing."
}
$utf8 = [System.Text.UTF8Encoding]::new($false, $true)
$specificationBytes = [System.IO.File]::ReadAllBytes($specificationPath)
if ($specificationBytes.Length -gt 65536) {
    throw "The owned process launch specification is unexpectedly large."
}
$sha256Algorithm = [System.Security.Cryptography.SHA256]::Create()
try {
    $actualSha256 = [System.Convert]::ToHexString(
        $sha256Algorithm.ComputeHash($specificationBytes)
    ).ToLowerInvariant()
}
finally {
    $sha256Algorithm.Dispose()
}
if ($actualSha256 -cne $ExpectedSha256) {
    throw "The owned process launch specification changed before use."
}
$json = $utf8.GetString($specificationBytes)
try {
    $specification = $json | ConvertFrom-Json -ErrorAction Stop
}
catch {
    throw "The owned process launch specification is not valid JSON."
}
$expectedProperties = @(
    "schema_version",
    "file_path",
    "working_directory",
    "argument_list",
    "standard_output_path",
    "standard_error_path"
) | Sort-Object
$actualProperties = @($specification.PSObject.Properties.Name) | Sort-Object
if (
    (Compare-Object -ReferenceObject $expectedProperties -DifferenceObject $actualProperties) -or
    $specification.schema_version -ne 2
) {
    throw "The owned process launch specification has an invalid schema."
}

$targetPath = [System.IO.Path]::GetFullPath([string] $specification.file_path)
if (-not (Test-Path -LiteralPath $targetPath -PathType Leaf)) {
    throw "The owned process target is missing."
}
$workingDirectory = [System.IO.Path]::GetFullPath(
    [string] $specification.working_directory
)
Assert-SafeRepositoryPath -Path $workingDirectory
if (-not (Test-Path -LiteralPath $workingDirectory -PathType Container)) {
    throw "The owned process working directory is missing."
}
$arguments = @($specification.argument_list)
if (@($arguments | Where-Object { $_ -isnot [string] }).Count -gt 0) {
    throw "The owned process argument list contains a non-string value."
}

$standardOutputPath = [System.IO.Path]::GetFullPath(
    [string] $specification.standard_output_path
)
$standardErrorPath = [System.IO.Path]::GetFullPath(
    [string] $specification.standard_error_path
)
if ($standardOutputPath -ceq $standardErrorPath) {
    throw "Owned process output and error paths must be different."
}
foreach ($logPath in @($standardOutputPath, $standardErrorPath)) {
    Assert-SafeMutableRepositoryFile -Path $logPath
    if (-not (Test-Path -LiteralPath $logPath -PathType Leaf)) {
        throw "An owned process log path is missing."
    }
}

function Convert-ToWindowsProcessArgument {
    param([AllowEmptyString()][Parameter(Mandatory = $true)][string] $Argument)

    if (-not [string]::IsNullOrEmpty($Argument) -and $Argument -cnotmatch '[\s"]') {
        return $Argument
    }
    $backslash = [char] 92
    $quote = [char] 34
    $builder = [System.Text.StringBuilder]::new()
    $null = $builder.Append($quote)
    $backslashCount = 0
    foreach ($character in $Argument.ToCharArray()) {
        if ($character -eq $backslash) {
            $backslashCount += 1
            continue
        }
        if ($character -eq $quote) {
            $null = $builder.Append($backslash, ($backslashCount * 2) + 1)
            $null = $builder.Append($quote)
            $backslashCount = 0
            continue
        }
        $null = $builder.Append($backslash, $backslashCount)
        $backslashCount = 0
        $null = $builder.Append($character)
    }
    $null = $builder.Append($backslash, $backslashCount * 2)
    $null = $builder.Append($quote)
    return $builder.ToString()
}

$nativeArguments = @(
    $arguments | ForEach-Object {
        Convert-ToWindowsProcessArgument -Argument $_
    }
)
$childProcess = $null
Push-Location -LiteralPath $workingDirectory
try {
    try {
        $childProcess = Start-Process `
            -FilePath $targetPath `
            -ArgumentList $nativeArguments `
            -WorkingDirectory $workingDirectory `
            -PassThru `
            -WindowStyle Hidden `
            -RedirectStandardOutput $standardOutputPath `
            -RedirectStandardError $standardErrorPath
        $childProcess.WaitForExit()
        $exitCode = $childProcess.ExitCode
        $commandSucceeded = $exitCode -eq 0
    }
    catch {
        [System.IO.File]::AppendAllText(
            $standardErrorPath,
            ($_.Exception.ToString() + [Environment]::NewLine),
            [System.Text.UTF8Encoding]::new($false)
        )
        $commandSucceeded = $false
        $exitCode = 1
    }
}
finally {
    Pop-Location
    if ($null -ne $childProcess) {
        $childProcess.Dispose()
    }
}
if ($null -eq $exitCode) {
    $exitCode = if ($commandSucceeded) { 0 } else { 1 }
}
exit ([int] $exitCode)
