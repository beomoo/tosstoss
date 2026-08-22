. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-RepoRoot
$scopedRoots = @(
    (Join-Path $repoRoot "services\api"),
    (Join-Path $repoRoot "apps\web"),
    (Join-Path $repoRoot "tests"),
    (Join-Path $repoRoot "scripts")
) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }

$sourceFiles = foreach ($root in $scopedRoots) {
    Get-ChildItem -LiteralPath $root -Recurse -File |
        Where-Object {
            $_.FullName -notmatch '[\\/](node_modules|\.next|playwright-report|test-results|__pycache__)[\\/]' -and
            $_.Name -ne "next-env.d.ts" -and
            $_.FullName -ne $PSCommandPath
        }
}
$runtimeSourceFiles = @(
    $sourceFiles | Where-Object { $_.FullName -notmatch '[\\/]tests?[\\/]' }
)

function Assert-NoPattern {
    param(
        [Parameter(Mandatory = $true)][string] $Pattern,
        [Parameter(Mandatory = $true)][string] $Message,
        [System.IO.FileInfo[]] $Files = $sourceFiles
    )

    if (-not $Files -or $Files.Count -eq 0) {
        throw "Policy scan received an empty file scope."
    }
    $hits = $Files | Select-String -Pattern $Pattern
    if ($hits) {
        $hits | Select-Object Path, LineNumber | Format-Table -AutoSize | Out-Host
        throw $Message
    }
}

function Get-NodeDependencyNames {
    param([Parameter(Mandatory = $true)][object] $Manifest)

    $names = @()
    foreach ($sectionName in @(
        "dependencies", "devDependencies", "optionalDependencies", "peerDependencies"
    )) {
        if ($Manifest -is [System.Collections.IDictionary]) {
            if (-not $Manifest.Contains($sectionName) -or $null -eq $Manifest[$sectionName]) {
                continue
            }
            $names += @($Manifest[$sectionName].Keys)
        }
        else {
            $section = $Manifest.PSObject.Properties[$sectionName]
            if ($null -eq $section -or $null -eq $section.Value) {
                continue
            }
            $names += @($section.Value.PSObject.Properties.Name)
        }
    }
    return @($names | Sort-Object -Unique)
}

function Assert-NodeDependencySpecifiers {
    param(
        [Parameter(Mandatory = $true)][object] $Manifest,
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary] $AllowedSpecifiers
    )

    $invalid = $false
    foreach ($sectionName in @(
        "dependencies", "devDependencies", "optionalDependencies", "peerDependencies"
    )) {
        $entries = if ($Manifest -is [System.Collections.IDictionary]) {
            if (-not $Manifest.Contains($sectionName) -or $null -eq $Manifest[$sectionName]) {
                continue
            }
            $Manifest[$sectionName].GetEnumerator()
        }
        else {
            $section = $Manifest.PSObject.Properties[$sectionName]
            if ($null -eq $section -or $null -eq $section.Value) {
                continue
            }
            $section.Value.PSObject.Properties | ForEach-Object {
                [pscustomobject]@{ Key = $_.Name; Value = $_.Value }
            }
        }
        foreach ($entry in $entries) {
            $name = [string] $entry.Key
            $specifier = $entry.Value
            if (
                -not $AllowedSpecifiers.Contains($name) -or
                $specifier -isnot [string] -or
                $specifier -cne [string] $AllowedSpecifiers[$name]
            ) {
                $invalid = $true
            }
        }
    }
    if ($invalid) {
        [pscustomobject]@{ Path = $Path; LineNumber = 1 } |
            Format-Table -AutoSize |
            Out-Host
        throw "A Node dependency uses an unapproved package or specifier."
    }
}

function Read-JsonFile {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [switch] $AsHashtable
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required policy manifest is missing: $Path"
    }
    try {
        if ($AsHashtable) {
            $document = Get-Content -LiteralPath $Path -Raw |
                ConvertFrom-Json -AsHashtable -ErrorAction Stop
        }
        else {
            $document = Get-Content -LiteralPath $Path -Raw |
                ConvertFrom-Json -ErrorAction Stop
        }
        return $document
    }
    catch {
        throw "Policy manifest is not valid JSON: $Path"
    }
}

