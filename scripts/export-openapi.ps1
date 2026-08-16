param(
    [switch] $Check
)

. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
$repoRoot = Get-RepoRoot
$outputPath = Join-Path $repoRoot "contracts\openapi.json"

if ($Check) {
    $temporaryDirectory = New-TaskTempDirectory
    try {
        $candidatePath = Join-Path $temporaryDirectory "openapi.json"
        Invoke-Checked -FilePath $python -ArgumentList @("-m", "toss_dashboard_api.openapi_export", "--output", $candidatePath)
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
    [System.IO.Directory]::CreateDirectory((Split-Path -Parent $outputPath)) | Out-Null
    Invoke-Checked -FilePath $python -ArgumentList @("-m", "toss_dashboard_api.openapi_export", "--output", $outputPath)
    Invoke-Checked -FilePath "npm" -ArgumentList @(
        "run", "generate:api", "--workspace", "apps/web"
    )
}
