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
            $_.Name -ne "next-env.d.ts"
        }
}
$runtimeSourceFiles = @(
    $sourceFiles | Where-Object {
        $_.FullName -notmatch '[\\/]tests?[\\/]' -or
        $_.FullName -match '[\\/]apps[\\/]web[\\/]tests[\\/]e2e[\\/]start-(?:backend|frontend)\.ps1$'
    }
)
$prohibitedDependencyNamePattern = '(?i)(^|[-_.])(openai(?:[-_.]agents?)?|dart[-_.]?fss|sec[-_.]?edgar[-_.]?downloader|yfinance|finnhub(?:[-_.]?python)?|polygon[-_.]?api[-_.]?client|alpaca[-_.]?py)([-_.]|$)'

function Assert-NoPattern {
    param(
        [Parameter(Mandatory = $true)][string] $Pattern,
        [Parameter(Mandatory = $true)][string] $Message,
        [System.IO.FileInfo[]] $Files = $sourceFiles,
        [switch] $SuppressHitOutput
    )

    if (-not $Files -or $Files.Count -eq 0) {
        throw "Policy scan received an empty file scope."
    }
    $hits = $Files | Select-String -Pattern $Pattern
    if ($hits) {
        if (-not $SuppressHitOutput) {
            $hits | Select-Object Path, LineNumber | Format-Table -AutoSize | Out-Host
        }
        throw $Message
    }
}

function Assert-ExactStringMap {
    param(
        [Parameter(Mandatory = $true)][object] $Actual,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary] $Expected,
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if ($Actual -isnot [pscustomobject] -and $Actual -isnot [System.Collections.IDictionary]) {
        throw "$Label must be a JSON object in $Path."
    }
    $actualEntries = if ($Actual -is [System.Collections.IDictionary]) {
        @($Actual.GetEnumerator())
    }
    else {
        @($Actual.PSObject.Properties | ForEach-Object {
            [pscustomobject]@{ Key = $_.Name; Value = $_.Value }
        })
    }
    $actualNames = @($actualEntries | ForEach-Object { [string] $_.Key })
    $expectedNames = @($Expected.Keys | ForEach-Object { [string] $_ })
    if (
        $actualNames.Count -ne $expectedNames.Count -or
        (Compare-Object -CaseSensitive `
            -ReferenceObject @($expectedNames | Sort-Object) `
            -DifferenceObject @($actualNames | Sort-Object))
    ) {
        throw "$Label keys do not match the exact Phase 1 allowlist in $Path."
    }
    foreach ($entry in $actualEntries) {
        if (
            $entry.Value -isnot [string] -or
            [string] $entry.Value -cne [string] $Expected[[string] $entry.Key]
        ) {
            throw "$Label values do not match the exact Phase 1 allowlist in $Path."
        }
    }
}

function Assert-PolicyCanaryRejected {
    param(
        [Parameter(Mandatory = $true)][scriptblock] $Action,
        [Parameter(Mandatory = $true)][string] $Message
    )

    $rejected = $false
    try {
        & $Action
    }
    catch {
        $rejected = $true
    }
    if (-not $rejected) {
        throw $Message
    }
}

