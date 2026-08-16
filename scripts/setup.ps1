. (Join-Path $PSScriptRoot "common.ps1")

$powerShellVersion = [System.Version]::Parse($PSVersionTable.PSVersion.ToString())
if ($powerShellVersion -lt [System.Version]"7.4.0") {
    throw "PowerShell 7.4 or newer is required. Found $powerShellVersion."
}

Assert-CommandAvailable -Name "node"
Assert-CommandAvailable -Name "npm"
Assert-CommandAvailable -Name "py"

$nodeVersionText = (& node -p "process.versions.node").Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read Node.js version."
}
$nodeVersion = [System.Version]::Parse($nodeVersionText)
if ($nodeVersion -lt [System.Version]"24.15.0" -or $nodeVersion.Major -ge 25) {
    throw "Node.js 24.15.x is required. Found $nodeVersionText."
}

$npmVersionText = (& npm --version).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read npm version."
}
$npmVersion = [System.Version]::Parse($npmVersionText)
if ($npmVersion.Major -ne 11) {
    throw "npm 11 is required. Found $npmVersionText."
}

$pythonVersionText = (& py -3.13 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))").Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.13 is required and must be available through the py launcher."
}
$pythonVersion = [System.Version]::Parse($pythonVersionText)
if ($pythonVersion -lt [System.Version]"3.13.1" -or $pythonVersion.Major -ne 3 -or $pythonVersion.Minor -ne 13) {
    throw "Python 3.13.1 or newer within the 3.13 line is required. Found $pythonVersionText."
}
Write-Host "Python $pythonVersionText"

$repoRoot = Get-RepoRoot
$tempRoot = Join-Path $repoRoot "var\tmp"
[System.IO.Directory]::CreateDirectory($tempRoot) | Out-Null
$env:TEMP = $tempRoot
$env:TMP = $tempRoot
$env:TMPDIR = $tempRoot
$env:PYTHONUTF8 = "1"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    Invoke-Checked -FilePath "py" -ArgumentList @("-3.13", "-m", "venv", "--without-pip", ".venv")
}

& $venvPython -m pip --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Invoke-Checked -FilePath $venvPython -ArgumentList @("-m", "ensurepip", "--upgrade", "--default-pip")
}

$lockPath = Join-Path $repoRoot "requirements.lock"
if (-not (Test-Path -LiteralPath $lockPath -PathType Leaf)) {
    throw "requirements.lock is missing."
}

Invoke-Checked -FilePath $venvPython -ArgumentList @(
    "-m", "pip", "install", "--disable-pip-version-check",
    "--require-hashes", "-r", $lockPath
)
Invoke-Checked -FilePath $venvPython -ArgumentList @(
    "-m", "pip", "install", "--disable-pip-version-check",
    "--no-deps", "--no-build-isolation", "-e", "."
)

$env:NEXT_TELEMETRY_DISABLED = "1"
Invoke-Checked -FilePath "npm" -ArgumentList @("ci")
Invoke-Checked -FilePath "npm" -ArgumentList @(
    "exec", "--workspace", "apps/web", "--", "playwright", "install", "chromium"
)

Write-Host "Setup completed. No external API credentials were requested."
