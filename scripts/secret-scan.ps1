. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = [System.IO.Path]::GetFullPath((Get-RepoRoot))
$scanner = Join-Path $repoRoot ".venv\Scripts\detect-secrets.exe"
if (-not (Test-Path -LiteralPath $scanner -PathType Leaf)) {
    throw "detect-secrets is not installed. Run scripts/setup.ps1 first."
}

$webRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "apps\web"))
$nextRoot = [System.IO.Path]::GetFullPath((Join-Path $webRoot ".next"))
$buildIdPath = [System.IO.Path]::GetFullPath((Join-Path $nextRoot "BUILD_ID"))
$nextStaticRoot = [System.IO.Path]::GetFullPath((Join-Path $nextRoot "static"))
$nextServerRoot = [System.IO.Path]::GetFullPath((Join-Path $nextRoot "server"))
$runtimeRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "var"))
$sentinelPath = [System.IO.Path]::GetFullPath(
    (Join-Path $runtimeRoot "phase-01-build-sentinel.txt")
)
$buildEvidencePath = [System.IO.Path]::GetFullPath(
    (Join-Path $runtimeRoot "phase-01-build-evidence.json")
)
$logRoot = [System.IO.Path]::GetFullPath((Join-Path $runtimeRoot "logs"))
$e2eApiLog = [System.IO.Path]::GetFullPath(
    (Join-Path $logRoot "phase-01-e2e-api.jsonl")
)
$e2eWebLog = [System.IO.Path]::GetFullPath(
    (Join-Path $logRoot "phase-01-e2e-web.log")
)
$playwrightReportRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $webRoot "playwright-report")
)
$playwrightResultsRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $webRoot "test-results")
)
$playwrightArtifactRoots = @($playwrightReportRoot, $playwrightResultsRoot)
$textArtifactExtensions = @(
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".json", ".jsonl", ".map",
    ".html", ".txt", ".log", ".css", ".xml", ".har", ".trace", ".network",
    ".toml", ".yaml", ".yml"
)
$sensitivePattern = '(?i)(sk-(?:(?:live|proj|svcacct)[_-][a-z0-9_-]{20,}|[a-z0-9]{32,})|github_pat_[a-z0-9_]{20,}|gh[pousr]_[a-z0-9]{20,}|glpat-[a-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._-]{20,}|eyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{10,})'
$script:AllowedArtifactSecretHashes = @{}

function Get-Sha1Hex {
    param([Parameter(Mandatory = $true)][string] $Value)

    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        return [System.Convert]::ToHexString($sha1.ComputeHash($bytes)).ToLowerInvariant()
    }
    finally {
        $sha1.Dispose()
    }
}

function Add-AllowedArtifactSecret {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Value,
        [ValidateRange(0, [int]::MaxValue)][int] $LineNumber = 0
    )

    $key = [System.IO.Path]::GetFullPath($Path).ToLowerInvariant()
    if (-not $script:AllowedArtifactSecretHashes.ContainsKey($key)) {
        $script:AllowedArtifactSecretHashes[$key] =
            [System.Collections.Generic.HashSet[string]]::new(
                [System.StringComparer]::OrdinalIgnoreCase
            )
    }
    $lineKey = if ($LineNumber -gt 0) { [string] $LineNumber } else { "*" }
    $findingKey = [string]::Concat($lineKey, "|", (Get-Sha1Hex -Value $Value))
    $null = $script:AllowedArtifactSecretHashes[$key].Add($findingKey)
}

function Get-JsonSha256Values {
    param([AllowNull()][object] $Node)

    if ($null -eq $Node -or $Node -is [string]) {
        return
    }
    if ($Node -is [pscustomobject]) {
        foreach ($property in $Node.PSObject.Properties) {
            if (
                $property.Name -eq "sha256" -and
                $property.Value -is [string] -and
                $property.Value -cmatch '^[0-9a-f]{64}$'
            ) {
                $property.Value
            }
            Get-JsonSha256Values -Node $property.Value
        }
        return
    }
    if ($Node -is [System.Collections.IDictionary]) {
        foreach ($entry in $Node.GetEnumerator()) {
            if (
                [string] $entry.Key -eq "sha256" -and
                $entry.Value -is [string] -and
                $entry.Value -cmatch '^[0-9a-f]{64}$'
            ) {
                $entry.Value
            }
            Get-JsonSha256Values -Node $entry.Value
        }
        return
    }
    if ($Node -is [System.Collections.IEnumerable]) {
        foreach ($item in $Node) {
            Get-JsonSha256Values -Node $item
        }
    }
}

