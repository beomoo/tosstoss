param(
    [switch] $Check
)

. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
$repoRoot = Get-RepoRoot
Assert-NoProjectPythonBytecode
$outputPath = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "contracts\openapi.json")
)
Assert-SafeRepositoryPath -Path $outputPath

if ($Check) {
    $temporaryDirectory = New-TaskTempDirectory
    try {
        $candidatePath = Join-Path $temporaryDirectory "openapi.json"
        Invoke-Checked `
            -FilePath $python `
            -ArgumentList (Get-GuardedPythonModuleArguments `
                -Module "toss_dashboard_api.openapi_export" `
                -ArgumentList @("--output", $candidatePath))
        if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
            throw "Committed OpenAPI snapshot is missing: $outputPath"
        }
        $expectedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputPath).Hash
        $candidateHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $candidatePath).Hash
        if ($expectedHash -ne $candidateHash) {
            throw "OpenAPI snapshot drift detected. Run scripts/export-openapi.ps1."
        }
        Invoke-Checked -FilePath "npm" -ArgumentList @(
            "run", "check:api", "--workspace", "apps/web"
        )
    }
    finally {
        Remove-TaskTempDirectory -Path $temporaryDirectory
    }
}
else {
    $outputDirectory = Split-Path -Parent $outputPath
    $generatedTypesDirectory = [System.IO.Path]::GetFullPath(
        (Join-Path $repoRoot "apps\web\src\types")
    )
    foreach ($directory in @($outputDirectory, $generatedTypesDirectory)) {
        Assert-SafeRepositoryPath -Path $directory
        if (Test-Path -LiteralPath $directory -PathType Container) {
            Assert-NoReparsePointsInTree -Path $directory -RejectHardLinks
        }
    }
    [System.IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
    Assert-SafeRepositoryPath -Path $outputDirectory
    Assert-SafeMutableRepositoryFile -Path $outputPath
    Invoke-Checked `
        -FilePath $python `
        -ArgumentList (Get-GuardedPythonModuleArguments `
            -Module "toss_dashboard_api.openapi_export" `
            -ArgumentList @("--output", $outputPath))
    Assert-SafeMutableRepositoryFile -Path $outputPath
    Invoke-Checked -FilePath "npm" -ArgumentList @(
        "run", "generate:api", "--workspace", "apps/web"
    )
    Assert-NoReparsePointsInTree -Path $generatedTypesDirectory -RejectHardLinks
}
