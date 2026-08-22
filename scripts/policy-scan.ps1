. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-RepoRoot
Assert-NoProjectPythonBytecode
$scopedRoots = @(
    (Join-Path $repoRoot "services\api"),
    (Join-Path $repoRoot "apps\web"),
    (Join-Path $repoRoot "tests"),
    (Join-Path $repoRoot "scripts")
) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }

function Get-PolicySourceFiles {
    param([Parameter(Mandatory = $true)][string[]] $Roots)

    $excludedDirectories = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($excludedPath in @(
        (Join-Path $repoRoot "apps\web\.next"),
        (Join-Path $repoRoot "apps\web\node_modules"),
        (Join-Path $repoRoot "apps\web\playwright-report"),
        (Join-Path $repoRoot "apps\web\test-results")
    )) {
        $null = $excludedDirectories.Add(
            [System.IO.Path]::GetFullPath($excludedPath)
        )
    }
    $nextEnvironmentPath = [System.IO.Path]::GetFullPath(
        (Join-Path $repoRoot "apps\web\next-env.d.ts")
    )
    $files = [System.Collections.Generic.List[System.IO.FileInfo]]::new()
    foreach ($root in $Roots) {
        $rootPath = [System.IO.Path]::GetFullPath($root)
        $rootItem = Get-Item -LiteralPath $rootPath -Force
        if (
            -not $rootItem.PSIsContainer -or
            ($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)
        ) {
            throw "A policy source root is missing or is a reparse point: $rootPath"
        }
        $directories = [System.Collections.Generic.Stack[string]]::new()
        $directories.Push($rootPath)
        while ($directories.Count -gt 0) {
            $directory = $directories.Pop()
            foreach ($item in Get-ChildItem -LiteralPath $directory -Force -ErrorAction Stop) {
                if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                    throw "A policy source path is a reparse point: $($item.FullName)"
                }
                if ($item.PSIsContainer) {
                    if (-not $excludedDirectories.Contains($item.FullName)) {
                        $directories.Push($item.FullName)
                    }
                    continue
                }
                if ([string] $item.LinkType -ceq "HardLink") {
                    throw "A policy source file is hard-linked: $($item.FullName)"
                }
                if ($item.FullName -ceq $nextEnvironmentPath) {
                    continue
                }
                $files.Add([System.IO.FileInfo] $item)
            }
        }
    }
    return @($files)
}
$sourceFiles = @(Get-PolicySourceFiles -Roots $scopedRoots)
$hiddenScopeCanaryDirectory = New-TaskTempDirectory
try {
    $hiddenScopeCanaryPath = Join-Path $hiddenScopeCanaryDirectory "hidden-policy.py"
    $cacheNamedCanaryDirectory = Join-Path $hiddenScopeCanaryDirectory "__pycache__"
    [System.IO.Directory]::CreateDirectory($cacheNamedCanaryDirectory) | Out-Null
    $cacheNamedCanaryPath = Join-Path $cacheNamedCanaryDirectory "policy-source.py"
    [System.IO.File]::WriteAllText($hiddenScopeCanaryPath, "value = 1")
    [System.IO.File]::WriteAllText($cacheNamedCanaryPath, "value = 2")
    $hiddenScopeCanaryItem = Get-Item -LiteralPath $hiddenScopeCanaryPath -Force
    $hiddenScopeCanaryItem.Attributes =
        $hiddenScopeCanaryItem.Attributes -bor [System.IO.FileAttributes]::Hidden
    $hiddenScopeFiles = @(
        Get-PolicySourceFiles -Roots @($hiddenScopeCanaryDirectory)
    )
    if (
        $hiddenScopeFiles.Count -ne 2 -or
        $hiddenScopeFiles.FullName -notcontains $hiddenScopeCanaryPath -or
        $hiddenScopeFiles.FullName -notcontains $cacheNamedCanaryPath
    ) {
        throw "The policy source scope omitted a hidden or cache-named source canary."
    }
}
finally {
    Remove-TaskTempDirectory -Path $hiddenScopeCanaryDirectory
}
function Test-IsRuntimePolicySourcePath {
    param([Parameter(Mandatory = $true)][string] $Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $testRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "tests"))
    $webTestRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "apps\web\tests"))
    $testRootPrefix = $testRoot.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    $webTestRootPrefix = $webTestRoot.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    if ($fullPath.StartsWith($testRootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }
    if (-not $fullPath.StartsWith(
            $webTestRootPrefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
        return $true
    }

    $approvedWebTestRuntimePaths = @(
        [System.IO.Path]::GetFullPath(
            (Join-Path $webTestRoot "e2e\start-backend.ps1")
        ),
        [System.IO.Path]::GetFullPath(
            (Join-Path $webTestRoot "e2e\start-frontend.ps1")
        )
    )
    return $approvedWebTestRuntimePaths -contains $fullPath
}

$runtimeSourceFiles = @(
    $sourceFiles | Where-Object {
        Test-IsRuntimePolicySourcePath -Path $_.FullName
    }
)
$applicationRuntimeRoots = @(
    (Join-Path $repoRoot "services\api\src"),
    (Join-Path $repoRoot "apps\web\src")
)
$applicationRuntimeSourceFiles = @(
    Get-PolicySourceFiles -Roots $applicationRuntimeRoots
)
if ($applicationRuntimeSourceFiles.Count -eq 0) {
    throw "The application runtime policy source scope is empty."
}
$runtimeScopeCanaries = @(
    @{
        Path = Join-Path $repoRoot "services\api\src\test\provider.py"
        Expected = $true
    },
    @{
        Path = Join-Path $repoRoot "apps\web\src\broker.test.ts"
        Expected = $true
    },
    @{
        Path = Join-Path $repoRoot "tests\backend\runtime_canary.py"
        Expected = $false
    },
    @{
        Path = Join-Path $repoRoot "apps\web\tests\e2e\phase-01.spec.ts"
        Expected = $false
    },
    @{
        Path = Join-Path $repoRoot "apps\web\tests\e2e\start-backend.ps1"
        Expected = $true
    }
)
foreach ($canary in $runtimeScopeCanaries) {
    $actual = Test-IsRuntimePolicySourcePath -Path $canary.Path
    if ($actual -ne $canary.Expected) {
        throw "The runtime policy source classifier accepted a path-name bypass canary."
    }
}
$openAiDependencyName = [regex]::Escape([string]::Concat("open", "ai"))
$prohibitedDependencyNamePattern = '(?i)(^|[-_./@])(?:' +
    $openAiDependencyName +
    '(?:[-_.]agents?)?|dart[-_.]?fss|sec[-_.]?edgar[-_.]?downloader|' +
    'yfinance|finnhub(?:[-_.]?python)?|polygon[-_.]?api[-_.]?client|' +
    'alpaca[-_.]?py)([-_./@]|$)'

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
            foreach ($hit in $hits) {
                Write-Host "$($hit.Path):$($hit.LineNumber)"
            }
        }
        throw $Message
    }
}