function Add-StructuredSha256Exceptions {
    param([Parameter(Mandatory = $true)][string] $Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return
    }
    try {
        $json = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "A structured SHA-256 manifest is not valid JSON: $Path"
    }
    $lines = @(Get-Content -LiteralPath $Path)
    foreach ($value in @(Get-JsonSha256Values -Node $json)) {
        $propertyPattern = '"sha256"\s*:\s*"' + [regex]::Escape($value) + '"'
        $matchedProperty = $false
        for ($lineIndex = 0; $lineIndex -lt $lines.Count; $lineIndex += 1) {
            if ($lines[$lineIndex] -match $propertyPattern) {
                Add-AllowedArtifactSecret `
                    -Path $Path `
                    -Value $value `
                    -LineNumber ($lineIndex + 1)
                $matchedProperty = $true
            }
        }
        if (-not $matchedProperty) {
            throw "A structured SHA-256 value is not in an exact sha256 JSON property."
        }
    }
}

function Convert-ToScanArgument {
    param([Parameter(Mandatory = $true)][string] $Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $repoPrefix = $repoRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) +
        [System.IO.Path]::DirectorySeparatorChar
    if ($fullPath.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        return [System.IO.Path]::GetRelativePath($repoRoot, $fullPath).Replace("\", "/")
    }
    return $fullPath
}

function Invoke-DetectSecretsJson {
    param(
        [Parameter(Mandatory = $true)][string[]] $Files,
        [Parameter(Mandatory = $true)][string] $OutputPath
    )

    if ($Files.Count -eq 0) {
        throw "No files were selected for detect-secrets."
    }
    Push-Location -LiteralPath $repoRoot
    try {
        $scanOutput = & $scanner -c 1 scan --force-use-all-plugins --no-verify @Files
        if ($LASTEXITCODE -ne 0) {
            throw "detect-secrets scan failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
    [System.IO.File]::WriteAllText(
        $OutputPath,
        ($scanOutput -join [Environment]::NewLine)
    )
    try {
        $document = Get-Content -LiteralPath $OutputPath -Raw |
            ConvertFrom-Json -ErrorAction Stop
        return $document
    }
    catch {
        throw "detect-secrets did not emit valid JSON."
    }
}

function Test-AllowedArtifactFinding {
    param(
        [Parameter(Mandatory = $true)][string] $FindingPath,
        [Parameter(Mandatory = $true)][pscustomobject] $Finding
    )

    if ($Finding.type -notin @("Hex High Entropy String", "Base64 High Entropy String")) {
        return $false
    }
    if ($Finding.hashed_secret -notmatch '^[0-9a-f]{40}$') {
        return $false
    }
    $fullPath = if ([System.IO.Path]::IsPathRooted($FindingPath)) {
        [System.IO.Path]::GetFullPath($FindingPath)
    }
    else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $FindingPath))
    }
    $key = $fullPath.ToLowerInvariant()
    $findingHash = [string] $Finding.hashed_secret
    $exactFindingKey = [string]::Concat(
        [string] $Finding.line_number,
        "|",
        $findingHash
    )
    $anyLineFindingKey = [string]::Concat("*|", $findingHash)
    return (
        $script:AllowedArtifactSecretHashes.ContainsKey($key) -and
        (
            $script:AllowedArtifactSecretHashes[$key].Contains($exactFindingKey) -or
            $script:AllowedArtifactSecretHashes[$key].Contains($anyLineFindingKey)
        )
    )
}

function Assert-CurrentBuildEvidence {
    foreach ($requiredFile in @($buildIdPath, $sentinelPath, $buildEvidencePath)) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            throw "Required current-build evidence is missing: $requiredFile"
        }
    }
    $sentinelItem = Get-Item -LiteralPath $sentinelPath
    foreach ($requiredDirectory in @($nextStaticRoot, $nextServerRoot)) {
        if (-not (Test-Path -LiteralPath $requiredDirectory -PathType Container)) {
            throw "A required production build directory is missing: $requiredDirectory"
        }
        $directoryItem = Get-Item -LiteralPath $requiredDirectory -Force
        if ($directoryItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "A required production build directory cannot be a reparse point."
        }
        $artifactFiles = @(Get-ChildItem -LiteralPath $requiredDirectory -Recurse -File)
        if ($artifactFiles.Count -eq 0) {
            throw "A required production build directory is empty: $requiredDirectory"
        }
        if (@($artifactFiles | Where-Object {
            $_.LastWriteTimeUtc -lt $sentinelItem.LastWriteTimeUtc
        }).Count -gt 0) {
            throw "A required production build directory contains stale artifacts."
        }
    }

    $buildId = [System.IO.File]::ReadAllText($buildIdPath).Trim()
    $sentinel = [System.IO.File]::ReadAllText($sentinelPath).Trim()
    if ($buildId -notmatch '^[A-Za-z0-9_-]{8,128}$') {
        throw "The production BUILD_ID is empty or invalid."
    }
    if ($sentinel -notmatch '^PHASE1_RUNTIME_[0-9a-f]{32}$') {
        throw "Build sentinel evidence is empty or invalid."
    }
    $buildIdItem = Get-Item -LiteralPath $buildIdPath
    if ($buildIdItem.LastWriteTimeUtc -lt $sentinelItem.LastWriteTimeUtc) {
        throw "The production build predates the current sentinel."
    }
    try {
        $evidence = Get-Content -LiteralPath $buildEvidencePath -Raw |
            ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "The Phase 1 build evidence is not valid JSON."
    }
    $sentinelSha256 = (Get-FileHash -LiteralPath $sentinelPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if (
        $evidence.schema_version -ne 1 -or
        $evidence.build_id -ne $buildId -or
        $evidence.sentinel_sha256 -ne $sentinelSha256
    ) {
        throw "The Phase 1 build evidence does not match the current build."
    }
    $evidenceTimestamps = @{}
    foreach ($propertyName in @(
        "sentinel_written_at_utc",
        "build_id_written_at_utc",
        "completed_at_utc"
    )) {
        $parsedTimestamp = [System.DateTimeOffset]::MinValue
        $rawTimestamp = $evidence.$propertyName
        $validTimestamp = if ($rawTimestamp -is [System.DateTime]) {
            $parsedTimestamp = [System.DateTimeOffset] $rawTimestamp
            $true
        }
        else {
            [System.DateTimeOffset]::TryParse(
                [string] $rawTimestamp,
                [System.Globalization.CultureInfo]::InvariantCulture,
                [System.Globalization.DateTimeStyles]::RoundtripKind,
                [ref] $parsedTimestamp
            )
        }
        if (-not $validTimestamp -or $parsedTimestamp.Offset -ne [System.TimeSpan]::Zero) {
            throw "The Phase 1 build evidence contains an invalid UTC timestamp."
        }
        $evidenceTimestamps[$propertyName] = $parsedTimestamp.UtcDateTime
    }
    $buildEvidenceItem = Get-Item -LiteralPath $buildEvidencePath
    if (
        $evidenceTimestamps["sentinel_written_at_utc"] -ne $sentinelItem.LastWriteTimeUtc -or
        $evidenceTimestamps["build_id_written_at_utc"] -ne $buildIdItem.LastWriteTimeUtc -or
        $evidenceTimestamps["build_id_written_at_utc"] -lt
            $evidenceTimestamps["sentinel_written_at_utc"] -or
        $evidenceTimestamps["completed_at_utc"] -lt
            $evidenceTimestamps["build_id_written_at_utc"] -or
        $buildEvidenceItem.LastWriteTimeUtc -lt $evidenceTimestamps["completed_at_utc"] -or
        $evidenceTimestamps["completed_at_utc"] -gt [System.DateTime]::UtcNow.AddMinutes(5)
    ) {
        throw "The Phase 1 build evidence timestamps are stale or incoherent."
    }
    return [pscustomobject]@{
        BuildId = $buildId
        Sentinel = $sentinel
        SentinelSha256 = $sentinelSha256
        EvidenceTimestampUtc = (Get-Item -LiteralPath $buildEvidencePath).LastWriteTimeUtc
    }
}

function Assert-E2eEvidence {
    param([Parameter(Mandatory = $true)][pscustomobject] $Build)

    foreach ($requiredFile in @(
        $e2eApiLog,
        $e2eWebLog,
        (Join-Path $playwrightReportRoot "index.html"),
        (Join-Path $playwrightResultsRoot ".last-run.json")
    )) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            throw "Required E2E evidence is missing: $requiredFile"
        }
        $item = Get-Item -LiteralPath $requiredFile
        if ($item.Length -eq 0 -or $item.LastWriteTimeUtc -lt $Build.EvidenceTimestampUtc) {
            throw "E2E evidence is empty or predates the current build: $requiredFile"
        }
    }

    try {
        $lastRun = Get-Content -LiteralPath (Join-Path $playwrightResultsRoot ".last-run.json") -Raw |
            ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "Playwright last-run evidence is not valid JSON."
    }
    if ($lastRun.status -ne "passed" -or @($lastRun.failedTests).Count -ne 0) {
        throw "Playwright last-run evidence does not record a clean pass."
    }

    $apiLines = @(
        Get-Content -LiteralPath $e2eApiLog |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($apiLines.Count -eq 0) {
        throw "E2E API JSONL evidence is empty."
    }
    $markerCount = 0
    $startupCount = 0
    $requestCount = 0
    for ($lineIndex = 0; $lineIndex -lt $apiLines.Count; $lineIndex += 1) {
        $jsonDocument = $null
        try {
            $item = $apiLines[$lineIndex] | ConvertFrom-Json -ErrorAction Stop
            # ConvertFrom-Json may materialize ISO timestamps as local DateTime
            # objects. JsonDocument preserves the original string and works on
            # the repository's minimum supported PowerShell 7.4 runtime.
            $jsonDocument = [System.Text.Json.JsonDocument]::Parse(
                [string] $apiLines[$lineIndex]
            )
            $timestampText = $jsonDocument.RootElement.GetProperty("timestamp").GetString()
        }
        catch {
            throw "E2E API log contains a non-JSON line."
        }
        finally {
            if ($null -ne $jsonDocument) {
                $jsonDocument.Dispose()
            }
        }
        if ($null -eq $item -or $item -isnot [pscustomobject]) {
            throw "E2E API log lines must be JSON objects."
        }
        foreach ($requiredField in @("timestamp", "level", "logger", "event")) {
            if (
                $requiredField -notin $item.PSObject.Properties.Name -or
                [string]::IsNullOrWhiteSpace([string] $item.$requiredField)
            ) {
                throw "E2E API log line is missing the required '$requiredField' field."
            }
        }
        $timestamp = [System.DateTimeOffset]::MinValue
        if (
            $timestampText -notmatch 'Z$' -or
            -not [System.DateTimeOffset]::TryParse(
                $timestampText,
                [System.Globalization.CultureInfo]::InvariantCulture,
                [System.Globalization.DateTimeStyles]::RoundtripKind,
                [ref] $timestamp
            )
        ) {
            throw "E2E API log line has an invalid UTC timestamp."
        }
        if (
            $timestamp.Offset -ne [System.TimeSpan]::Zero -or
            $timestamp.UtcDateTime -lt $Build.EvidenceTimestampUtc -or
            $timestamp.UtcDateTime -gt [System.DateTime]::UtcNow.AddMinutes(5)
        ) {
            throw "E2E API log line is stale or has a future timestamp."
        }
        if ($item.event -eq "e2e_build_coherence") {
            $markerCount += 1
            if (
                $lineIndex -ne 0 -or
                $item.build_id -ne $Build.BuildId -or
                $item.sentinel_sha256 -ne $Build.SentinelSha256
            ) {
                throw "The E2E API build coherence marker is stale or invalid."
            }
        }
        elseif ($item.event -eq "api_started" -and $item.status -eq "ok") {
            $startupCount += 1
        }
        elseif ($item.event -eq "request_completed") {
            if (
                $item.request_id -notmatch '^[0-9a-f]{32}$' -or
                $item.method -ne "GET" -or
                $item.path -notmatch '^/' -or
                [int] $item.status_code -lt 100 -or
                [int] $item.status_code -gt 599
            ) {
                throw "An E2E API request_completed event is missing its structured schema."
            }
            # Uvicorn emits a fresh opaque request identifier for each request. Only
            # allow the exact value after this JSONL record has passed the event,
            # method, path, status, and 32-hex schema checks above.
            Add-AllowedArtifactSecret `
                -Path $e2eApiLog `
                -Value ([string] $item.request_id) `
                -LineNumber ($lineIndex + 1)
            $requestCount += 1
        }
    }
    if ($markerCount -ne 1 -or $startupCount -lt 1 -or $requestCount -lt 1) {
        throw "E2E API evidence lacks coherence, startup, or request_completed events."
    }

    $webLines = @(
        Get-Content -LiteralPath $e2eWebLog |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if (
        $webLines.Count -lt 2 -or
        $webLines[0] -ne "PHASE1_E2E_WEB_BUILD_ID=$($Build.BuildId)" -or
        -not ($webLines | Select-String -SimpleMatch "127.0.0.1:3000")
    ) {
        throw "The production web log is missing current-build startup evidence."
    }
}

function Add-NextGeneratedHashExceptions {
    foreach ($nftPath in @(
        Get-ChildItem -LiteralPath $nextRoot -Recurse -File -Filter "*.nft.json"
    )) {
        try {
            $nft = Get-Content -LiteralPath $nftPath.FullName -Raw |
                ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            throw "A Next.js file-trace manifest is not valid JSON: $($nftPath.FullName)"
        }
        $files = @($nft.files)
        $hashes = @($nft.fileHashes)
        if ($files.Count -ne $hashes.Count) {
            throw "A Next.js file-trace manifest has inconsistent files and fileHashes."
        }
        foreach ($hash in $hashes) {
            if ($hash -isnot [string] -or $hash -cnotmatch '^[0-9a-f]{32}$') {
                throw "A Next.js file-trace manifest contains an invalid file hash."
            }
            Add-AllowedArtifactSecret -Path $nftPath.FullName -Value $hash
        }
        if ("entryHash" -in $nft.PSObject.Properties.Name -and $null -ne $nft.entryHash) {
            if ($nft.entryHash -isnot [string] -or $nft.entryHash -cnotmatch '^[0-9a-f]{32}$') {
                throw "A Next.js file-trace manifest contains an invalid entry hash."
            }
            Add-AllowedArtifactSecret -Path $nftPath.FullName -Value $nft.entryHash
        }
    }
}

function Add-NextPrerenderManifestExceptions {
    $manifestPath = Join-Path $nextRoot "prerender-manifest.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "The production prerender manifest is missing."
    }
    try {
        $manifest = Get-Content -LiteralPath $manifestPath -Raw |
            ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "The production prerender manifest is not valid JSON."
    }
    if (
        $null -eq $manifest.preview -or
        $manifest.preview -isnot [pscustomobject]
    ) {
        throw "The production prerender manifest lacks its preview-key object."
    }
    $expectedProperties = @(
        "previewModeEncryptionKey",
        "previewModeId",
        "previewModeSigningKey"
    )
    $actualProperties = @($manifest.preview.PSObject.Properties.Name | Sort-Object)
    if (Compare-Object -ReferenceObject $expectedProperties -DifferenceObject $actualProperties) {
        throw "The production prerender preview-key schema is unexpected."
    }
    $previewModeId = [string] $manifest.preview.previewModeId
    $signingKey = [string] $manifest.preview.previewModeSigningKey
    $encryptionKey = [string] $manifest.preview.previewModeEncryptionKey
    if (
        $previewModeId -cnotmatch '^[0-9a-f]{32}$' -or
        $signingKey -cnotmatch '^[0-9a-f]{64}$' -or
        $encryptionKey -cnotmatch '^[0-9a-f]{64}$'
    ) {
        throw "The production prerender preview keys have invalid shapes."
    }
    foreach ($value in @($previewModeId, $signingKey, $encryptionKey)) {
        Add-AllowedArtifactSecret -Path $manifestPath -Value $value
    }
}

function Add-SentinelUnitFixtureExceptions {
    $fixturePath = Join-Path $webRoot "src\lib\runtime-boundary.test.ts"
    if (-not (Test-Path -LiteralPath $fixturePath -PathType Leaf)) {
        throw "The runtime-boundary unit-test fixture is missing."
    }
    $fixtureText = Get-Content -LiteralPath $fixturePath -Raw
    # Assemble the public dummy fixture from sub-threshold fragments so the
    # allowlist implementation does not itself become an entropy finding.
    $dummyBlock = [string]::Concat("01234567", "89abcdef")
    $dummyHex = [string]::Concat($dummyBlock, $dummyBlock)
    $fixtureValues = @(
        [string]::Concat("PHASE1_RUNTIME_", $dummyHex),
        [string]::Concat("PHASE1_RUNTIME_", $dummyHex.Substring(0, 31)),
        [string]::Concat("PHASE1_RUNTIME_", $dummyHex, "0"),
        [string]::Concat("PHASE1_RUNTIME_", $dummyHex.ToUpperInvariant()),
        [string]::Concat("phase1_runtime_", $dummyHex),
        [string]::Concat("PHASE1_RUNTIME_", $dummyHex, "\n")
    )
    foreach ($value in $fixtureValues) {
        if (-not $fixtureText.Contains(('"' + $value + '"'))) {
            throw "The runtime-boundary unit-test fixture has an unexpected shape."
        }
        Add-AllowedArtifactSecret -Path $fixturePath -Value $value
    }
}

function Add-NextEncryptionKeyExceptions {
    $manifestJsonPath = Join-Path $nextServerRoot "server-reference-manifest.json"
    $manifestJsPath = Join-Path $nextServerRoot "server-reference-manifest.js"
    foreach ($requiredPath in @($manifestJsonPath, $manifestJsPath)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw "A required Next.js server-reference manifest is missing: $requiredPath"
        }
    }
    try {
        $manifest = Get-Content -LiteralPath $manifestJsonPath -Raw |
            ConvertFrom-Json -ErrorAction Stop
        $keyBytes = [System.Convert]::FromBase64String([string] $manifest.encryptionKey)
    }
    catch {
        throw "The Next.js server-reference encryption key is invalid."
    }
    if ($keyBytes.Length -ne 32) {
        throw "The Next.js server-reference encryption key must contain exactly 32 bytes."
    }
    $encryptionKey = [string] $manifest.encryptionKey
    $manifestJs = Get-Content -LiteralPath $manifestJsPath -Raw
    if (-not $manifestJs.Contains($encryptionKey)) {
        throw "The Next.js server-reference manifests do not contain the same encryption key."
    }
    Add-AllowedArtifactSecret -Path $manifestJsonPath -Value $encryptionKey
    Add-AllowedArtifactSecret -Path $manifestJsPath -Value $encryptionKey
    # The JS wrapper escapes the closing JSON quote, and detect-secrets includes
    # that one trailing backslash in its entropy token.
    Add-AllowedArtifactSecret `
        -Path $manifestJsPath `
        -Value ([string]::Concat($encryptionKey, [char] 92))
    return [pscustomobject]@{
        Value = $encryptionKey
        AllowedPaths = @(
            [System.IO.Path]::GetFullPath($manifestJsonPath),
            [System.IO.Path]::GetFullPath($manifestJsPath)
        )
    }
}