function New-OrdinalIgnoreCaseSet {
    param([string[]] $Values = @())

    $set = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($value in $Values) {
        $null = $set.Add($value)
    }
    return ,$set
}

function Assert-DependencyAllowlist {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [string[]] $Names,
        [Parameter(Mandatory = $true)]
        [System.Collections.Generic.HashSet[string]] $Allowed
    )

    $violations = @($Names | Where-Object { -not $Allowed.Contains($_) })
    if ($violations.Count -gt 0) {
        $violations | ForEach-Object {
            [pscustomobject]@{ Path = $Path; LineNumber = 1 }
        } | Format-Table -AutoSize | Out-Host
        throw "A dependency outside the Phase 1 allowlist was found in $Path."
    }
}

$allowedNodeSpecifiers = [ordered]@{
    "next" = "16.3.1"
    "react" = "19.2.8"
    "react-dom" = "19.2.8"
    "server-only" = "0.0.1"
    "@playwright/test" = "1.57.0"
    "@testing-library/jest-dom" = "6.9.1"
    "@testing-library/react" = "16.3.1"
    "@types/node" = "24.10.1"
    "@types/react" = "19.2.7"
    "@types/react-dom" = "19.2.3"
    "@vitejs/plugin-react" = "5.1.1"
    "eslint" = "9.39.1"
    "eslint-config-next" = "16.3.1"
    "jsdom" = "27.2.0"
    "openapi-typescript" = "7.13.0"
    "typescript" = "5.9.3"
    "vitest" = "4.1.10"
}
$allowedNodeDependencies = New-OrdinalIgnoreCaseSet -Values @($allowedNodeSpecifiers.Keys)
$rootPackagePath = Join-Path $repoRoot "package.json"
$webPackagePath = Join-Path $repoRoot "apps\web\package.json"
$packageLockPath = Join-Path $repoRoot "package-lock.json"
$rootPackage = Read-JsonFile -Path $rootPackagePath
$webPackage = Read-JsonFile -Path $webPackagePath
$packageLock = Read-JsonFile -Path $packageLockPath -AsHashtable
$rootDependencyNames = @(Get-NodeDependencyNames -Manifest $rootPackage)
$webDependencyNames = @(Get-NodeDependencyNames -Manifest $webPackage)
Assert-NodeDependencySpecifiers `
    -Manifest $rootPackage `
    -Path $rootPackagePath `
    -AllowedSpecifiers $allowedNodeSpecifiers
Assert-NodeDependencySpecifiers `
    -Manifest $webPackage `
    -Path $webPackagePath `
    -AllowedSpecifiers $allowedNodeSpecifiers
Assert-DependencyAllowlist `
    -Path $rootPackagePath `
    -Names $rootDependencyNames `
    -Allowed $allowedNodeDependencies
Assert-DependencyAllowlist `
    -Path $webPackagePath `
    -Names $webDependencyNames `
    -Allowed $allowedNodeDependencies

$lockImporters = @{
    "" = $rootDependencyNames
    "apps/web" = $webDependencyNames
}
foreach ($entry in $lockImporters.GetEnumerator()) {
    $lockPackages = $packageLock["packages"]
    if (-not $lockPackages.Contains($entry.Key)) {
        throw "package-lock.json is missing the '$($entry.Key)' workspace importer."
    }
    $lockNames = @(Get-NodeDependencyNames -Manifest $lockPackages[$entry.Key])
    Assert-NodeDependencySpecifiers `
        -Manifest $lockPackages[$entry.Key] `
        -Path $packageLockPath `
        -AllowedSpecifiers $allowedNodeSpecifiers
    $expected = New-OrdinalIgnoreCaseSet -Values @($entry.Value)
    if (-not $expected.SetEquals([string[]] $lockNames)) {
        [pscustomobject]@{ Path = $packageLockPath; LineNumber = 1 } |
            Format-Table -AutoSize |
            Out-Host
        throw "package-lock.json direct dependencies do not match their package manifest."
    }
    Assert-DependencyAllowlist `
        -Path $packageLockPath `
        -Names $lockNames `
        -Allowed $allowedNodeDependencies
}