function Assert-PatternRejectsCanary {
    param(
        [Parameter(Mandatory = $true)][string] $Pattern,
        [Parameter(Mandatory = $true)][string] $Content,
        [Parameter(Mandatory = $true)][string] $Message
    )

    $tempDirectory = New-TaskTempDirectory
    try {
        $canaryPath = Join-Path $tempDirectory "policy-negative-canary.txt"
        [System.IO.File]::WriteAllText($canaryPath, $Content)
        $canaryFile = Get-Item -LiteralPath $canaryPath
        Assert-PolicyCanaryRejected `
            -Action {
                Assert-NoPattern `
                    -Pattern $Pattern `
                    -Message "Expected negative canary rejection." `
                    -Files @($canaryFile) `
                    -SuppressHitOutput
            } `
            -Message $Message
    }
    finally {
        Remove-TaskTempDirectory -Path $tempDirectory
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

function Assert-NodeLockPackageEntry {
    param(
        [Parameter(Mandatory = $true)][string] $LockKey,
        [Parameter(Mandatory = $true)][object] $Entry,
        [Parameter(Mandatory = $true)][string] $RegistryPrefix
    )

    if (
        $LockKey -cnotmatch
            '^node_modules/(?:@[^/]+/)?[^/]+(?:/node_modules/(?:@[^/]+/)?[^/]+)*$' -or
        $Entry -isnot [System.Collections.IDictionary]
    ) {
        throw "A Node lock package entry has an invalid shape."
    }
    $marker = "node_modules/"
    $nameOffset = $LockKey.LastIndexOf(
        $marker,
        [System.StringComparison]::Ordinal
    ) + $marker.Length
    $packageName = $LockKey.Substring($nameOffset)
    if (
        $packageName -match $prohibitedDependencyNamePattern -or
        ($Entry.Contains("name") -and [string] $Entry["name"] -cne $packageName) -or
        $Entry.Contains("link") -or
        -not $Entry.Contains("version") -or
        -not $Entry.Contains("resolved") -or
        -not $Entry.Contains("integrity")
    ) {
        throw "A Node lock package entry has an unapproved identity."
    }
    $version = [string] $Entry["version"]
    $tarballName = ($packageName -split '/')[-1]
    $expectedResolved = [string]::Concat(
        $RegistryPrefix,
        $packageName,
        "/-/",
        $tarballName,
        "-",
        $version,
        ".tgz"
    )
    if (
        $version -cnotmatch '^[0-9A-Za-z][0-9A-Za-z._+-]*$' -or
        [string] $Entry["resolved"] -cne $expectedResolved -or
        [string] $Entry["integrity"] -cnotmatch '^sha512-[A-Za-z0-9+/]+={0,2}$'
    ) {
        throw "A Node lock package entry is not pinned to its npm registry identity."
    }
    foreach ($sectionName in @(
        "dependencies", "optionalDependencies", "peerDependencies"
    )) {
        if (-not $Entry.Contains($sectionName)) {
            continue
        }
        if ($Entry[$sectionName] -isnot [System.Collections.IDictionary]) {
            throw "A Node lock dependency section has an invalid shape."
        }
        foreach ($dependency in $Entry[$sectionName].GetEnumerator()) {
            if (
                [string] $dependency.Key -match $prohibitedDependencyNamePattern -or
                [string] $dependency.Value -match
                    '(?i)^(?:https?:|git(?:\+|:)|file:|npm:|workspace:)'
            ) {
                throw "A Node lock dependency edge uses an unapproved name or source."
            }
        }
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
$allowedRootScripts = [ordered]@{
    "dev" = "npm run dev --workspace @toss-dashboard/web"
    "lint" = "npm run lint --workspace @toss-dashboard/web"
    "typecheck" = "npm run typecheck --workspace @toss-dashboard/web"
    "test" = "npm run test --workspace @toss-dashboard/web"
    "test:frontend" = "npm run test --workspace @toss-dashboard/web"
    "generate:api" = "npm run generate:api --workspace @toss-dashboard/web"
    "check:api" = "npm run check:api --workspace @toss-dashboard/web"
    "build" = "npm run build --workspace @toss-dashboard/web"
    "start" = "npm run start --workspace @toss-dashboard/web"
    "e2e" = "npm run e2e --workspace @toss-dashboard/web"
    "test:e2e" = "npm run test:e2e --workspace @toss-dashboard/web"
}
$allowedWebScripts = [ordered]@{
    "dev" = "next dev --hostname 127.0.0.1 --port 3000"
    "lint" = "eslint . --max-warnings 0"
    "typecheck" = "next typegen && tsc --noEmit"
    "test" = "vitest run"
    "test:watch" = "vitest"
    "generate:api" = "openapi-typescript ../../contracts/openapi.json --output src/types/api.generated.ts --alphabetize"
    "check:api" = "openapi-typescript ../../contracts/openapi.json --output src/types/api.generated.ts --alphabetize --check"
    "build" = "next build"
    "start" = "next start --hostname 127.0.0.1 --port 3000"
    "e2e" = "playwright test"
    "test:e2e" = "playwright test"
}
$allowedNodeDependencies = New-OrdinalIgnoreCaseSet -Values @($allowedNodeSpecifiers.Keys)
$rootPackagePath = Join-Path $repoRoot "package.json"
$webPackagePath = Join-Path $repoRoot "apps\web\package.json"
$packageLockPath = Join-Path $repoRoot "package-lock.json"
$rootPackage = Read-JsonFile -Path $rootPackagePath
$webPackage = Read-JsonFile -Path $webPackagePath
$packageLock = Read-JsonFile -Path $packageLockPath -AsHashtable
if (
    $rootPackage.name -cne "toss-invest-dashboard" -or
    $rootPackage.private -ne $true -or
    $rootPackage.packageManager -cne "npm@11.12.1" -or
    @($rootPackage.workspaces).Count -ne 1 -or
    [string] @($rootPackage.workspaces)[0] -cne "apps/web" -or
    $webPackage.name -cne "@toss-dashboard/web" -or
    $webPackage.private -ne $true
) {
    throw "The Node workspace topology does not match the exact Phase 1 contract."
}
Assert-ExactStringMap `
    -Actual $rootPackage.scripts `
    -Expected $allowedRootScripts `
    -Path $rootPackagePath `
    -Label "Root package scripts"
Assert-ExactStringMap `
    -Actual $webPackage.scripts `
    -Expected $allowedWebScripts `
    -Path $webPackagePath `
    -Label "Web package scripts"
$scriptCanary = [ordered]@{}
foreach ($entry in $allowedWebScripts.GetEnumerator()) {
    $scriptCanary[$entry.Key] = $entry.Value
}
$scriptCanary["build"] = "Write-Output pass"
Assert-PolicyCanaryRejected `
    -Action {
        Assert-ExactStringMap `
            -Actual $scriptCanary `
            -Expected $allowedWebScripts `
            -Path $webPackagePath `
            -Label "Web package script canary"
    } `
    -Message "The package-script policy accepted a false-green canary."
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
$registryPrefix = [string]::Concat("http", "s://registry.", "npmjs.org/")
if (
    [int] $packageLock["lockfileVersion"] -ne 3 -or
    $packageLock["requires"] -ne $true -or
    [string] $packageLock["name"] -cne "toss-invest-dashboard" -or
    [string] $packageLock["version"] -cne "0.1.0" -or
    $packageLock["packages"] -isnot [System.Collections.IDictionary]
) {
    throw "package-lock.json has an unexpected top-level schema."
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
    $expectedResolved = [string]::Concat(
        $registryPrefix,
        $dependencyName,
        "/-/",
        $tarballName,
        "-",
        $version,
        ".tgz"
    )
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

$workspaceLinkKey = "node_modules/@toss-dashboard/web"
if (-not $packageLock["packages"].Contains($workspaceLinkKey)) {
    throw "package-lock.json is missing the exact web workspace link."
}
$workspaceLink = $packageLock["packages"][$workspaceLinkKey]
if (
    $workspaceLink -isnot [System.Collections.IDictionary] -or
    $workspaceLink.Count -ne 2 -or
    [string] $workspaceLink["resolved"] -cne "apps/web" -or
    $workspaceLink["link"] -ne $true
) {
    throw "package-lock.json has an invalid web workspace link."
}
foreach ($lockEntry in $packageLock["packages"].GetEnumerator()) {
    if ($lockEntry.Key -in @("", "apps/web", $workspaceLinkKey)) {
        continue
    }
    Assert-NodeLockPackageEntry `
        -LockKey ([string] $lockEntry.Key) `
        -Entry $lockEntry.Value `
        -RegistryPrefix $registryPrefix
}

$providerPackageCanary = [string]::Concat("open", "ai-agents")
$providerCanaryEntry = [ordered]@{
    version = "1.0.0"
    resolved = [string]::Concat(
        $registryPrefix,
        $providerPackageCanary,
        "/-/",
        $providerPackageCanary,
        "-1.0.0.tgz"
    )
    integrity = [string]::Concat("sha512-", ("A" * 86), "==")
}
Assert-PolicyCanaryRejected `
    -Action {
        Assert-NodeLockPackageEntry `
            -LockKey ([string]::Concat("node_modules/", $providerPackageCanary)) `
            -Entry $providerCanaryEntry `
            -RegistryPrefix $registryPrefix
    } `
    -Message "The Node lock policy accepted a prohibited provider package canary."
$externalTarballCanary = [ordered]@{
    version = "1.0.0"
    resolved = [string]::Concat(
        "http", "s://example.invalid/fixture-package-1.0.0.tgz"
    )
    integrity = [string]::Concat("sha512-", ("A" * 86), "==")
}
Assert-PolicyCanaryRejected `
    -Action {
        Assert-NodeLockPackageEntry `
            -LockKey "node_modules/fixture-package" `
            -Entry $externalTarballCanary `
            -RegistryPrefix $registryPrefix
    } `
    -Message "The Node lock policy accepted a non-registry tarball canary."

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
$approvedRequirementsLockSha256 = [string]::Concat(
    "77c659d8", "79ecc4ed",
    "595e790b", "1af3b747",
    "353c6494", "a85d1ec8",
    "21bdf0ac", "0a1b552d"
)
$actualRequirementsLockSha256 = (
    Get-FileHash -LiteralPath $requirementsLockPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($actualRequirementsLockSha256 -cne $approvedRequirementsLockSha256) {
    throw "requirements.lock does not match the approved Phase 1 lock digest."
}
$requirementsLockLines = @(Get-Content -LiteralPath $requirementsLockPath)
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

$nonLocalUrlPattern = '(?i)(?:https?|wss?)://(?!(?:127\.0\.0\.1|localhost|example\.invalid)(?=[:/"''\s]|$))(?:[a-z0-9]|\[)|["''](?:https?|wss?)["'']\s*\+\s*["'']://'
$nonLocalBindPattern = '(?ix)(?:--host(?:name)?["'']?\s*(?:,\s*|=\s*|\s+)["'']?(?!127\.0\.0\.1(?=["''\s,\)]|$))[^\s"'',\)]+|\bhost(?:name)?\s*(?::|=(?!=))\s*["'']?(?!127\.0\.0\.1(?=["''\s,\}\)]|$))[^\s"'',\}\)]+|\blisten\s*\(\s*(?:[0-9]+\s*,\s*)?["'']?(?!127\.0\.0\.1(?=["''\s,\)]|$))[A-Za-z0-9:*\.\[\]-]+|(?<![0-9])(?!(?:127\.0\.0\.1)(?![0-9]))(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})(?:\.(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})){3}(?![0-9])|(?:allow_origins|cors_origins)\s*=\s*[\[\(]\s*["'']\*["'']|allow_origin_regex\s*=\s*["'']\.\*["''])'
$prohibitedExecutionPattern = '(?i)(["'']/api/["'']\s*\+\s*["''](?:orders?|accounts?|brokerage|trades?)|/(?:api/)?[A-Za-z0-9_/-]*(?:orders?|accounts?|brokerage|trades?)\b|\b(?:execute|place|submit|send|create|buy|sell)[_-](?:trade|order)(?:[_-][a-z0-9]+)*\b|\b(?:execute|place|submit|send|create|buy|sell)(?-i:Trade|Order)\b|\b(?:broker(?:age)?|orders?|trades?|accounts?|order[_-]?(?:client|service|api|sdk)|trade[_-]?(?:client|service|api|sdk))\s*\[\s*(?:["''$]|[A-Za-z])|\b(?:broker(?:age)?|orders?|trades?|accounts?|order[_-]?(?:client|service|api|sdk)|trade[_-]?(?:client|service|api|sdk))(?:\s*\??\.\s*[a-z_][a-z0-9_]*){0,2}\s*\??\.\s*(?:create|place|submit|send|execute|buy|sell)\b)'
$disabledTestPattern = '(?i)(\bpytest\.(?:(?:mark\.)?(?:skip|xfail)|importorskip)\b|\bunittest\.(?:skip|skipIf|skipUnless)\b|\b(?:xdescribe|xit|xtest)\s*\(|\b(?:describe|it|test)(?:\.(?:concurrent|serial|each))*\.(?:skip|todo|fixme|only|failing)\b)'
$remoteIntegrationNames = @(
    [string]::Concat("next/font/", "google"),
    [string]::Concat("fonts.google", "apis.com"),
    [string]::Concat("fonts.g", "static.com"),
    [string]::Concat("navigator.send", "Beacon"),
    [string]::Concat("g", "tag("),
    [string]::Concat("data", "Layer"),
    [string]::Concat("@vercel/", "analytics"),
    [string]::Concat("@vercel/", "speed-insights"),
    [string]::Concat("posthog", "-js"),
    [string]::Concat("mixpanel", "-browser"),
    [string]::Concat("@segment/", "analytics-next"),
    [string]::Concat("@amplitude/", "analytics-browser"),
    [string]::Concat("react-", "ga4"),
    [string]::Concat("next-", "plausible"),
    [string]::Concat("@sentry/", "nextjs")
)
$remoteIntegrationPattern = '(?i)(' + (
    @($remoteIntegrationNames | ForEach-Object { [regex]::Escape($_) }) -join '|'
) + ')'

$bindCanaries = @(
    [string]::Concat('@("--host", "', (@("0", "0", "0", "0") -join "."), '")'),
    [string]::Concat('--host ', (@("192", "168", "1", "5") -join ".")),
    [string]::Concat('--host ', (":" * 2))
)
foreach ($canary in $bindCanaries) {
    Assert-PatternRejectsCanary `
        -Pattern $nonLocalBindPattern `
        -Content $canary `
        -Message "The local-bind policy accepted a non-loopback canary."
}
$urlCanaries = @(
    [string]::Concat("w", "ss://outside.invalid/socket"),
    [string]::Concat('"w', 'ss" + "://outside.invalid/socket"')
)
foreach ($canary in $urlCanaries) {
    Assert-PatternRejectsCanary `
        -Pattern $nonLocalUrlPattern `
        -Content $canary `
        -Message "The local-URL policy accepted an external URL canary."
}
$executionCanaries = @(
    [string]::Concat("'/api/' + '", "orders'"),
    [string]::Concat("create_", "order_request"),
    [string]::Concat("bro", "ker['dynamicMethod']"),
    [string]::Concat("submit", "Order")
)
foreach ($canary in $executionCanaries) {
    Assert-PatternRejectsCanary `
        -Pattern $prohibitedExecutionPattern `
        -Content $canary `
        -Message "The execution-path policy accepted a prohibited canary."
}
$testCanaries = @(
    [string]::Concat("it.", "todo('fixture')"),
    [string]::Concat("test.concurrent.", "skip('fixture')"),
    [string]::Concat("pytest.", "importorskip('fixture')"),
    [string]::Concat("describe.", "only('fixture')")
)
foreach ($canary in $testCanaries) {
    Assert-PatternRejectsCanary `
        -Pattern $disabledTestPattern `
        -Content $canary `
        -Message "The disabled-test policy accepted a skip/focus canary."
}
$prohibitedPythonCanary = [string]::Concat("open", "ai-agents")
if ($allowedPythonDependencies.Contains($prohibitedPythonCanary)) {
    throw "Policy self-test found a prohibited dependency in the allowlist."
}

Assert-NoPattern `
    -Pattern $nonLocalUrlPattern `
    -Message "A non-local URL was found in Phase 1 source."
Assert-NoPattern `
    -Pattern $remoteIntegrationPattern `
    -Message "A remote font, analytics, or telemetry integration was found."
Assert-NoPattern `
    -Pattern $disabledTestPattern `
    -Message "A skipped, focused, todo, fixme, or xfail test was found." `
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