function Expand-TraceTextArtifacts {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.IO.FileInfo[]] $Archives,
        [Parameter(Mandatory = $true)][string] $Destination,
        [Parameter(Mandatory = $true)][string] $Sentinel
    )

    [System.IO.Directory]::CreateDirectory($Destination) | Out-Null
    $strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
    $extracted = @()
    $entryIndex = 0
    $totalBytes = [int64] 0
    foreach ($traceArchive in $Archives) {
        $archive = [System.IO.Compression.ZipFile]::OpenRead($traceArchive.FullName)
        try {
            foreach ($entry in $archive.Entries) {
                if ([string]::IsNullOrEmpty($entry.Name)) {
                    continue
                }
                if ($entry.Length -gt 25MB) {
                    throw "A Playwright trace entry exceeds the 25 MiB inspection limit."
                }
                $totalBytes += $entry.Length
                if ($totalBytes -gt 200MB) {
                    throw "Playwright trace text exceeds the 200 MiB inspection limit."
                }
                $memory = [System.IO.MemoryStream]::new()
                try {
                    $entryStream = $entry.Open()
                    try {
                        $entryStream.CopyTo($memory)
                    }
                    finally {
                        $entryStream.Dispose()
                    }
                    $bytes = $memory.ToArray()
                }
                finally {
                    $memory.Dispose()
                }
                $inspectionText = [System.Text.Encoding]::UTF8.GetString($bytes)
                if ($inspectionText.Contains($Sentinel)) {
                    throw "The runtime sentinel leaked into a Playwright trace archive."
                }
                if ($inspectionText -match $sensitivePattern) {
                    throw "A high-confidence secret pattern was found in a Playwright trace archive."
                }
                try {
                    $strictText = $strictUtf8.GetString($bytes)
                }
                catch [System.Text.DecoderFallbackException] {
                    continue
                }
                if ($strictText.Contains([char] 0)) {
                    continue
                }
                $entryIndex += 1
                $destinationPath = Join-Path $Destination ("trace-{0:D6}.txt" -f $entryIndex)
                [System.IO.File]::WriteAllText($destinationPath, $strictText)
                $extracted += Get-Item -LiteralPath $destinationPath
            }
        }
        finally {
            $archive.Dispose()
        }
    }
    return $extracted
}