foreach ($dependencyName in $allowedNodeSpecifiers.Keys) {
    $lockKey = "node_modules/$dependencyName"
    if (-not $packageLock["packages"].Contains($lockKey)) {
        throw "package-lock.json is missing a direct dependency package entry."
    }
    $packageEntry = $packageLock["packages"][$lockKey]
    $version = [string] $allowedNodeSpecifiers[$dependencyName]
    $tarballName = ($dependencyName -split '/')[-1]
    $expectedResolved = "https://registry.npmjs.org/$dependencyName/-/$tarballName-$version.tgz"
    if (
        $packageEntry -isnot [System.Collections.IDictionary] -or
        -not $packageEntry.Contains("version") -or
        -not $packageEntry.Contains("resolved") -or
        -not $packageEntry.Contains("integrity") -or
        [string] $packageEntry["version"] -cne $version -or
        [string] $packageEntry["resolved"] -cne $expectedResolved -or
        [string] $packageEntry["integrity"] -cnotmatch '^sha512-[A-Za-z0-9+/]+={0,2}$'
    ) {
        [pscustomobject]@{ Path = $packageLockPath; LineNumber = 1 } |
            Format-Table -AutoSize |
            Out-Host
        throw "A direct Node lock entry does not match its approved registry identity."
    }
}

$python = Get-VenvPython
$pyprojectPath = Join-Path $repoRoot "pyproject.toml"
$pythonDependencyReader = @'
import json
import pathlib
import sys
import tomllib
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

document = tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
requirements = list(document.get("build-system", {}).get("requires", []))
project = document.get("project", {})
requirements.extend(project.get("dependencies", []))
for values in project.get("optional-dependencies", {}).values():
    requirements.extend(values)
records = []
for value in requirements:
    requirement = Requirement(value)
    records.append({
        "name": canonicalize_name(requirement.name),
        "specifier": str(requirement.specifier),
        "url": requirement.url,
        "extras": sorted(requirement.extras),
        "marker": str(requirement.marker) if requirement.marker is not None else None,
    })
