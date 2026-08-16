. (Join-Path $PSScriptRoot "common.ps1")

$python = Get-VenvPython
Invoke-Checked -FilePath $python -ArgumentList @(
    "-m", "mypy", "services/api/src"
)
Invoke-Checked -FilePath "npm" -ArgumentList @(
    "run", "typecheck", "--workspace", "apps/web"
)