$tempDirectory = New-TaskTempDirectory
try {
    $build = Assert-CurrentBuildEvidence
    Assert-E2eEvidence -Build $build

    Add-AllowedArtifactSecret -Path $buildIdPath -Value $build.BuildId
    Add-AllowedArtifactSecret -Path $buildEvidencePath -Value $build.BuildId
    Add-AllowedArtifactSecret -Path $buildEvidencePath -Value $build.SentinelSha256
    Add-AllowedArtifactSecret -Path $e2eApiLog -Value $build.BuildId
    Add-AllowedArtifactSecret -Path $e2eApiLog -Value $build.SentinelSha256
    Add-AllowedArtifactSecret -Path $e2eWebLog -Value $build.BuildId
    Add-StructuredSha256Exceptions -Path (Join-Path $repoRoot "PACKAGE_MANIFEST.json")
    Add-StructuredSha256Exceptions -Path (
        Join-Path $repoRoot "qa\evidence\phase_01\evidence-manifest.json"
    )
    Add-NextGeneratedHashExceptions
    Add-NextPrerenderManifestExceptions
    Add-SentinelUnitFixtureExceptions
    $nextEncryption = Add-NextEncryptionKeyExceptions

    $entropyCanaryPath = Join-Path $tempDirectory "generic-entropy-canary.txt"
    $entropyCanaryBytes = [byte[]]::new(48)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($entropyCanaryBytes)
    $entropyCanary = [System.Convert]::ToBase64String($entropyCanaryBytes)
    [System.IO.File]::WriteAllText($entropyCanaryPath, "opaque_value = `"$entropyCanary`"")
    $canaryScan = Invoke-DetectSecretsJson `
        -Files @((Convert-ToScanArgument -Path $entropyCanaryPath)) `
        -OutputPath (Join-Path $tempDirectory "canary-scan.json")
    $canaryTypes = @(
        foreach ($property in $canaryScan.results.PSObject.Properties) {
            foreach ($finding in $property.Value) {
                $finding.type
            }
        }
    )
    if ($canaryTypes -notcontains "Base64 High Entropy String") {
        throw "detect-secrets did not reject the generated generic entropy canary."
    }

    Push-Location -LiteralPath $repoRoot
    try {
        $gitFiles = @(& git ls-files --cached --others --exclude-standard)
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to enumerate tracked and untracked repository files."
        }
    }
    finally {
        Pop-Location
    }

    $nextArtifactFiles = @(
        Get-ChildItem -LiteralPath $nextRoot -Recurse -File |
            Where-Object {
                $relative = [System.IO.Path]::GetRelativePath($nextRoot, $_.FullName)
                $topLevel = $relative.Split(
                    [System.IO.Path]::DirectorySeparatorChar,
                    [System.StringSplitOptions]::RemoveEmptyEntries
                )[0]
                $topLevel -notin @("cache", "dev") -and (
                    $_.Extension.ToLowerInvariant() -in $textArtifactExtensions -or
                    $_.Name -eq "BUILD_ID"
                )
            }
    )
    $logArtifactFiles = @(
        Get-ChildItem -LiteralPath $logRoot -Recurse -File |
            Where-Object { $_.Extension.ToLowerInvariant() -in $textArtifactExtensions }
    )
    $playwrightTextFiles = @(
        foreach ($root in $playwrightArtifactRoots) {
            Get-ChildItem -LiteralPath $root -Recurse -File |
                Where-Object { $_.Extension.ToLowerInvariant() -in $textArtifactExtensions }
        }
    )
    $qaTextFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $repoRoot "qa") -Recurse -File |
            Where-Object { $_.Extension.ToLowerInvariant() -in $textArtifactExtensions }
    )
    $ignoredEnvironmentFiles = @(
        Get-ChildItem -LiteralPath $repoRoot -Recurse -File -Force |
            Where-Object {
                $_.Name -like ".env*" -and
                $_.FullName -notmatch '[\\/](\.git|\.venv|node_modules|\.next)[\\/]'
            }
    )
    $ignoredLogFiles = @(
        Get-ChildItem -LiteralPath $repoRoot -Recurse -File -Filter "*.log" -Force |
            Where-Object {
                $_.FullName -notmatch '[\\/](\.git|\.venv|node_modules)[\\/]'
            }
    )
    $traceArchives = @(
        foreach ($root in $playwrightArtifactRoots) {
            Get-ChildItem -LiteralPath $root -Recurse -File -Filter "*.zip"
        }
    )
    $traceTextFiles = @(
        Expand-TraceTextArtifacts `
            -Archives $traceArchives `
            -Destination (Join-Path $tempDirectory "trace-text") `
            -Sentinel $build.Sentinel
    )

    $artifactFiles = @(
        $nextArtifactFiles +
        $logArtifactFiles +
        $playwrightTextFiles +
        $qaTextFiles +
        $ignoredEnvironmentFiles +
        $ignoredLogFiles +
        $traceTextFiles +
        @(Get-Item -LiteralPath $buildEvidencePath)
    )
    $artifactScanArguments = @(
        $artifactFiles |
            ForEach-Object { Convert-ToScanArgument -Path $_.FullName } |
            Where-Object { $_ } |
            Sort-Object -Unique
    )
    $scanFiles = @(
        $gitFiles + $artifactScanArguments |
            Where-Object { $_ } |
            Sort-Object -Unique
    )
    $scan = Invoke-DetectSecretsJson `
        -Files $scanFiles `
        -OutputPath (Join-Path $tempDirectory "scan.json")

    $findings = @()
    $allowedFindingCount = 0
    foreach ($property in $scan.results.PSObject.Properties) {
        foreach ($finding in $property.Value) {
            if (Test-AllowedArtifactFinding -FindingPath $property.Name -Finding $finding) {
                $allowedFindingCount += 1
                continue
            }
            $findings += [pscustomobject]@{
                Path = $property.Name
                LineNumber = $finding.line_number
                Type = $finding.type
            }
        }
    }
    if ($findings.Count -gt 0) {
        $findings | Format-Table -AutoSize | Out-Host
        throw "Secret scan found $($findings.Count) potential secret(s)."
    }
    Write-Host "Validated narrow generated-hash exceptions: $allowedFindingCount"

    $strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
    $sourceInspectionFiles = @(
        Get-ChildItem -LiteralPath $repoRoot -Recurse -File |
            Where-Object {
                $_.FullName -notmatch '[\\/](\.git|\.venv|node_modules|\.next|playwright-report|test-results|var)[\\/]'
            } |
            Where-Object {
                try {
                    $candidateText = $strictUtf8.GetString(
                        [System.IO.File]::ReadAllBytes($_.FullName)
                    )
                    return -not $candidateText.Contains([char] 0)
                }
                catch [System.Text.DecoderFallbackException] {
                    return $false
                }
            }
    )
    $inspectionFiles = @(
        $sourceInspectionFiles + $artifactFiles |
            Sort-Object -Property FullName -Unique
    )
    $patternHits = $inspectionFiles | Select-String -Pattern $sensitivePattern
    if ($patternHits) {
        $patternHits | Select-Object Path, LineNumber | Format-Table -AutoSize | Out-Host
        throw "High-confidence secret pattern detected."
    }

    $bundleHits = Get-ChildItem -LiteralPath $nextStaticRoot -Recurse -File |
        Select-String -Pattern '(?i)(CLIENT_SECRET|ACCESS_TOKEN|AUTHORIZATION|PHASE1_SERVER_ONLY_SENTINEL|NEXT_PUBLIC_[A-Z0-9_]+)'
    if ($bundleHits) {
        $bundleHits | Select-Object Path, LineNumber | Format-Table -AutoSize | Out-Host
        throw "Sensitive or NEXT_PUBLIC identifier found in the browser bundle."
    }
    $publicEnvironmentHits = $ignoredEnvironmentFiles |
        Select-String -Pattern '(?i)\bNEXT_PUBLIC_[A-Z0-9_]+'
    if ($publicEnvironmentHits) {
        $publicEnvironmentHits |
            Select-Object Path, LineNumber |
            Format-Table -AutoSize |
            Out-Host
        throw "NEXT_PUBLIC variables are prohibited in Phase 1 environment files."
    }

    $sentinelLeakFiles = @(
        Get-ChildItem -LiteralPath $nextRoot -Recurse -File |
            Where-Object {
                $relative = [System.IO.Path]::GetRelativePath($nextRoot, $_.FullName)
                $relative -notmatch '^(cache|dev)[\\/]'
            }
    )
    foreach ($root in @(
        (Join-Path $repoRoot "qa"),
        (Join-Path $repoRoot "contracts"),
        $logRoot,
        $playwrightReportRoot,
        $playwrightResultsRoot
    )) {
        $sentinelLeakFiles += @(Get-ChildItem -LiteralPath $root -Recurse -File)
    }
    $sentinelLeaks = $sentinelLeakFiles | Select-String -SimpleMatch $build.Sentinel
    if ($sentinelLeaks) {
        $sentinelLeaks | Select-Object Path, LineNumber | Format-Table -AutoSize | Out-Host
        throw "The runtime sentinel leaked into a browser or API artifact."
    }

    $encryptionLeakFiles = @(
        $sentinelLeakFiles | Where-Object {
            [System.IO.Path]::GetFullPath($_.FullName) -notin $nextEncryption.AllowedPaths
        }
    )
    $encryptionLeaks = $encryptionLeakFiles |
        Select-String -SimpleMatch $nextEncryption.Value
    if ($encryptionLeaks) {
        $encryptionLeaks | Select-Object Path, LineNumber | Format-Table -AutoSize | Out-Host
        throw "The Next.js server-reference encryption key leaked outside its manifests."
    }

    foreach ($ignoreProbe in @(".env", "apps/web/.env.local", "services/api/.env")) {
        Push-Location -LiteralPath $repoRoot
        try {
            $ignored = @(& git check-ignore --no-index $ignoreProbe 2>$null)
            if ($LASTEXITCODE -ne 0 -or $ignored -notcontains $ignoreProbe) {
                throw "A Phase 1 environment file pattern is not ignored by Git: $ignoreProbe"
            }
        }
        finally {
            Pop-Location
        }
    }
    Push-Location -LiteralPath $repoRoot
    try {
        $trackedEnvironmentFiles = @(
            & git ls-files |
                Where-Object {
                    [System.IO.Path]::GetFileName($_) -like ".env*" -and
                    [System.IO.Path]::GetFileName($_) -ne ".env.example"
                }
        )
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to inspect tracked environment files."
        }
    }
    finally {
        Pop-Location
    }
    if ($trackedEnvironmentFiles.Count -gt 0) {
        $trackedEnvironmentFiles | ForEach-Object {
            [pscustomobject]@{ Path = $_; LineNumber = 1 }
        } | Format-Table -AutoSize | Out-Host
        throw "A non-example environment file is tracked by Git."
    }

    Write-Host "Secret scan passed."
}
finally {
    Remove-TaskTempDirectory -Path $tempDirectory
}