print(json.dumps(records))
'@
$pythonDependencyJson = & $python -c $pythonDependencyReader $pyprojectPath
if ($LASTEXITCODE -ne 0) {
    throw "Unable to parse Python dependency metadata from pyproject.toml."
}
try {
    $pythonDependencyRecords = @(
        ($pythonDependencyJson -join [Environment]::NewLine) |
            ConvertFrom-Json -ErrorAction Stop
    )
}
catch {
    throw "Python dependency metadata did not produce valid JSON."
}
$allowedPythonSpecifiers = [ordered]@{
    "alembic" = "==1.16.5"
    "detect-secrets" = "==1.5.0"
    "fastapi" = "==0.116.1"
    "httpx" = "==0.28.1"
    "mypy" = "==1.17.1"
    "pydantic" = "==2.11.7"
    "pydantic-settings" = "==2.10.1"
    "pytest" = "==8.4.1"
    "pytest-socket" = "==0.7.0"
    "ruff" = "==0.12.11"
    "setuptools" = "==80.9.0"
    "sqlalchemy" = "==2.0.43"
    "typing-extensions" = "==4.14.1"
    "tzdata" = "==2025.2"
    "uvicorn" = "==0.35.0"
}
$allowedPythonDependencies = New-OrdinalIgnoreCaseSet -Values @($allowedPythonSpecifiers.Keys)
$pythonDependencyNames = @($pythonDependencyRecords | ForEach-Object { [string] $_.name })
$uniquePythonDependencies = New-OrdinalIgnoreCaseSet -Values $pythonDependencyNames
if (
    $pythonDependencyNames.Count -ne $uniquePythonDependencies.Count -or
    -not $allowedPythonDependencies.SetEquals([string[]] $pythonDependencyNames)
) {
    [pscustomobject]@{ Path = $pyprojectPath; LineNumber = 1 } |
        Format-Table -AutoSize |
        Out-Host
    throw "pyproject.toml does not match the exact Phase 1 dependency allowlist."
}
foreach ($record in $pythonDependencyRecords) {
    if (
        -not $allowedPythonSpecifiers.Contains([string] $record.name) -or
        [string] $record.specifier -cne
            [string] $allowedPythonSpecifiers[[string] $record.name] -or
        -not [string]::IsNullOrEmpty([string] $record.url) -or
        @($record.extras).Count -ne 0 -or
        -not [string]::IsNullOrEmpty([string] $record.marker)
    ) {
        [pscustomobject]@{ Path = $pyprojectPath; LineNumber = 1 } |
            Format-Table -AutoSize |
            Out-Host
        throw "A Python dependency uses an unapproved specifier, URL, extra, or marker."
    }
}
Assert-DependencyAllowlist `
    -Path $pyprojectPath `
    -Names $pythonDependencyNames `
    -Allowed $allowedPythonDependencies

$requirementsLockPath = Join-Path $repoRoot "requirements.lock"
if (-not (Test-Path -LiteralPath $requirementsLockPath -PathType Leaf)) {
    throw "requirements.lock is missing."
}
$requirementsLockLines = @(Get-Content -LiteralPath $requirementsLockPath)
$prohibitedDependencyNamePattern = '(?i)(^|[-_.])(openai(?:[-_.]agents?)?|dart[-_.]?fss|sec[-_.]?edgar[-_.]?downloader|yfinance|finnhub(?:[-_.]python)?|polygon[-_.]?api[-_.]?client|alpaca[-_.]?py)([-_.]|$)'
$lockedPythonNames = @(
    $requirementsLockLines |
        ForEach-Object {
            if ($_ -match '^([A-Za-z0-9_.-]+)==') {
                $Matches[1].ToLowerInvariant().Replace("_", "-").Replace(".", "-")
            }
        }
)
$unexpectedTopLevelLockLines = @(
    $requirementsLockLines | Where-Object {
        -not [string]::IsNullOrWhiteSpace($_) -and
        $_ -notmatch '^\s*#' -and
        $_ -notmatch '^[A-Za-z0-9_.-]+==[^\s\\]+\s+\\$' -and
        $_ -notmatch '^\s+--hash=sha256:[0-9a-fA-F]{64}(?:\s+\\)?$'
    }
)
if ($unexpectedTopLevelLockLines.Count -gt 0) {
    [pscustomobject]@{ Path = $requirementsLockPath; LineNumber = 1 } |
        Format-Table -AutoSize |
        Out-Host
    throw "requirements.lock contains an unparsed top-level requirement."
}
$allowedLockedPythonDependencies = New-OrdinalIgnoreCaseSet -Values @(
    "alembic",
    "annotated-types",
    "anyio",
    "certifi",
    "charset-normalizer",
    "click",
    "colorama",
    "detect-secrets",
    "fastapi",
    "greenlet",
    "h11",
    "httpcore",
    "httpx",
    "idna",
    "iniconfig",
    "mako",
    "markupsafe",
    "mypy",
    "mypy-extensions",
    "packaging",
    "pathspec",
    "pluggy",
    "pydantic",
    "pydantic-core",
    "pydantic-settings",
    "pygments",
    "pytest",
    "pytest-socket",
    "python-dotenv",
    "pyyaml",
    "requests",
    "ruff",
    "setuptools",
    "sqlalchemy",
    "starlette",
    "typing-extensions",
    "typing-inspection",
    "tzdata",
    "urllib3",
    "uvicorn"
)
$uniqueLockedPythonDependencies = New-OrdinalIgnoreCaseSet -Values $lockedPythonNames
if (
    $lockedPythonNames.Count -ne $uniqueLockedPythonDependencies.Count -or
    -not $allowedLockedPythonDependencies.SetEquals([string[]] $lockedPythonNames) -or
    $lockedPythonNames | Where-Object { $_ -match $prohibitedDependencyNamePattern }
) {
    [pscustomobject]@{ Path = $requirementsLockPath; LineNumber = 1 } |
        Format-Table -AutoSize |
        Out-Host
    throw "requirements.lock does not match the exact Phase 1 dependency allowlist."
}

$nonLocalBindPattern = '(?i)(?<![0-9])0\.0\.0\.0(?![0-9])|(?:allow_origins|cors_origins)\s*=\s*[\[\(]\s*["'']\*["'']'
$prohibitedExecutionPattern = '(?i)(/(?:api/)?[A-Za-z0-9_/-]*(?:orders?|accounts?|brokerage|trades?)\b|\b(?:execute|place|submit|send|create|buy|sell)[_-]?(?:trade|order)\b|\b(?:broker(?:age)?|orders?|trades?|accounts?|order[_-]?(?:client|service|api|sdk)|trade[_-]?(?:client|service|api|sdk))(?:\s*\??\.\s*[a-z_][a-z0-9_]*){0,2}\s*\??\.\s*(?:create|place|submit|send|execute|buy|sell)\b)'
if ('@("--host", "0.0.0.0")' -notmatch $nonLocalBindPattern) {
    throw "Policy self-test failed to detect an array-form non-local bind."
}
foreach ($canary in @(
    '"/brokerage/trades"',
    "submitOrder",
    "broker.orders.create()",
    "orderClient.place()"
)) {
    if ($canary -notmatch $prohibitedExecutionPattern) {
        throw "Policy self-test failed to detect a prohibited execution canary."
    }
}
if ($allowedPythonDependencies.Contains("openai-agents")) {
    throw "Policy self-test found a prohibited dependency in the allowlist."
}

Assert-NoPattern `
    -Pattern '(?i)https?://(?!(?:127\.0\.0\.1|localhost|example\.invalid)(?=[:/"''\s]|$))(?:[a-z0-9]|\[)' `
    -Message "A non-local URL was found in Phase 1 source."
Assert-NoPattern `
    -Pattern '(?i)(next/font/google|fonts\.(googleapis|gstatic)\.com|navigator\.sendBeacon|\bgtag\s*\(|\bdataLayer\b|@vercel/(analytics|speed-insights)|posthog-js|mixpanel-browser|@segment/analytics-next|@amplitude/analytics-browser|react-ga4|next-plausible|@sentry/nextjs)' `
    -Message "A remote font, analytics, or telemetry integration was found."
Assert-NoPattern `
    -Pattern '(?i)(pytest\.mark\.skip|pytest\.skip|xfail|describe\.skip|it\.skip|test\.skip|test\.todo|test\.fixme)' `
    -Message "A skipped, todo, fixme, or xfail test was found." `
    -Files ($sourceFiles | Where-Object {
        $_.FullName -match '[\\/](tests?|__tests__)[\\/]|\.test\.|\.spec\.'
    })
Assert-NoPattern `
    -Pattern '(?i)\bNEXT_PUBLIC_[A-Z0-9_]+' `
    -Message "A NEXT_PUBLIC variable was found in Phase 1 runtime source." `
    -Files $runtimeSourceFiles
Assert-NoPattern `
    -Pattern $nonLocalBindPattern `
    -Message "A non-local bind or wildcard setting was found." `
    -Files $runtimeSourceFiles
Assert-NoPattern `
    -Pattern $prohibitedExecutionPattern `
    -Message "A prohibited order, account, brokerage, or trade execution path was found." `
    -Files $runtimeSourceFiles

Write-Host "Phase 1 scope policy scan passed."