function Assert-NoRawPattern {
    param(
        [Parameter(Mandatory = $true)][string] $Pattern,
        [Parameter(Mandatory = $true)][string] $Message,
        [Parameter(Mandatory = $true)][System.IO.FileInfo[]] $Files,
        [switch] $SuppressHitOutput
    )

    if (-not $Files -or $Files.Count -eq 0) {
        throw "Raw-text policy scan received an empty file scope."
    }
    $hits = @()
    foreach ($file in $Files) {
        $text = [string] (Get-Content -LiteralPath $file.FullName -Raw)
        $match = [regex]::Match($text, $Pattern)
        if ($match.Success) {
            $lineNumber = 1 + [regex]::Matches(
                $text.Substring(0, $match.Index),
                "\r\n|\r|\n"
            ).Count
            $hits += [pscustomobject]@{
                Path = $file.FullName
                LineNumber = $lineNumber
            }
        }
    }
    if ($hits.Count -gt 0) {
        if (-not $SuppressHitOutput) {
            foreach ($hit in $hits) {
                Write-Host "$($hit.Path):$($hit.LineNumber)"
            }
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

function Assert-RawPatternRejectsCanary {
    param(
        [Parameter(Mandatory = $true)][string] $Pattern,
        [Parameter(Mandatory = $true)][string] $Content,
        [Parameter(Mandatory = $true)][string] $Message
    )

    $tempDirectory = New-TaskTempDirectory
    try {
        $canaryPath = Join-Path $tempDirectory "raw-policy-canary.txt"
        [System.IO.File]::WriteAllText($canaryPath, $Content)
        $canaryFile = Get-Item -LiteralPath $canaryPath
        Assert-PolicyCanaryRejected `
            -Action {
                Assert-NoRawPattern `
                    -Pattern $Pattern `
                    -Message "Expected raw negative canary rejection." `
                    -Files @($canaryFile) `
                    -SuppressHitOutput
            } `
            -Message $Message
    }
    finally {
        Remove-TaskTempDirectory -Path $tempDirectory
    }
}

function Assert-NoConstantStringConcatenationPattern {
    param(
        [Parameter(Mandatory = $true)][string] $Pattern,
        [Parameter(Mandatory = $true)][string] $Message,
        [Parameter(Mandatory = $true)][System.IO.FileInfo[]] $Files,
        [switch] $SuppressHitOutput
    )

    if (-not $Files -or $Files.Count -eq 0) {
        throw "Constant-concatenation policy scan received an empty file scope."
    }
    $hits = @()
    foreach ($file in $Files) {
        $text = Get-Content -LiteralPath $file.FullName -Raw
        $normalized = [regex]::Replace(
            $text,
            '["''`]\s*\+\s*["''`]',
            ""
        )
        $normalized = [regex]::Replace(
            $normalized,
            '["''`]\s+(?:[rRuUbBfF]{0,2})?["''`]',
            ""
        )
        $match = [regex]::Match($normalized, $Pattern)
        if ($match.Success) {
            $lineNumber = 1 + [regex]::Matches(
                $normalized.Substring(0, $match.Index),
                "\r\n|\r|\n"
            ).Count
            $hits += [pscustomobject]@{
                Path = $file.FullName
                LineNumber = $lineNumber
            }
        }
    }
    if ($hits.Count -gt 0) {
        if (-not $SuppressHitOutput) {
            foreach ($hit in $hits) {
                Write-Host "$($hit.Path):$($hit.LineNumber)"
            }
        }
        throw $Message
    }
}

function Assert-NormalizedPatternRejectsCanary {
    param(
        [Parameter(Mandatory = $true)][string] $Pattern,
        [Parameter(Mandatory = $true)][string] $Content,
        [Parameter(Mandatory = $true)][string] $Message
    )

    $tempDirectory = New-TaskTempDirectory
    try {
        $canaryPath = Join-Path $tempDirectory "normalized-policy-canary.txt"
        [System.IO.File]::WriteAllText($canaryPath, $Content)
        $canaryFile = Get-Item -LiteralPath $canaryPath
        Assert-PolicyCanaryRejected `
            -Action {
                Assert-NoConstantStringConcatenationPattern `
                    -Pattern $Pattern `
                    -Message "Expected normalized negative canary rejection." `
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

$hardLinkCanaryDirectory = New-TaskTempDirectory
try {
    $hardLinkCanaryTarget = Join-Path $hardLinkCanaryDirectory "target.txt"
    $hardLinkCanaryAlias = Join-Path $hardLinkCanaryDirectory "alias.txt"
    [System.IO.File]::WriteAllText($hardLinkCanaryTarget, "fixture")
    New-Item `
        -ItemType HardLink `
        -Path $hardLinkCanaryAlias `
        -Target $hardLinkCanaryTarget | Out-Null
    Assert-PolicyCanaryRejected `
        -Action {
            Assert-SafeMutableRepositoryFile -Path $hardLinkCanaryTarget
        } `
        -Message "The mutable-file path guard accepted a hard-link canary."
    Assert-PolicyCanaryRejected `
        -Action {
            Assert-NoReparsePointsInTree `
                -Path $hardLinkCanaryDirectory `
                -RejectHardLinks
        } `
        -Message "The mutable-tree path guard accepted a hard-link canary."
    $sqliteCanaryPath = Join-Path $hardLinkCanaryDirectory "fixture.db"
    $sqliteWalCanaryPath = "$sqliteCanaryPath-wal"
    New-Item `
        -ItemType HardLink `
        -Path $sqliteWalCanaryPath `
        -Target $hardLinkCanaryTarget | Out-Null
    Assert-PolicyCanaryRejected `
        -Action {
            Assert-SafeSqliteDatabaseFiles -DatabasePath $sqliteCanaryPath
        } `
        -Message "The SQLite path guard accepted a hard-linked sidecar canary."
}
finally {
    Remove-TaskTempDirectory -Path $hardLinkCanaryDirectory
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
$approvedPackageLockSha256 = [string]::Concat(
    "71abcfc0", "28cbb5e4",
    "74c35f2c", "1d3e1aab",
    "1152e61b", "87850709",
    "a808b4b4", "f3280f92"
)
$actualPackageLockSha256 = (
    Get-FileHash -LiteralPath $packageLockPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($actualPackageLockSha256 -cne $approvedPackageLockSha256) {
    throw "package-lock.json does not match the approved Phase 1 lock digest."
}
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

$providerPackageCanaries = @(
    [string]::Concat("open", "ai-agents"),
    [string]::Concat("@open", "ai/agents"),
    [string]::Concat("@open", "ai/sdk"),
    [string]::Concat("@scope/open", "ai-agents")
)
foreach ($providerPackageCanary in $providerPackageCanaries) {
    if ($providerPackageCanary -notmatch $prohibitedDependencyNamePattern) {
        throw "The prohibited provider package pattern missed a negative canary."
    }
    $providerCanaryTarballName = ($providerPackageCanary -split '/')[-1]
    $providerCanaryEntry = [ordered]@{
        version = "1.0.0"
        resolved = [string]::Concat(
            $registryPrefix,
            $providerPackageCanary,
            "/-/",
            $providerCanaryTarballName,
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
}
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

if sys.flags.isolated != 1 or not sys.dont_write_bytecode:
    raise RuntimeError("The dependency reader requires isolated, bytecode-free Python.")
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
$pythonDependencyJson = & $python -I -B -c $pythonDependencyReader $pyprojectPath
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

function Assert-ApprovedFileSha256 {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $ExpectedSha256
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    Assert-SafeRepositoryPath -Path $fullPath
    if (
        $ExpectedSha256 -cnotmatch '^[0-9a-f]{64}$' -or
        -not (Test-Path -LiteralPath $fullPath -PathType Leaf)
    ) {
        throw "An approved policy file definition is invalid."
    }
    $actualSha256 = (
        Get-FileHash -LiteralPath $fullPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($actualSha256 -cne $ExpectedSha256) {
        throw "A Phase 1 test configuration does not match its approved digest."
    }
}

function Assert-ExactRelativeFileSet {
    param(
        [Parameter(Mandatory = $true)][string[]] $Expected,
        [Parameter(Mandatory = $true)][string[]] $Actual,
        [Parameter(Mandatory = $true)][string] $Name
    )

    $expectedSet = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::Ordinal
    )
    $actualSet = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::Ordinal
    )
    foreach ($value in $Expected) {
        $null = $expectedSet.Add($value)
    }
    foreach ($value in $Actual) {
        $null = $actualSet.Add($value)
    }
    if (
        $expectedSet.Count -ne $Expected.Count -or
        $actualSet.Count -ne $Actual.Count -or
        -not $expectedSet.SetEquals($actualSet)
    ) {
        throw "$Name does not match the exact approved Phase 1 file set."
    }
}

function Get-FileSetManifestSha256 {
    param(
        [Parameter(Mandatory = $true)][System.IO.FileInfo[]] $Files
    )

    if (-not $Files -or $Files.Count -eq 0) {
        throw "A file-set digest requires at least one file."
    }
    $relativePaths = [string[]] @(
        $Files | ForEach-Object {
            [System.IO.Path]::GetRelativePath($repoRoot, $_.FullName).Replace("\", "/")
        }
    )
    [System.Array]::Sort($relativePaths, [System.StringComparer]::Ordinal)
    $records = foreach ($relativePath in $relativePaths) {
        $fullPath = [System.IO.Path]::GetFullPath(
            (Join-Path $repoRoot $relativePath.Replace("/", "\"))
        )
        Assert-SafeRepositoryPath -Path $fullPath
        $sha256 = (
            Get-FileHash -LiteralPath $fullPath -Algorithm SHA256
        ).Hash.ToLowerInvariant()
        "$relativePath`t$sha256"
    }
    $payload = [System.Text.Encoding]::UTF8.GetBytes(($records -join "`n"))
    $sha256Algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        return [System.Convert]::ToHexString(
            $sha256Algorithm.ComputeHash($payload)
        ).ToLowerInvariant()
    }
    finally {
        $sha256Algorithm.Dispose()
    }
}

$approvedTestConfigurationDigests = @(
    [pscustomobject]@{
        Path = Join-Path $repoRoot "pyproject.toml"
        Sha256 = [string]::Concat(
            "11197c96", "e7316942", "e1cbb72d", "763fd01a",
            "8b763599", "f82a578d", "9f21675e", "df11351c"
        )
    },
    [pscustomobject]@{
        Path = Join-Path $repoRoot "apps\web\vitest.config.ts"
        Sha256 = [string]::Concat(
            "b8be2da4", "0a9d828e", "c12534fe", "04823f10",
            "d169cc87", "5e28f74b", "62cf0c65", "0133c546"
        )
    },
    [pscustomobject]@{
        Path = Join-Path $repoRoot "apps\web\playwright.config.ts"
        Sha256 = [string]::Concat(
            "06833529", "ead8b7e9", "d821a0eb", "4c30a32f",
            "c6209bd7", "6277dfc0", "d544b85c", "74688210"
        )
    },
    [pscustomobject]@{
        Path = Join-Path $repoRoot "apps\web\vitest.setup.ts"
        Sha256 = [string]::Concat(
            "9b328c48", "43431fa7", "6d8de000", "08fc159e",
            "95f99a84", "0211085f", "f3b8f25e", "53d14409"
        )
    },
    [pscustomobject]@{
        Path = Join-Path $repoRoot "tests\backend\conftest.py"
        Sha256 = [string]::Concat(
            "e8361296", "45eec16a", "4d4e4287", "c1c80d51",
            "17380b62", "6acf9bbc", "8efbb834", "2d504ece"
        )
    }
)
foreach ($configuration in $approvedTestConfigurationDigests) {
    Assert-ApprovedFileSha256 `
        -Path $configuration.Path `
        -ExpectedSha256 $configuration.Sha256
}
$competingPytestConfigurations = @(
    "pytest.ini",
    ".pytest.ini",
    "tox.ini",
    "setup.cfg"
) | ForEach-Object { Join-Path $repoRoot $_ }
if (@($competingPytestConfigurations | Where-Object {
    Test-Path -LiteralPath $_
}).Count -gt 0) {
    throw "A competing root-level pytest configuration is prohibited."
}

$expectedBackendTestFiles = @(
    "tests/backend/test_api_analysis_packet.py",
    "tests/backend/test_api_companies.py",
    "tests/backend/test_api_data_quality.py",
    "tests/backend/test_api_error_contract.py",
    "tests/backend/test_api_health_status.py",
    "tests/backend/test_contract_decimal.py",
    "tests/backend/test_contract_ids_hashes.py",
    "tests/backend/test_contract_nonempty_strings.py",
    "tests/backend/test_contract_null_enum.py",
    "tests/backend/test_contract_required_fields.py",
    "tests/backend/test_contract_roundtrip.py",
    "tests/backend/test_contract_time.py",
    "tests/backend/test_error_isolation.py",
    "tests/backend/test_fixture_import.py",
    "tests/backend/test_logging_redaction.py",
    "tests/backend/test_migrations.py",
    "tests/backend/test_no_external_network.py",
    "tests/backend/test_openapi_snapshot.py",
    "tests/backend/test_rejection_matrix.py",
    "tests/backend/test_repositories.py",
    "tests/backend/test_settings_security.py",
    "tests/backend/test_temp_cleanup.py",
    "tests/backend/test_uvicorn_runtime_logging.py"
)
$actualBackendTestFiles = @(
    Get-ChildItem -LiteralPath (Join-Path $repoRoot "tests\backend") `
        -Recurse -File -Force -Filter "test_*.py" |
        ForEach-Object {
            [System.IO.Path]::GetRelativePath($repoRoot, $_.FullName).Replace("\", "/")
        }
)
Assert-ExactRelativeFileSet `
    -Expected $expectedBackendTestFiles `
    -Actual $actualBackendTestFiles `
    -Name "Backend test source"

$expectedFrontendTestFiles = @(
    "apps/web/src/components/AppShell.test.tsx",
    "apps/web/src/components/CompanyOverview.test.tsx",
    "apps/web/src/components/DataField.test.tsx",
    "apps/web/src/components/DataQualityGrid.test.tsx",
    "apps/web/src/components/FixtureBanner.test.tsx",
    "apps/web/src/components/StatePanel.test.tsx",
    "apps/web/src/lib/format.test.ts",
    "apps/web/src/lib/issuer-id.test.ts",
    "apps/web/src/lib/runtime-boundary.test.ts",
    "apps/web/src/lib/safe-url.test.ts"
)
$actualFrontendTestFiles = @(
    Get-ChildItem -LiteralPath (Join-Path $repoRoot "apps\web\src") `
        -Recurse -File -Force |
        Where-Object { $_.Name -match '\.test\.(?:ts|tsx)$' } |
        ForEach-Object {
            [System.IO.Path]::GetRelativePath($repoRoot, $_.FullName).Replace("\", "/")
        }
)
Assert-ExactRelativeFileSet `
    -Expected $expectedFrontendTestFiles `
    -Actual $actualFrontendTestFiles `
    -Name "Frontend unit test source"

$expectedE2eTestFiles = @("apps/web/tests/e2e/phase-01.spec.ts")
$actualE2eTestFiles = @(
    Get-ChildItem -LiteralPath (Join-Path $repoRoot "apps\web\tests\e2e") `
        -Recurse -File -Force |
        Where-Object { $_.Name -match '\.spec\.(?:ts|tsx)$' } |
        ForEach-Object {
            [System.IO.Path]::GetRelativePath($repoRoot, $_.FullName).Replace("\", "/")
        }
)
Assert-ExactRelativeFileSet `
    -Expected $expectedE2eTestFiles `
    -Actual $actualE2eTestFiles `
    -Name "Playwright test source"

$repoConftestFiles = @(
    $rootConftestPath = Join-Path $repoRoot "conftest.py"
    if (Test-Path -LiteralPath $rootConftestPath -PathType Leaf) {
        Get-Item -LiteralPath $rootConftestPath
    }
    Get-ChildItem -LiteralPath (Join-Path $repoRoot "tests") `
        -Recurse -File -Force -Filter "conftest.py"
)
$actualConftestPaths = @(
    $repoConftestFiles | ForEach-Object {
        [System.IO.Path]::GetRelativePath($repoRoot, $_.FullName).Replace("\", "/")
    }
)
Assert-ExactRelativeFileSet `
    -Expected @("tests/backend/conftest.py") `
    -Actual $actualConftestPaths `
    -Name "Pytest conftest source"

$phaseControlFiles = @(
    Get-ChildItem -LiteralPath (Join-Path $repoRoot "tests\backend") `
        -Recurse -File -Force -Filter "*.py"
    Get-ChildItem -LiteralPath (Join-Path $repoRoot "apps\web\src") `
        -Recurse -File -Force |
        Where-Object { $_.Name -match '\.test\.(?:ts|tsx)$' }
    Get-ChildItem -LiteralPath (Join-Path $repoRoot "apps\web\tests\e2e") `
        -Recurse -File -Force |
        Where-Object { $_.Extension -in @(".ps1", ".ts", ".tsx") }
    Get-ChildItem -LiteralPath (Join-Path $repoRoot "scripts") -File -Force |
        Where-Object { $_.Name -cne "policy-scan.ps1" }
)
$approvedPhaseControlDigest = [string]::Concat(
    "abb94cfb", "fa98f30e", "7217f270", "95651699",
    "2ae38509", "9815abae", "eecfb10a", "c4d44543"
)
if (
    $phaseControlFiles.Count -ne 59 -or
    (Get-FileSetManifestSha256 -Files $phaseControlFiles) -cne
        $approvedPhaseControlDigest
) {
    throw "The Phase 1 control-plane source digest does not match the approved suite."
}

$testSourceFiles = @(
    $sourceFiles | Where-Object {
        $_.FullName -match '(?i)(?:[\\/](?:tests?|__tests__)[\\/]|\.(?:test|spec)\.)'
    }
)
$testConfigurationFiles = @(
    $approvedTestConfigurationDigests | ForEach-Object {
        Get-Item -LiteralPath $_.Path
    }
)
$testPolicyFiles = @(
    @($testSourceFiles) + @($testConfigurationFiles) |
        Sort-Object FullName -Unique
)

$nonLocalUrlPattern = '(?i)(?:(?:https?|wss?)://(?!(?:127\.0\.0\.1|localhost)(?=[:/"''`\s]|$))(?:[a-z0-9]|\[)|["''`](?:https?|wss?):?["''`]\s*\+\s*["''`](?::?//)|["''`]//(?!(?:127\.0\.0\.1|localhost)(?=[:/"''`\s]|$))(?:[a-z0-9]|\[)|\burl\s*\(\s*//(?!(?:127\.0\.0\.1|localhost)(?=[:/\s\)]|$))(?:[a-z0-9]|\[)|\b(?:src|href|action|poster)\s*=\s*//(?!(?:127\.0\.0\.1|localhost)(?=[:/\s>]|$))(?:[a-z0-9]|\[))'
$nonLocalBindPattern = '(?ix)(?:--host(?:name)?["'']?\s*(?:,\s*|=\s*|\s+)["'']?(?!127\.0\.0\.1(?=["''\s,\)]|$))[^\s"'',\)]+|\bhost(?:name)?\s*(?::|=(?!=))\s*["'']?(?!127\.0\.0\.1(?=["''\s,\}\)]|$))[^\s"'',\}\)]+|\blisten\s*\(\s*(?:[0-9]+\s*,\s*)?["'']?(?!127\.0\.0\.1(?=["''\s,\)]|$))[A-Za-z0-9:*\.\[\]-]+|(?<![0-9])(?!(?:127\.0\.0\.1)(?![0-9]))(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})(?:\.(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})){3}(?![0-9])|(?:allow_origins|cors_origins)\s*=\s*[\[\(]\s*["'']\*["'']|allow_origin_regex\s*=\s*(?:r|u|f|fr|rf)?["'']\.\*["''])'
$wildcardAccessPattern = @'
(?ixs)
(?:
    \b(?:allow_origins|cors_origins|allowed_hosts|trusted_hosts)\b
    \s*(?::\s*[^=\r\n]{0,128})?\s*(?:=|:)\s*
    (?:[A-Za-z_][A-Za-z0-9_.]*\s*\([^\)]{0,128})?
    [\[\(\{][^\]\)\}]{0,512}
    ["']\s*\*\s*["']
  |
    \ballow_origin_regex\b
    \s*(?::\s*[^=\r\n]{0,128})?\s*(?:=|:)\s*
    (?:re\s*\.\s*compile\s*\(\s*)?
    (?:r|u|f|fr|rf)?["']\s*\^?\.\*\$?\s*["']\s*\)?
)
'@
$prohibitedExecutionPattern = '(?i)(["'']/api/["'']\s*\+\s*["''](?:orders?|accounts?|brokerage|trades?)|/(?:api/)?[A-Za-z0-9_/-]*(?:orders?|accounts?|brokerage|trades?)\b|\b(?:execute|place|submit|send|create|buy|sell)[_-](?:trade|order)(?:[_-][a-z0-9]+)*\b|\b(?:execute|place|submit|send|create|buy|sell)(?-i:Trade|Order)\b|\bgetattr\s*\(\s*(?:broker(?:age)?|orders?|trades?|accounts?|order[_-]?(?:client|service|api|sdk)|trade[_-]?(?:client|service|api|sdk))\b|\b(?:broker(?:age)?|orders?|trades?|accounts?|order[_-]?(?:client|service|api|sdk)|trade[_-]?(?:client|service|api|sdk))\s*\[\s*(?:["''$]|[A-Za-z])|\b(?:broker(?:age)?|orders?|trades?|accounts?|order[_-]?(?:client|service|api|sdk)|trade[_-]?(?:client|service|api|sdk))(?:\s*\??\.\s*[a-z_][a-z0-9_]*){0,2}\s*\??\.\s*(?:create|place|submit|send|execute|buy|sell)\b)'
$prohibitedProviderRuntimePattern = @'
(?imx)
(?:
    ^\s*(?:from\s+(?:openai|agents)(?:\.|\s+import\b)|import\s+(?:openai|agents)\b)
  |
    \b(?:
        from\s*|
        require\s*\(\s*|
        import\s*(?:\(\s*)?
    )["'](?:openai|@openai/)
  |
    \bOpenAI\s*\(
  |
    \bopenai\s*\.
)
'@
$prohibitedApplicationEscapePattern = @'
(?imx)
(?:
    ^\s*(?:
        from\s+(?:ctypes|_winapi|_socket|subprocess|multiprocessing)\b
      |
        import\s+(?:ctypes|_winapi|_socket|subprocess|multiprocessing)\b
      |
        from\s+os\s+import[^\r\n]*\b(?:system|popen|spawn\w*|exec\w*|startfile)\b
    )
  |
    \b(?:__import__|import_module)\s*\(\s*["']
        (?:ctypes|_winapi|_socket|subprocess|multiprocessing)["']
  |
    \b(?:ctypes|_winapi|_socket|subprocess|multiprocessing)\s*\.
  |
    \bos\s*\.\s*(?:system|popen|spawn\w*|exec\w*|startfile)\s*\(
  |
    \b(?:ctypes\s*\.\s*)?(?:WinDLL|CDLL|PyDLL)\s*\(
  |
    \b(?:from\s*|require\s*\(\s*|import\s*(?:\(\s*)?)["']
        (?:node:)?(?:child_process|worker_threads|cluster|net|dgram|dns|tls|http|https|http2)["']
  |
    \bprocess\s*(?:
        \.\s*(?:binding|_linkedBinding|getBuiltinModule)\s*\(
      |
        \[\s*["'](?:binding|_linkedBinding|getBuiltinModule)["']\s*\]\s*\(
    )
  |
    \b(?:RTCPeerConnection|webkitRTCPeerConnection|WebTransport|WebSocketStream|SharedWorker|Worker)\b
)
'@
$disabledTestPattern = @'
(?ix)
(?:
    \bpytest\s*(?:\.\s*mark)?\s*\.\s*
        (?:skip|skipif|xfail|importorskip)\b
  |
    \b(?:unittest|mark)\s*\.\s*
        (?:skip|skipif|skipunless|xfail|expectedfailure)\b
  |
    \bfrom\s+(?:pytest(?:\.mark)?|unittest)\s+import[^\r\n]*
        \b(?:skip|skipif|skipunless|xfail|importorskip|expectedfailure)\b
  |
    \b(?:import\s+(?:pytest|unittest)|from\s+pytest\s+import\s+mark)\s+as\b
  |
    \b(?:xdescribe|xit|xtest)\s*\(
  |
    \b(?:describe|suite|it|test)\b
    (?:
        \s*(?:\?\.|\.)\s*[A-Za-z_$][A-Za-z0-9_$]*
        (?:\s*\([^;{}]*\))?
    )*
    \s*(?:\?\.|\.)\s*
        (?:skip|skipif|runif|todo|fixme|only|failing|fails|fail)\b
  |
    \b(?:describe|suite|it|test)\b\s*\[\s*["']
        (?:skip|skipif|runif|todo|fixme|only|failing|fails|fail)
        ["']\s*\]
)
'@
$disabledTestConfigurationPattern = @'
(?ix)
(?:
    \b(?:passWithNoTests|testIgnore|grepInvert|hideSkippedTests|
        dangerouslyIgnoreUnhandledErrors)\b
  |
    --(?:pass-with-no-tests|last-failed|only-changed|test-list-invert)\b
  |
    \b(?:allowOnly|reuseExistingServer)\s*:\s*true\b
  |
    \bforbidOnly\s*:\s*false\b
  |
    ^\s*addopts\s*=.*(?:--ignore|--deselect|(?:^|\s)-(?:k|m)(?:\s|$))
)
'@
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
    [string]::Concat('--host ', (":" * 2)),
    [string]::Concat("allow_origin_", 'regex = r".*"')
)
foreach ($canary in $bindCanaries) {
    Assert-PatternRejectsCanary `
        -Pattern $nonLocalBindPattern `
        -Content $canary `
        -Message "The local-bind policy accepted a non-loopback canary."
}
$wildcardAccessCanaries = @(
    [string]::Concat("allowed_", 'hosts = ["', "*", '"]'),
    [string]::Concat("trusted_", 'hosts = ["', "*", '"]'),
    [string]::Concat(
        "allow_",
        'origins = ["http://127.0.0.1:3000", "',
        "*",
        '"]'
    ),
    [string]::Concat("allow_origin_", 'regex = r"^.', "*", '$"'),
    [string]::Concat("allow_origin_", 'regex = re.compile(".', "*", '")'),
    [string]::Concat("allowed_", "hosts = [`n    'safe',`n    '", "*", "'`n]")
    [string]::Concat("allow_", "origins = {'", "*", "'}")
)
foreach ($canary in $wildcardAccessCanaries) {
    Assert-RawPatternRejectsCanary `
        -Pattern $wildcardAccessPattern `
        -Content $canary `
        -Message "The wildcard host/CORS policy accepted a prohibited canary."
}
$urlCanaries = @(
    [string]::Concat("w", "ss://outside.invalid/socket"),
    [string]::Concat('"w', 'ss" + "://outside.invalid/socket"'),
    [string]::Concat(
        'httpx.get("http',
        's:" + "',
        '/',
        '/outside.invalid")'
    ),
    [string]::Concat('fetch("', '/', '/outside.invalid/path")'),
    [string]::Concat('.x{background:url(', '/', '/outside.invalid/a.png)}'),
    [string]::Concat('<img src=', '/', '/outside.invalid/a.png>')
)
foreach ($canary in $urlCanaries) {
    Assert-PatternRejectsCanary `
        -Pattern $nonLocalUrlPattern `
        -Content $canary `
        -Message "The local-URL policy accepted an external URL canary."
}
$normalizedUrlCanaries = @(
    [string]::Concat('httpx.get("h" + "tt', 'ps://outside.invalid")'),
    [string]::Concat('fetch(`w` + `s', '://outside.invalid`)'),
    [string]::Concat(
        'httpx.get("http',
        's:" "',
        '/',
        '/outside.invalid")'
    )
)
foreach ($canary in $normalizedUrlCanaries) {
    Assert-NormalizedPatternRejectsCanary `
        -Pattern $nonLocalUrlPattern `
        -Content $canary `
        -Message "The normalized URL policy accepted a split external URL canary."
}
$executionCanaries = @(
    [string]::Concat("'/api/' + '", "orders'"),
    [string]::Concat("create_", "order_request"),
    [string]::Concat("bro", "ker['dynamicMethod']"),
    [string]::Concat("getattr(bro", "ker, 'create')()"),
    [string]::Concat("submit", "Order")
)
foreach ($canary in $executionCanaries) {
    Assert-PatternRejectsCanary `
        -Pattern $prohibitedExecutionPattern `
        -Content $canary `
        -Message "The execution-path policy accepted a prohibited canary."
}
$providerRuntimeCanaries = @(
    [string]::Concat("import open", "ai"),
    [string]::Concat("from open", "ai import OpenAI"),
    [string]::Concat('import SDK from "@open', 'ai/agents"'),
    [string]::Concat('import "@open', 'ai/agents"'),
    [string]::Concat('import "open', 'ai"'),
    [string]::Concat("from agents import ", "Agent"),
    [string]::Concat("client = Open", "AI()")
)
foreach ($canary in $providerRuntimeCanaries) {
    Assert-RawPatternRejectsCanary `
        -Pattern $prohibitedProviderRuntimePattern `
        -Content $canary `
        -Message "The provider-runtime policy accepted a prohibited canary."
}
$applicationEscapeCanaries = @(
    [string]::Concat("import cty", "pes"),
    [string]::Concat("from _win", "api import CreateProcess"),
    [string]::Concat("import _sock", "et"),
    [string]::Concat("subprocess.", "Popen(command)"),
    [string]::Concat("os.", "spawnv(mode, path, args)"),
    [string]::Concat('require("node:', 'child_process")'),
    [string]::Concat('import { Worker } from "', 'worker_threads"'),
    [string]::Concat('import net from "node:', 'net"'),
    [string]::Concat('process["bind', 'ing"]("tcp_wrap")'),
    [string]::Concat('process.getBuiltin', 'Module("net")'),
    [string]::Concat("new RTCPeer", "Connection(configuration)"),
    [string]::Concat("globalThis.Web", "Transport")
    [string]::Concat("new WebSocket", "Stream(url)")
)
foreach ($canary in $applicationEscapeCanaries) {
    Assert-RawPatternRejectsCanary `
        -Pattern $prohibitedApplicationEscapePattern `
        -Content $canary `
        -Message "The application escape policy accepted a low-level bypass canary."
}
$testCanaries = @(
    [string]::Concat("it.", "todo('fixture')"),
    [string]::Concat("test.concurrent.", "skip('fixture')"),
    [string]::Concat("pytest.", "importorskip('fixture')"),
    [string]::Concat("pytest.mark.", "skipif(True, reason='fixture')"),
    [string]::Concat("suite.", "skip('fixture')"),
    [string]::Concat("test.", "skipIf(true)('fixture')"),
    [string]::Concat("test.", "fails('fixture')"),
    [string]::Concat("test.", "fail(true, 'fixture')"),
    [string]::Concat("describe.", "only('fixture')"),
    [string]::Concat("from pytest import mark; @mark.", "skip"),
    [string]::Concat("from unittest import ", "skip"),
    [string]::Concat('test["', 'skip"]("fixture")'),
    [string]::Concat("test?.", "skip('fixture')"),
    [string]::Concat("test.each(cases).", "skip('fixture')"),
    [string]::Concat("test ", ".skip('fixture')")
)
foreach ($canary in $testCanaries) {
    Assert-RawPatternRejectsCanary `
        -Pattern $disabledTestPattern `
        -Content $canary `
        -Message "The disabled-test policy accepted a skip/focus canary."
}
$testConfigurationCanaries = @(
    [string]::Concat("passWithNo", "Tests: true"),
    [string]::Concat("forbid", "Only: false"),
    [string]::Concat("reuseExisting", "Server: true"),
    [string]::Concat("--pass-with-no-", "tests")
)
foreach ($canary in $testConfigurationCanaries) {
    Assert-RawPatternRejectsCanary `
        -Pattern $disabledTestConfigurationPattern `
        -Content $canary `
        -Message "The test-configuration policy accepted a false-green canary."
}
$prohibitedPythonCanary = [string]::Concat("open", "ai-agents")
if ($allowedPythonDependencies.Contains($prohibitedPythonCanary)) {
    throw "Policy self-test found a prohibited dependency in the allowlist."
}

Assert-NoPattern `
    -Pattern $nonLocalUrlPattern `
    -Message "A non-local URL was found in Phase 1 runtime source." `
    -Files $runtimeSourceFiles
Assert-NoConstantStringConcatenationPattern `
    -Pattern $nonLocalUrlPattern `
    -Message "A constant-concatenated non-local URL was found in Phase 1 source." `
    -Files $runtimeSourceFiles
Assert-NoPattern `
    -Pattern $remoteIntegrationPattern `
    -Message "A remote font, analytics, or telemetry integration was found."
Assert-NoRawPattern `
    -Pattern $prohibitedProviderRuntimePattern `
    -Message "A prohibited provider import or call was found." `
    -Files $sourceFiles
Assert-NoRawPattern `
    -Pattern $prohibitedApplicationEscapePattern `
    -Message "A low-level process, native-network, or unmediated browser escape was found." `
    -Files $applicationRuntimeSourceFiles
Assert-NoRawPattern `
    -Pattern $disabledTestPattern `
    -Message "A skipped, focused, todo, fixme, or xfail test was found." `
    -Files $testPolicyFiles
Assert-NoRawPattern `
    -Pattern $disabledTestConfigurationPattern `
    -Message "A false-green test configuration was found." `
    -Files $testPolicyFiles
Assert-NoPattern `
    -Pattern '(?i)\bNEXT_PUBLIC_[A-Z0-9_]+' `
    -Message "A NEXT_PUBLIC variable was found in Phase 1 runtime source." `
    -Files $runtimeSourceFiles
Assert-NoPattern `
    -Pattern $nonLocalBindPattern `
    -Message "A non-local bind or wildcard setting was found." `
    -Files $runtimeSourceFiles
Assert-NoRawPattern `
    -Pattern $wildcardAccessPattern `
    -Message "A wildcard host or CORS setting was found." `
    -Files $runtimeSourceFiles
Assert-NoPattern `
    -Pattern $prohibitedExecutionPattern `
    -Message "A prohibited order, account, brokerage, or trade execution path was found." `
    -Files $runtimeSourceFiles

Write-Host "Phase 1 scope policy scan passed."
