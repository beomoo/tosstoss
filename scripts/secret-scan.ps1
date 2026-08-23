. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = [System.IO.Path]::GetFullPath((Get-RepoRoot))
$scanner = Join-Path $repoRoot ".venv\Scripts\detect-secrets.exe"
if (-not (Test-Path -LiteralPath $scanner -PathType Leaf)) {
    throw "detect-secrets is not installed. Run scripts/setup.ps1 first."
}
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$serialScanDriver = Join-Path $repoRoot "scripts\secret_scan_driver.py"
foreach ($requiredScannerFile in @($python, $serialScanDriver)) {
    if (-not (Test-Path -LiteralPath $requiredScannerFile -PathType Leaf)) {
        throw "A required secret-scan component is missing: $requiredScannerFile"
    }
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
$sensitivePattern = '(?i)(sk-(?:(?:live|proj|svcacct)[_-][a-z0-9_-]{20,}|[a-z0-9]{32,})|github_pat_[a-z0-9_]{20,}|gh[pousr]_[a-z0-9]{20,}|glpat-[a-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._-]{20,}|eyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{10,})'
$script:AllowedArtifactSecretHashes = @{}
$inlineAllowlistFilter = "detect_secrets.filters.allowlist.is_line_allowlisted"
$invalidFileFilter = "detect_secrets.filters.common.is_invalid_file"
$lockFileFilter = "detect_secrets.filters.heuristic.is_lock_file"
$nonTextFileFilter = "detect_secrets.filters.heuristic.is_non_text_file"
$swaggerFileFilter = "detect_secrets.filters.heuristic.is_swagger_file"
$prohibitedDetectSecretsFilters = @(
    $inlineAllowlistFilter,
    $invalidFileFilter,
    $lockFileFilter,
    $nonTextFileFilter,
    $swaggerFileFilter
)
$approvedBinaryExtensions = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase
)
foreach ($extension in @(
    ".7z", ".avif", ".bin", ".blob", ".bmp", ".bz2", ".class", ".db",
    ".db-journal", ".db-shm", ".db-wal", ".dll", ".dmg", ".doc", ".docx",
    ".eot", ".exe", ".gif", ".gz", ".ico", ".jar", ".jpeg", ".jpg",
    ".mo", ".node", ".pack", ".pdf", ".png", ".psd", ".pyc", ".pyd",
    ".rar", ".realm", ".s7z", ".sqlite", ".sqlite3", ".sst", ".tar",
    ".tif", ".tiff", ".ttf", ".wasm", ".webm", ".webp", ".woff",
    ".woff2", ".xls", ".xlsx", ".zip"
)) {
    $null = $approvedBinaryExtensions.Add($extension)
}
$compressedContainerExtensions = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase
)
foreach ($extension in @(
    ".7z", ".bz2", ".dmg", ".doc", ".docx", ".gz", ".jar", ".rar",
    ".s7z", ".tar", ".xls", ".xlsx", ".zip"
)) {
    $null = $compressedContainerExtensions.Add($extension)
}
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

function Get-Sha256HexFromBytes {
    param([Parameter(Mandatory = $true)][byte[]] $Bytes)

    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        return [System.Convert]::ToHexString(
            $sha256.ComputeHash($Bytes)
        ).ToLowerInvariant()
    }
    finally {
        $sha256.Dispose()
    }
}

function Add-AllowedArtifactSecret {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Value,
        [Parameter(Mandatory = $true)]
        [ValidateRange(1, [int]::MaxValue)]
        [int] $LineNumber
    )

    $key = [System.IO.Path]::GetFullPath($Path).ToLowerInvariant()
    if (-not $script:AllowedArtifactSecretHashes.ContainsKey($key)) {
        $script:AllowedArtifactSecretHashes[$key] =
            [System.Collections.Generic.HashSet[string]]::new(
                [System.StringComparer]::OrdinalIgnoreCase
            )
    }
    $findingKey = [string]::Concat(
        [string] $LineNumber,
        "|",
        (Get-Sha1Hex -Value $Value)
    )
    $null = $script:AllowedArtifactSecretHashes[$key].Add($findingKey)
}

function Add-AllowedArtifactSecretAtMatchingLines {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Value,
        [string] $SearchValue = $Value
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "An allowed secret artifact is missing: $Path"
    }
    $matchingLines = @()
    $lines = [System.IO.File]::ReadAllLines($Path)
    for ($lineIndex = 0; $lineIndex -lt $lines.Count; $lineIndex += 1) {
        if ($lines[$lineIndex].Contains($SearchValue)) {
            $matchingLines += $lineIndex + 1
        }
    }
    if ($matchingLines.Count -eq 0) {
        throw "An allowed artifact value is missing from its validated text line."
    }
    foreach ($lineNumber in $matchingLines) {
        Add-AllowedArtifactSecret `
            -Path $Path `
            -Value $Value `
            -LineNumber $lineNumber
    }
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

function Add-ValidatedEvidenceManifestExceptions {
    param([Parameter(Mandatory = $true)][string] $Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return
    }
    try {
        $manifest = Get-Content -LiteralPath $Path -Raw |
            ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "The Phase 1 evidence manifest is not valid JSON."
    }
    $records = @($manifest.files)
    if ($manifest.schema_version -ne 1 -or $records.Count -eq 0) {
        throw "The Phase 1 evidence manifest has an unexpected schema."
    }
    $evidenceRoot = [System.IO.Path]::GetFullPath(
        (Join-Path $repoRoot "qa\evidence\phase_01")
    )
    $evidencePrefix = $evidenceRoot.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    $manifestFullPath = [System.IO.Path]::GetFullPath($Path)
    $seenPaths = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    $lines = @(Get-Content -LiteralPath $Path)
    foreach ($record in $records) {
        $properties = @($record.PSObject.Properties.Name | Sort-Object)
        if (Compare-Object `
            -ReferenceObject @("path", "sha256", "size") `
            -DifferenceObject $properties) {
            throw "An evidence manifest file record has an unexpected schema."
        }
        $relativePath = [string] $record.path
        $expectedHash = [string] $record.sha256
        $expectedSize = [int64] $record.size
        if (
            [System.IO.Path]::IsPathRooted($relativePath) -or
            $relativePath.Contains("\") -or
            $relativePath -cnotmatch '^qa/evidence/phase_01/[A-Za-z0-9._/-]+$' -or
            $expectedHash -cnotmatch '^[0-9a-f]{64}$' -or
            $expectedSize -lt 0
        ) {
            throw "An evidence manifest file record is not canonical."
        }
        $targetPath = [System.IO.Path]::GetFullPath(
            (Join-Path $repoRoot $relativePath)
        )
        if (
            -not $targetPath.StartsWith(
                $evidencePrefix,
                [System.StringComparison]::OrdinalIgnoreCase
            ) -or
            [string]::Equals(
                $targetPath,
                $manifestFullPath,
                [System.StringComparison]::OrdinalIgnoreCase
            ) -or
            -not $seenPaths.Add($targetPath) -or
            -not (Test-Path -LiteralPath $targetPath -PathType Leaf)
        ) {
            throw "An evidence manifest target is missing, duplicated, or out of scope."
        }
        $targetItem = Get-Item -LiteralPath $targetPath
        $actualHash = (
            Get-FileHash -LiteralPath $targetPath -Algorithm SHA256
        ).Hash.ToLowerInvariant()
        if ($targetItem.Length -ne $expectedSize -or $actualHash -cne $expectedHash) {
            throw "An evidence manifest target does not match its recorded digest."
        }
        $propertyPattern = '"sha256"\s*:\s*"' + [regex]::Escape($expectedHash) + '"'
        $matchingLines = @(
            for ($lineIndex = 0; $lineIndex -lt $lines.Count; $lineIndex += 1) {
                if ($lines[$lineIndex] -match $propertyPattern) {
                    $lineIndex + 1
                }
            }
        )
        if ($matchingLines.Count -eq 0) {
            throw "An evidence manifest digest is missing from the JSON text."
        }
        foreach ($matchingLine in $matchingLines) {
            Add-AllowedArtifactSecret `
                -Path $Path `
                -Value $expectedHash `
                -LineNumber $matchingLine
        }
    }
    if (@(Get-JsonSha256Values -Node $manifest).Count -ne $records.Count) {
        throw "The evidence manifest contains an unvalidated SHA-256 property."
    }
}

function Add-ValidatedPackageLockExceptions {
    param([Parameter(Mandatory = $true)][string] $Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "package-lock.json is missing from the secret-scan scope."
    }
    $approvedPackageLockSha256 = [string]::Concat(
        "f5cf022d", "d418c039",
        "74095c1f", "8f703c84",
        "648a90ed", "ff7edbb2",
        "2c13fb2a", "27614a67"
    )
    $actualPackageLockSha256 = (
        Get-FileHash -LiteralPath $Path -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($actualPackageLockSha256 -cne $approvedPackageLockSha256) {
        throw "package-lock.json does not match its approved immutable digest."
    }
    $integrityCount = 0
    $lines = @(Get-Content -LiteralPath $Path)
    for ($lineIndex = 0; $lineIndex -lt $lines.Count; $lineIndex += 1) {
        if (
            $lines[$lineIndex] -match
                '"integrity"\s*:\s*"(sha512-[A-Za-z0-9+/]+={0,2})"'
        ) {
            Add-AllowedArtifactSecret `
                -Path $Path `
                -Value $Matches[1] `
                -LineNumber ($lineIndex + 1)
            $integrityCount += 1
        }
    }
    if ($integrityCount -lt 500) {
        throw "package-lock.json did not expose the expected integrity population."
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

function Assert-GitIndexMatchesWorkingTree {
    param([Parameter(Mandatory = $true)][string] $Root)

    foreach ($variableName in @(
        "GIT_INDEX_FILE",
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES"
    )) {
        if (
            (Test-Path -LiteralPath "Env:$variableName") -and
            -not [string]::IsNullOrWhiteSpace(
                [string] [Environment]::GetEnvironmentVariable($variableName)
            )
        ) {
            throw "A Git repository environment override is prohibited during the secret scan."
        }
    }
    $rootPath = [System.IO.Path]::GetFullPath($Root)
    Assert-SafeRepositoryPath -Path $rootPath
    $indexOutput = [string] (& git -C $rootPath ls-files --stage -z)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to enumerate the Git index for the secret scan."
    }
    $indexRecords = @(
        $indexOutput.Split(
            [char] 0,
            [System.StringSplitOptions]::RemoveEmptyEntries
        )
    )
    if ($indexRecords.Count -eq 0) {
        throw "The Git index is empty during the secret scan."
    }

    $rootPrefix = $rootPath.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    $seenPaths = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($record in $indexRecords) {
        $match = [regex]::Match(
            $record,
            '^(?<mode>[0-9]{6}) (?<oid>[0-9a-f]{40}|[0-9a-f]{64}) (?<stage>[0-3])\t(?<path>.*)$',
            [System.Text.RegularExpressions.RegexOptions]::Singleline
        )
        if (-not $match.Success) {
            throw "A Git index record has an unexpected shape."
        }
        $mode = $match.Groups["mode"].Value
        $objectId = $match.Groups["oid"].Value
        $stage = $match.Groups["stage"].Value
        $relativePath = $match.Groups["path"].Value
        if (
            $mode -notin @("100644", "100755") -or
            $stage -cne "0" -or
            [string]::IsNullOrEmpty($relativePath) -or
            [System.IO.Path]::IsPathRooted($relativePath) -or
            $relativePath.Contains("\")
        ) {
            throw "The Git index contains an unsupported entry."
        }
        $fullPath = [System.IO.Path]::GetFullPath(
            (Join-Path $rootPath $relativePath.Replace("/", "\"))
        )
        if (
            -not $fullPath.StartsWith(
                $rootPrefix,
                [System.StringComparison]::OrdinalIgnoreCase
            ) -or
            -not $seenPaths.Add($fullPath) -or
            -not (Test-Path -LiteralPath $fullPath -PathType Leaf)
        ) {
            throw "A Git index path is missing, duplicated, or outside the worktree."
        }
        Assert-NoReparsePointInPath -Path $fullPath
        $item = Get-Item -LiteralPath $fullPath -Force
        if (
            ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or
            [string] $item.LinkType -ceq "HardLink"
        ) {
            throw "A Git index path is linked outside the exact worktree snapshot."
        }

        $workingObjectOutput = @(
            & git -C $rootPath hash-object --no-filters -- $relativePath 2>&1
        )
        if (
            $LASTEXITCODE -ne 0 -or
            $workingObjectOutput.Count -ne 1 -or
            [string] $workingObjectOutput[0] -cne $objectId
        ) {
            throw "The Git index and working tree differ during the secret scan."
        }
    }
}

function Invoke-DetectSecretsJson {
    param(
        [Parameter(Mandatory = $true)][string[]] $Files,
        [Parameter(Mandatory = $true)][string] $OutputPath,
        [string] $WorkingDirectory = $repoRoot
    )

    if ($Files.Count -eq 0) {
        throw "No files were selected for detect-secrets."
    }
    Assert-SafeRepositoryPath -Path $WorkingDirectory
    Assert-SafeRepositoryPath -Path $OutputPath
    Assert-SafeMutableRepositoryFile -Path $OutputPath
    $fileRecords = @(
        foreach ($scanPath in $Files) {
            $fullPath = if ([System.IO.Path]::IsPathRooted($scanPath)) {
                [System.IO.Path]::GetFullPath($scanPath)
            }
            else {
                [System.IO.Path]::GetFullPath((Join-Path $WorkingDirectory $scanPath))
            }
            if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
                throw "A serial secret-scan input is missing: $fullPath"
            }
            $item = Get-Item -LiteralPath $fullPath -Force
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                throw "A serial secret-scan input is a reparse point: $fullPath"
            }
            [ordered]@{
                scan_path = $scanPath.Replace("\", "/")
                full_path = $fullPath
                size = [int64] $item.Length
                sha256 = (
                    Get-FileHash -LiteralPath $fullPath -Algorithm SHA256
                ).Hash.ToLowerInvariant()
            }
        }
    )
    $requestPath = [System.String]::Concat($OutputPath, ".request.json")
    Assert-SafeMutableRepositoryFile -Path $requestPath
    $request = [ordered]@{
        root = [System.IO.Path]::GetFullPath($WorkingDirectory)
        files = $fileRecords
    }
    [System.IO.File]::WriteAllText(
        $requestPath,
        (($request | ConvertTo-Json -Depth 20) + [Environment]::NewLine),
        [System.Text.UTF8Encoding]::new($false)
    )
    Assert-SafeMutableRepositoryFile -Path $requestPath
    Push-Location -LiteralPath $WorkingDirectory
    try {
        $driverArguments = Get-GuardedPythonScriptArguments `
            -ScriptPath $serialScanDriver `
            -ArgumentList @($requestPath)
        $scanOutput = & $python @driverArguments
        if ($LASTEXITCODE -ne 0) {
            throw "The serial detect-secrets scan failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
    [System.IO.File]::WriteAllText(
        $OutputPath,
        ($scanOutput -join [Environment]::NewLine)
    )
    Assert-SafeMutableRepositoryFile -Path $OutputPath
    try {
        $document = Get-Content -LiteralPath $OutputPath -Raw |
            ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "detect-secrets did not emit valid JSON."
    }
    $activeFilterPaths = @($document.serial_scan.active_filters)
    foreach ($prohibitedFilter in $prohibitedDetectSecretsFilters) {
        if ($activeFilterPaths -contains $prohibitedFilter) {
            throw "The serial secret scanner kept a prohibited bypass filter enabled."
        }
    }
    $completed = @($document.serial_scan.completed)
    if ($completed.Count -ne $fileRecords.Count) {
        throw "The serial secret scanner did not report every input file as completed."
    }
    for ($index = 0; $index -lt $fileRecords.Count; $index += 1) {
        $expected = $fileRecords[$index]
        $actual = $completed[$index]
        if (
            $actual.scan_path -cne $expected.scan_path -or
            $actual.full_path -cne $expected.full_path -or
            [int64] $actual.size -ne [int64] $expected.size -or
            $actual.sha256 -cne $expected.sha256
        ) {
            throw "The serial secret scanner returned an invalid completion record."
        }
    }
    return $document
}

function Get-ShannonEntropy {
    param([Parameter(Mandatory = $true)][string] $Value)

    if ($Value.Length -eq 0) {
        return 0.0
    }
    $counts = @{}
    foreach ($character in $Value.ToCharArray()) {
        $key = [string] $character
        if ($counts.ContainsKey($key)) {
            $counts[$key] += 1
        }
        else {
            $counts[$key] = 1
        }
    }
    $entropy = 0.0
    foreach ($count in $counts.Values) {
        $probability = [double] $count / [double] $Value.Length
        $entropy -= $probability * [Math]::Log($probability, 2)
    }
    return $entropy
}

function Assert-NoHighConfidenceSecretInBytes {
    param(
        [Parameter(Mandatory = $true)][byte[]] $Bytes,
        [Parameter(Mandatory = $true)][string] $SourceLabel
    )

    $inspectionText = [System.Text.Encoding]::Latin1.GetString($bytes).Replace(
        [string][char]0,
        ""
    )
    if ($inspectionText -match $sensitivePattern) {
        throw "A high-confidence secret pattern was found in $SourceLabel."
    }

    # Mirror detect-secrets 1.5.0's quoted high-entropy detectors for files that
    # cannot safely be decoded as UTF-8. Otherwise, one invalid byte could turn
    # an approved binary extension into a bypass for a generic opaque secret.
    $base64QuotedPattern = '(?<quote>[''"])(?<value>[A-Za-z0-9+/\\_=\-]+)\k<quote>'
    foreach ($match in [regex]::Matches($inspectionText, $base64QuotedPattern)) {
        $value = $match.Groups["value"].Value
        if ((Get-ShannonEntropy -Value $value) -gt 4.5) {
            throw "A Base64 high-entropy string was found in $SourceLabel."
        }
    }

    $hexQuotedPattern = '(?<quote>[''"])(?<value>[0-9A-Fa-f]+)\k<quote>'
    foreach ($match in [regex]::Matches($inspectionText, $hexQuotedPattern)) {
        $value = $match.Groups["value"].Value
        $entropy = Get-ShannonEntropy -Value $value
        if ($value.Length -gt 1 -and $value -cmatch '^[0-9]+$') {
            $entropy -= 1.2 / [Math]::Log($value.Length, 2)
        }
        if ($entropy -gt 3.0) {
            throw "A hexadecimal high-entropy string was found in $SourceLabel."
        }
    }
}

function Assert-NoHighConfidenceSecretInBinaryFile {
    param([Parameter(Mandatory = $true)][System.IO.FileInfo] $File)

    Assert-NoHighConfidenceSecretInBytes `
        -Bytes ([System.IO.File]::ReadAllBytes($File.FullName)) `
        -SourceLabel ([System.String]::Concat("binary file ", $File.FullName))
}

function Add-ValidatedBinaryCompletionRecord {
    param(
        [Parameter(Mandatory = $true)][System.IO.FileInfo] $File,
        [Parameter(Mandatory = $true)][byte[]] $Bytes,
        [AllowNull()][System.Collections.Generic.List[object]] $CompletionRecords
    )

    Assert-NoHighConfidenceSecretInBytes `
        -Bytes $Bytes `
        -SourceLabel ([System.String]::Concat("binary file ", $File.FullName))
    $expectedSize = [int64] $Bytes.Length
    $expectedSha256 = Get-Sha256HexFromBytes -Bytes $Bytes
    Assert-NoReparsePointInPath -Path $File.FullName
    $currentItem = Get-Item -LiteralPath $File.FullName -Force
    if (
        ($currentItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or
        [string] $currentItem.LinkType -ceq "HardLink" -or
        [int64] $currentItem.Length -ne $expectedSize -or
        (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -cne
            $expectedSha256
    ) {
        throw "A binary secret-scan input changed during inspection."
    }
    if ($null -ne $CompletionRecords) {
        $CompletionRecords.Add([pscustomobject]@{
            full_path = [System.IO.Path]::GetFullPath($File.FullName)
            size = $expectedSize
            sha256 = $expectedSha256
        })
    }
}

function Get-SecretScanRepositoryFiles {
    param(
        [Parameter(Mandatory = $true)][string] $Root,
        [string[]] $ExcludedExactDirectories = @()
    )

    $rootPath = [System.IO.Path]::GetFullPath($Root)
    $isRepositoryRoot = $rootPath -ceq [System.IO.Path]::GetFullPath($repoRoot)
    $excludedDirectoryPaths = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    if ($isRepositoryRoot) {
        foreach ($relativePath in @(
            ".git",
            ".venv",
            "node_modules",
            "apps\web\node_modules",
            ".playwright-browsers",
            "ms-playwright",
            "apps\web\.playwright-browsers",
            "apps\web\ms-playwright"
        )) {
            $null = $excludedDirectoryPaths.Add(
                [System.IO.Path]::GetFullPath((Join-Path $repoRoot $relativePath))
            )
        }
    }
    foreach ($excludedPath in $ExcludedExactDirectories) {
        $fullExcludedPath = [System.IO.Path]::GetFullPath($excludedPath)
        $rootPrefix = $rootPath.TrimEnd(
            [System.IO.Path]::DirectorySeparatorChar
        ) + [System.IO.Path]::DirectorySeparatorChar
        if (-not $fullExcludedPath.StartsWith(
            $rootPrefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
            throw "A dynamic secret-scan exclusion is outside its enumeration root."
        }
        $null = $excludedDirectoryPaths.Add($fullExcludedPath)
    }
    $directories = [System.Collections.Generic.Stack[string]]::new()
    $directories.Push($rootPath)
    $files = [System.Collections.Generic.List[System.IO.FileInfo]]::new()
    $seenFiles = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    while ($directories.Count -gt 0) {
        $directory = $directories.Pop()
        foreach ($item in Get-ChildItem -LiteralPath $directory -Force -ErrorAction Stop) {
            if ($item.PSIsContainer) {
                if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                    throw "A secret-scan directory is a reparse point: $($item.FullName)"
                }
                if ($excludedDirectoryPaths.Contains($item.FullName)) {
                    continue
                }
                $directories.Push($item.FullName)
                continue
            }
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                throw "A secret-scan input file is a reparse point: $($item.FullName)"
            }
            if ($seenFiles.Add($item.FullName)) {
                $files.Add([System.IO.FileInfo] $item)
            }
        }
    }

    if ($isRepositoryRoot) {
        $trackedOutput = [string] (& git -C $repoRoot ls-files -z)
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to enumerate Git-tracked files for the secret scan."
        }
        foreach ($relativePath in $trackedOutput.Split(
            [char] 0,
            [System.StringSplitOptions]::RemoveEmptyEntries
        )) {
            $fullPath = [System.IO.Path]::GetFullPath(
                (Join-Path $repoRoot $relativePath)
            )
            $repoPrefix = $rootPath.TrimEnd(
                [System.IO.Path]::DirectorySeparatorChar
            ) + [System.IO.Path]::DirectorySeparatorChar
            if (
                -not $fullPath.StartsWith(
                    $repoPrefix,
                    [System.StringComparison]::OrdinalIgnoreCase
                ) -or
                -not (Test-Path -LiteralPath $fullPath -PathType Leaf)
            ) {
                throw "A Git-tracked secret-scan input is missing or out of scope."
            }
            Assert-NoReparsePointInPath -Path $fullPath
            $item = Get-Item -LiteralPath $fullPath -Force
            if ($seenFiles.Add($item.FullName)) {
                $files.Add([System.IO.FileInfo] $item)
            }
        }
    }
    return @($files)
}

function Get-ValidatedUtf8TextFiles {
    param(
        [Parameter(Mandatory = $true)][string[]] $Files,
        [string] $WorkingDirectory = $repoRoot,
        [AllowNull()]
        [System.Collections.Generic.List[object]] $BinaryCompletionRecords
    )

    $strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
    $validatedFiles = @()
    foreach ($scanPath in $Files) {
        $fullPath = if ([System.IO.Path]::IsPathRooted($scanPath)) {
            [System.IO.Path]::GetFullPath($scanPath)
        }
        else {
            [System.IO.Path]::GetFullPath((Join-Path $WorkingDirectory $scanPath))
        }
        if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
            throw "A secret-scan input file is missing: $fullPath"
        }
        $item = Get-Item -LiteralPath $fullPath -Force
        Assert-NoReparsePointInPath -Path $fullPath
        if ([string] $item.LinkType -ceq "HardLink") {
            throw "A secret-scan input cannot be hard-linked: $fullPath"
        }
        if ($compressedContainerExtensions.Contains($item.Extension)) {
            $isValidatedPlaywrightTrace = $false
            if ($item.Extension -ieq ".zip") {
                foreach ($artifactRoot in $playwrightArtifactRoots) {
                    $artifactPrefix = [System.IO.Path]::GetFullPath(
                        $artifactRoot
                    ).TrimEnd([System.IO.Path]::DirectorySeparatorChar) +
                        [System.IO.Path]::DirectorySeparatorChar
                    if ($fullPath.StartsWith(
                        $artifactPrefix,
                        [System.StringComparison]::OrdinalIgnoreCase
                    )) {
                        $isValidatedPlaywrightTrace = $true
                        break
                    }
                }
            }
            if (-not $isValidatedPlaywrightTrace) {
                throw "A compressed project container cannot be inspected safely: $fullPath"
            }
        }
        $bytes = [System.IO.File]::ReadAllBytes($fullPath)
        if (
            ($bytes.Length -ge 2 -and (
                ($bytes[0] -eq 0xff -and $bytes[1] -eq 0xfe) -or
                ($bytes[0] -eq 0xfe -and $bytes[1] -eq 0xff)
            )) -or
            ($bytes.Length -ge 4 -and (
                ($bytes[0] -eq 0xff -and $bytes[1] -eq 0xfe -and
                    $bytes[2] -eq 0x00 -and $bytes[3] -eq 0x00) -or
                ($bytes[0] -eq 0x00 -and $bytes[1] -eq 0x00 -and
                    $bytes[2] -eq 0xfe -and $bytes[3] -eq 0xff)
            ))
        ) {
            throw "A secret-scan text input uses a prohibited UTF-16/UTF-32 encoding: $fullPath"
        }
        try {
            $text = $strictUtf8.GetString($bytes)
        }
        catch [System.Text.DecoderFallbackException] {
            if (-not $approvedBinaryExtensions.Contains($item.Extension)) {
                throw "A non-binary secret-scan input is not valid UTF-8: $fullPath"
            }
            Add-ValidatedBinaryCompletionRecord `
                -File $item `
                -Bytes $bytes `
                -CompletionRecords $BinaryCompletionRecords
            continue
        }
        if ($text.Contains([char] 0)) {
            if (-not $approvedBinaryExtensions.Contains($item.Extension)) {
                throw "A non-binary secret-scan input contains NUL bytes: $fullPath"
            }
            Add-ValidatedBinaryCompletionRecord `
                -File $item `
                -Bytes $bytes `
                -CompletionRecords $BinaryCompletionRecords
            continue
        }
        $validatedFiles += $item
    }
    return @($validatedFiles)
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
    return (
        $script:AllowedArtifactSecretHashes.ContainsKey($key) -and
        $script:AllowedArtifactSecretHashes[$key].Contains($exactFindingKey)
    )
}

function Assert-SecretScanCompletionCoverage {
    param(
        [Parameter(Mandatory = $true)][System.IO.FileInfo[]] $ExpectedFiles,
        [Parameter(Mandatory = $true)][object[]] $TextCompletionRecords,
        [Parameter(Mandatory = $true)][object[]] $BinaryCompletionRecords
    )

    $expectedPaths = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($file in $ExpectedFiles) {
        $fullPath = [System.IO.Path]::GetFullPath($file.FullName)
        if (-not $expectedPaths.Add($fullPath)) {
            throw "The secret-scan artifact scope contains a duplicate path."
        }
    }

    $completedPaths = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($record in @($TextCompletionRecords) + @($BinaryCompletionRecords)) {
        $properties = @($record.PSObject.Properties.Name | Sort-Object)
        $requiredProperties = @("full_path", "sha256", "size")
        $allowedProperties = @("full_path", "scan_path", "sha256", "size")
        if (
            @($requiredProperties | Where-Object { $_ -notin $properties }).Count -gt 0 -or
            @($properties | Where-Object { $_ -notin $allowedProperties }).Count -gt 0
        ) {
            throw "A secret-scan completion record has an unexpected schema."
        }
        $fullPath = [System.IO.Path]::GetFullPath([string] $record.full_path)
        $expectedSize = [int64] $record.size
        $expectedSha256 = [string] $record.sha256
        if (
            $expectedSize -lt 0 -or
            $expectedSha256 -cnotmatch '^[0-9a-f]{64}$' -or
            -not (Test-Path -LiteralPath $fullPath -PathType Leaf) -or
            -not $completedPaths.Add($fullPath)
        ) {
            throw "A secret-scan completion record is invalid or duplicated."
        }
        Assert-NoReparsePointInPath -Path $fullPath
        $item = Get-Item -LiteralPath $fullPath -Force
        if (
            ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or
            [string] $item.LinkType -ceq "HardLink" -or
            [int64] $item.Length -ne $expectedSize -or
            (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne
                $expectedSha256
        ) {
            throw "A completed secret-scan input changed after inspection."
        }
    }
    if (-not $expectedPaths.SetEquals($completedPaths)) {
        throw "Secret-scan completion coverage does not match the exact artifact scope."
    }
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
        $artifactFiles = @(
            Get-ChildItem -LiteralPath $requiredDirectory -Recurse -File -Force
        )
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
        $buildEvidenceItem.LastWriteTimeUtc.AddSeconds(2) -lt
            $evidenceTimestamps["completed_at_utc"] -or
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
        Get-ChildItem -LiteralPath $nextRoot -Recurse -File -Filter "*.nft.json" -Force
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
            Add-AllowedArtifactSecretAtMatchingLines `
                -Path $nftPath.FullName `
                -Value $hash
        }
        if ("entryHash" -in $nft.PSObject.Properties.Name -and $null -ne $nft.entryHash) {
            if ($nft.entryHash -isnot [string] -or $nft.entryHash -cnotmatch '^[0-9a-f]{32}$') {
                throw "A Next.js file-trace manifest contains an invalid entry hash."
            }
            Add-AllowedArtifactSecretAtMatchingLines `
                -Path $nftPath.FullName `
                -Value $nft.entryHash
        }
    }
}

function Add-NextTraceIdExceptions {
    $tracePaths = @(
        (Join-Path $nextRoot "trace"),
        (Join-Path $nextRoot "trace-build")
    )
    $allTraceIds = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::Ordinal
    )
    foreach ($tracePath in $tracePaths) {
        if (-not (Test-Path -LiteralPath $tracePath -PathType Leaf)) {
            throw "A required Next.js diagnostic trace is missing: $tracePath"
        }
        $traceText = [System.IO.File]::ReadAllText($tracePath)
        try {
            $events = @($traceText | ConvertFrom-Json -ErrorAction Stop)
        }
        catch {
            throw "A Next.js diagnostic trace is not valid JSON: $tracePath"
        }
        if ($events.Count -eq 0) {
            throw "A Next.js diagnostic trace contains no events: $tracePath"
        }
        $fileTraceIds = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::Ordinal
        )
        foreach ($event in $events) {
            if ($event -isnot [pscustomobject]) {
                throw "A Next.js diagnostic trace contains a non-object event."
            }
            $propertyNames = @($event.PSObject.Properties.Name)
            foreach ($requiredProperty in @(
                "name", "duration", "timestamp", "id", "tags", "startTime", "traceId"
            )) {
                if ($requiredProperty -notin $propertyNames) {
                    throw "A Next.js diagnostic trace event has an unexpected schema."
                }
            }
            $traceId = [string] $event.traceId
            if ($traceId -cnotmatch '^[0-9a-f]{16}$') {
                throw "A Next.js diagnostic trace contains an invalid traceId."
            }
            $null = $fileTraceIds.Add($traceId)
            $null = $allTraceIds.Add($traceId)
        }
        foreach ($traceId in $fileTraceIds) {
            $propertyPattern = '"traceId"\s*:\s*"' + [regex]::Escape($traceId) + '"'
            if ($traceText -cnotmatch $propertyPattern) {
                throw "A validated Next.js traceId is missing from its JSON property."
            }
            Add-AllowedArtifactSecretAtMatchingLines `
                -Path $tracePath `
                -Value $traceId
        }
    }
    if ($allTraceIds.Count -ne 1) {
        throw "The Next.js diagnostic traces do not share one exact build traceId."
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
        Add-AllowedArtifactSecretAtMatchingLines `
            -Path $manifestPath `
            -Value $value
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
        Add-AllowedArtifactSecretAtMatchingLines `
            -Path $fixturePath `
            -Value $value
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
    Add-AllowedArtifactSecretAtMatchingLines `
        -Path $manifestJsonPath `
        -Value $encryptionKey
    Add-AllowedArtifactSecretAtMatchingLines `
        -Path $manifestJsPath `
        -Value $encryptionKey
    # The JS wrapper escapes the closing JSON quote, and detect-secrets includes
    # that one trailing backslash in its entropy token.
    Add-AllowedArtifactSecretAtMatchingLines `
        -Path $manifestJsPath `
        -Value ([string]::Concat($encryptionKey, [char] 92)) `
        -SearchValue $encryptionKey
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
        [Parameter(Mandatory = $true)][string] $Sentinel,
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[object]] $ArchiveCompletionRecords
    )

    [System.IO.Directory]::CreateDirectory($Destination) | Out-Null
    $strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
    $extracted = @()
    $entryIndex = 0
    $totalBytes = [int64] 0
    foreach ($traceArchive in $Archives) {
        Assert-NoReparsePointInPath -Path $traceArchive.FullName
        $archiveItem = Get-Item -LiteralPath $traceArchive.FullName -Force
        if (
            ($archiveItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or
            [string] $archiveItem.LinkType -ceq "HardLink"
        ) {
            throw "A Playwright trace archive cannot be linked."
        }
        $archiveBytes = [System.IO.File]::ReadAllBytes($traceArchive.FullName)
        Add-ValidatedBinaryCompletionRecord `
            -File $archiveItem `
            -Bytes $archiveBytes `
            -CompletionRecords $ArchiveCompletionRecords
        $archiveMemory = [System.IO.MemoryStream]::new($archiveBytes, $false)
        try {
            $archive = [System.IO.Compression.ZipArchive]::new(
                $archiveMemory,
                [System.IO.Compression.ZipArchiveMode]::Read,
                $false
            )
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
                    $entryExtension = [System.IO.Path]::GetExtension($entry.Name)
                    $hasCompressedSignature = (
                        $bytes.Length -ge 4 -and
                        $bytes[0] -eq 0x50 -and
                        $bytes[1] -eq 0x4b -and
                        $bytes[2] -in @(0x03, 0x05, 0x07) -and
                        $bytes[3] -in @(0x04, 0x06, 0x08)
                    ) -or (
                        $bytes.Length -ge 2 -and
                        $bytes[0] -eq 0x1f -and
                        $bytes[1] -eq 0x8b
                    ) -or (
                        $bytes.Length -ge 3 -and
                        $bytes[0] -eq 0x42 -and
                        $bytes[1] -eq 0x5a -and
                        $bytes[2] -eq 0x68
                    ) -or (
                        $bytes.Length -ge 6 -and
                        $bytes[0] -eq 0x37 -and
                        $bytes[1] -eq 0x7a -and
                        $bytes[2] -eq 0xbc -and
                        $bytes[3] -eq 0xaf -and
                        $bytes[4] -eq 0x27 -and
                        $bytes[5] -eq 0x1c
                    )
                    if (
                        $compressedContainerExtensions.Contains($entryExtension) -or
                        $hasCompressedSignature
                    ) {
                        throw "A nested compressed Playwright trace entry is prohibited."
                    }
                    Assert-NoHighConfidenceSecretInBytes `
                        -Bytes $bytes `
                        -SourceLabel "a Playwright trace entry"
                    $inspectionText = [System.Text.Encoding]::UTF8.GetString($bytes)
                    if ($inspectionText.Contains($Sentinel)) {
                        throw "The runtime sentinel leaked into a Playwright trace archive."
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
        finally {
            $archiveMemory.Dispose()
        }
    }
    return $extracted
}

$tempDirectory = New-TaskTempDirectory
try {
    $repositoryFiles = @(
        Get-SecretScanRepositoryFiles `
            -Root $repoRoot `
            -ExcludedExactDirectories @($tempDirectory)
    )

    $indexCanaryRoot = Join-Path $tempDirectory "index-worktree-canary"
    [System.IO.Directory]::CreateDirectory($indexCanaryRoot) | Out-Null
    & git -C $indexCanaryRoot init --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to initialize the Git index secret-scan canary."
    }
    & git -C $indexCanaryRoot config core.autocrlf false
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to configure the Git index secret-scan canary."
    }
    $indexCanaryPath = Join-Path $indexCanaryRoot "guarded.txt"
    [System.IO.File]::WriteAllText(
        $indexCanaryPath,
        "safe index snapshot`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    & git -C $indexCanaryRoot add -- "guarded.txt"
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to stage the Git index secret-scan canary."
    }
    Assert-GitIndexMatchesWorkingTree -Root $indexCanaryRoot
    [System.IO.File]::WriteAllText(
        $indexCanaryPath,
        "different working snapshot`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    $indexMismatchRejected = $false
    try {
        Assert-GitIndexMatchesWorkingTree -Root $indexCanaryRoot
    }
    catch {
        $indexMismatchRejected = $true
    }
    if (-not $indexMismatchRejected) {
        throw "The secret scan accepted a Git index/working-tree mismatch canary."
    }
    [System.IO.File]::WriteAllText(
        $indexCanaryPath,
        "safe index snapshot`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    Assert-GitIndexMatchesWorkingTree -Root $indexCanaryRoot
    $hadIndexEnvironment = Test-Path -LiteralPath Env:GIT_INDEX_FILE
    $previousIndexEnvironment = $env:GIT_INDEX_FILE
    $indexEnvironmentRejected = $false
    try {
        $env:GIT_INDEX_FILE = Join-Path $indexCanaryRoot "alternate-index"
        try {
            Assert-GitIndexMatchesWorkingTree -Root $indexCanaryRoot
        }
        catch {
            $indexEnvironmentRejected = $true
        }
    }
    finally {
        if ($hadIndexEnvironment) {
            $env:GIT_INDEX_FILE = $previousIndexEnvironment
        }
        else {
            Remove-Item Env:GIT_INDEX_FILE -ErrorAction SilentlyContinue
        }
    }
    if (-not $indexEnvironmentRejected) {
        throw "The secret scan accepted a Git index environment override canary."
    }

    $scopeCanaryRoot = Join-Path $tempDirectory "scope-enumeration"
    $scopeIncludedDirectory = Join-Path $scopeCanaryRoot ".vscode"
    $scopeNamedDirectory = Join-Path $scopeCanaryRoot "node_modules"
    [System.IO.Directory]::CreateDirectory($scopeIncludedDirectory) | Out-Null
    [System.IO.Directory]::CreateDirectory($scopeNamedDirectory) | Out-Null
    $scopeIncludedPath = Join-Path $scopeIncludedDirectory "settings.json"
    $scopeNamedPath = Join-Path $scopeNamedDirectory "project-file.txt"
    [System.IO.File]::WriteAllText($scopeIncludedPath, '{"scope":"included"}')
    [System.IO.File]::WriteAllText($scopeNamedPath, "project content")
    $scopeIncludedItem = Get-Item -LiteralPath $scopeIncludedPath -Force
    $scopeIncludedItem.Attributes =
        $scopeIncludedItem.Attributes -bor [System.IO.FileAttributes]::Hidden
    $scopeCanaryFiles = @(
        Get-SecretScanRepositoryFiles -Root $scopeCanaryRoot
    ).FullName
    if (
        $scopeCanaryFiles -notcontains $scopeIncludedPath -or
        $scopeCanaryFiles -notcontains $scopeNamedPath
    ) {
        throw "The secret-scan scope omitted a hidden or dependency-named project file."
    }

    $traceSnapshotCanaryPath = Join-Path $tempDirectory "trace-snapshot-canary.zip"
    $traceSnapshotCanaryArchive = [System.IO.Compression.ZipFile]::Open(
        $traceSnapshotCanaryPath,
        [System.IO.Compression.ZipArchiveMode]::Create
    )
    try {
        $traceSnapshotCanaryEntry = $traceSnapshotCanaryArchive.CreateEntry(
            "trace.txt",
            [System.IO.Compression.CompressionLevel]::Optimal
        )
        $traceSnapshotCanaryWriter = [System.IO.StreamWriter]::new(
            $traceSnapshotCanaryEntry.Open(),
            [System.Text.UTF8Encoding]::new($false)
        )
        try {
            $traceSnapshotCanaryWriter.Write("first immutable snapshot")
        }
        finally {
            $traceSnapshotCanaryWriter.Dispose()
        }
    }
    finally {
        $traceSnapshotCanaryArchive.Dispose()
    }
    $traceSnapshotCanaryRecords = [System.Collections.Generic.List[object]]::new()
    $traceSnapshotCanaryFiles = @(
        Expand-TraceTextArtifacts `
            -Archives @((Get-Item -LiteralPath $traceSnapshotCanaryPath)) `
            -Destination (Join-Path $tempDirectory "trace-snapshot-output") `
            -Sentinel "PHASE1_TRACE_SNAPSHOT_CANARY" `
            -ArchiveCompletionRecords $traceSnapshotCanaryRecords
    )
    if (
        $traceSnapshotCanaryRecords.Count -ne 1 -or
        $traceSnapshotCanaryFiles.Count -ne 1 -or
        [System.IO.File]::ReadAllText($traceSnapshotCanaryFiles[0].FullName) -cne
            "first immutable snapshot"
    ) {
        throw "The Playwright trace immutable-snapshot canary was not inspected exactly once."
    }

    $replacementMemory = [System.IO.MemoryStream]::new()
    try {
        $replacementArchive = [System.IO.Compression.ZipArchive]::new(
            $replacementMemory,
            [System.IO.Compression.ZipArchiveMode]::Create,
            $true
        )
        try {
            $replacementEntry = $replacementArchive.CreateEntry(
                "trace.txt",
                [System.IO.Compression.CompressionLevel]::Optimal
            )
            $replacementWriter = [System.IO.StreamWriter]::new(
                $replacementEntry.Open(),
                [System.Text.UTF8Encoding]::new($false)
            )
            try {
                $replacementWriter.Write("replacement archive snapshot")
            }
            finally {
                $replacementWriter.Dispose()
            }
        }
        finally {
            $replacementArchive.Dispose()
        }
        $replacementBytes = $replacementMemory.ToArray()
    }
    finally {
        $replacementMemory.Dispose()
    }
    [System.IO.File]::WriteAllBytes($traceSnapshotCanaryPath, $replacementBytes)
    $traceSnapshotMutationRejected = $false
    try {
        Assert-SecretScanCompletionCoverage `
            -ExpectedFiles @((Get-Item -LiteralPath $traceSnapshotCanaryPath)) `
            -TextCompletionRecords @() `
            -BinaryCompletionRecords @($traceSnapshotCanaryRecords)
    }
    catch {
        $traceSnapshotMutationRejected = $true
    }
    if (-not $traceSnapshotMutationRejected) {
        throw "The secret scan accepted a mutated Playwright trace archive canary."
    }

    Assert-GitIndexMatchesWorkingTree -Root $repoRoot

    $build = Assert-CurrentBuildEvidence
    Assert-E2eEvidence -Build $build

    Add-AllowedArtifactSecretAtMatchingLines -Path $buildIdPath -Value $build.BuildId
    Add-AllowedArtifactSecretAtMatchingLines `
        -Path $buildEvidencePath `
        -Value $build.BuildId
    Add-AllowedArtifactSecretAtMatchingLines `
        -Path $buildEvidencePath `
        -Value $build.SentinelSha256
    Add-AllowedArtifactSecretAtMatchingLines `
        -Path $e2eApiLog `
        -Value $build.BuildId
    Add-AllowedArtifactSecretAtMatchingLines `
        -Path $e2eApiLog `
        -Value $build.SentinelSha256
    Add-AllowedArtifactSecretAtMatchingLines `
        -Path $e2eWebLog `
        -Value $build.BuildId
    $packageManifestPath = Join-Path $repoRoot "PACKAGE_MANIFEST.json"
    $approvedPackageManifestSha256 = [string]::Concat(
        "c11bb9c8", "42694512",
        "f4026e92", "c7461268",
        "3a5c7d9e", "1091f9f8",
        "1faa1832", "9a3afda8"
    )
    $actualPackageManifestSha256 = (
        Get-FileHash -LiteralPath $packageManifestPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($actualPackageManifestSha256 -cne $approvedPackageManifestSha256) {
        throw "PACKAGE_MANIFEST.json does not match its approved immutable digest."
    }
    Add-StructuredSha256Exceptions -Path $packageManifestPath
    Add-ValidatedPackageLockExceptions -Path (
        Join-Path $repoRoot "package-lock.json"
    )
    Add-ValidatedEvidenceManifestExceptions -Path (
        Join-Path $repoRoot "qa\evidence\phase_01\evidence-manifest.json"
    )
    Add-NextGeneratedHashExceptions
    Add-NextTraceIdExceptions
    Add-NextPrerenderManifestExceptions
    Add-SentinelUnitFixtureExceptions
    $nextEncryption = Add-NextEncryptionKeyExceptions

    $entropyCanaryPath = Join-Path $tempDirectory "--only-allowlisted"
    $entropyCanaryBytes = [byte[]]::new(48)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($entropyCanaryBytes)
    $entropyCanary = [System.Convert]::ToBase64String($entropyCanaryBytes)
    $inlinePragma = [string]::Concat("# pragma: allowlist ", "secret")
    [System.IO.File]::WriteAllText(
        $entropyCanaryPath,
        "opaque_value = `"$entropyCanary`" $inlinePragma"
    )
    $lockCanaryPath = Join-Path $tempDirectory "package-lock.json"
    [System.IO.File]::WriteAllText(
        $lockCanaryPath,
        "{`"opaque`":`"$entropyCanary`"}"
    )
    $nonTextExtensionCanaryPath = Join-Path $tempDirectory "entropy-canary.svg"
    $nonTextEntropyCanaryBytes = [byte[]]::new(48)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill(
        $nonTextEntropyCanaryBytes
    )
    $nonTextEntropyCanary = [System.Convert]::ToBase64String(
        $nonTextEntropyCanaryBytes
    )
    [System.IO.File]::WriteAllText(
        $nonTextExtensionCanaryPath,
        "<svg><!-- opaque_value = `"$nonTextEntropyCanary`" --></svg>"
    )
    $fakeBinaryExtensionCanaryPath = Join-Path $tempDirectory "text-canary.png"
    [System.IO.File]::WriteAllText(
        $fakeBinaryExtensionCanaryPath,
        [System.String]::Concat("opaque_value = `"", $nonTextEntropyCanary, "`"")
    )
    $utf8SwaggerCanaryPath = Join-Path $tempDirectory "emoji-swagger-canary.txt"
    [System.IO.File]::WriteAllText(
        $utf8SwaggerCanaryPath,
        [System.String]::Concat("표시 = `"", $nonTextEntropyCanary, "`"")
    )
    $detectSecretsCanaryFiles = @(
        "--only-allowlisted",
        "package-lock.json",
        "entropy-canary.svg",
        "emoji-swagger-canary.txt",
        "text-canary.png"
    )
    $null = Get-ValidatedUtf8TextFiles `
        -Files $detectSecretsCanaryFiles `
        -WorkingDirectory $tempDirectory
    $canaryScan = Invoke-DetectSecretsJson `
        -Files $detectSecretsCanaryFiles `
        -OutputPath (Join-Path $tempDirectory "canary-scan.json") `
        -WorkingDirectory $tempDirectory
    $canaryTypes = @(
        foreach ($property in $canaryScan.results.PSObject.Properties) {
            foreach ($finding in $property.Value) {
                $finding.type
            }
        }
    )
    $canaryFindingPaths = @($canaryScan.results.PSObject.Properties.Name)
    if (
        $canaryTypes -notcontains "Base64 High Entropy String" -or
        $canaryFindingPaths -notcontains "--only-allowlisted" -or
        $canaryFindingPaths -notcontains "package-lock.json" -or
        $canaryFindingPaths -notcontains "entropy-canary.svg" -or
        $canaryFindingPaths -notcontains "emoji-swagger-canary.txt" -or
        $canaryFindingPaths -notcontains "text-canary.png"
    ) {
        throw "detect-secrets did not reject every filter, path, extension, and UTF-8 canary."
    }
    $lineScopeCanaryPath = Join-Path $tempDirectory "line-scoped-exception-canary.txt"
    [System.IO.File]::WriteAllLines(
        $lineScopeCanaryPath,
        @(
            [System.String]::Concat("first = `"", $entropyCanary, "`""),
            [System.String]::Concat("second = `"", $entropyCanary, "`"")
        )
    )
    Add-AllowedArtifactSecret `
        -Path $lineScopeCanaryPath `
        -Value $entropyCanary `
        -LineNumber 1
    $wrongLineFinding = [pscustomobject]@{
        type = "Base64 High Entropy String"
        hashed_secret = Get-Sha1Hex -Value $entropyCanary
        line_number = 2
    }
    if (Test-AllowedArtifactFinding `
        -FindingPath $lineScopeCanaryPath `
        -Finding $wrongLineFinding) {
        throw "A generated-secret exception escaped its exact validated line."
    }

    $utf16CanaryPath = Join-Path $tempDirectory "utf16-encoding-canary.ps1"
    [System.IO.File]::WriteAllText(
        $utf16CanaryPath,
        "opaque_value = `"$entropyCanary`"",
        [System.Text.Encoding]::Unicode
    )
    $utf16Rejected = $false
    try {
        $null = Get-ValidatedUtf8TextFiles `
            -Files @($utf16CanaryPath) `
            -WorkingDirectory $tempDirectory
    }
    catch {
        $utf16Rejected = $true
    }
    if (-not $utf16Rejected) {
        throw "The secret-scan encoding gate accepted a UTF-16 text canary."
    }
    $invalidUtf8CanaryPath = Join-Path $tempDirectory "invalid-utf8-canary.txt"
    $invalidUtf8Prefix = [System.Text.Encoding]::UTF8.GetBytes(
        [System.String]::Concat("opaque_value = `"", $entropyCanary, "`"")
    )
    $invalidUtf8Bytes = [byte[]]::new($invalidUtf8Prefix.Length + 1)
    [System.Array]::Copy(
        $invalidUtf8Prefix,
        $invalidUtf8Bytes,
        $invalidUtf8Prefix.Length
    )
    $invalidUtf8Bytes[$invalidUtf8Bytes.Length - 1] = 0x80
    [System.IO.File]::WriteAllBytes($invalidUtf8CanaryPath, $invalidUtf8Bytes)
    $invalidUtf8Rejected = $false
    try {
        $null = Get-ValidatedUtf8TextFiles `
            -Files @($invalidUtf8CanaryPath) `
            -WorkingDirectory $tempDirectory
    }
    catch {
        $invalidUtf8Rejected = $true
    }
    if (-not $invalidUtf8Rejected) {
        throw "The secret-scan encoding gate accepted an invalid UTF-8 text canary."
    }

    $binaryEntropyCanaryPath = Join-Path $tempDirectory "binary-entropy-canary.png"
    $binaryEntropyPrefix = [System.Text.Encoding]::UTF8.GetBytes(
        [System.String]::Concat("opaque_value = `"", $entropyCanary, "`"")
    )
    $binaryEntropyBytes = [byte[]]::new($binaryEntropyPrefix.Length + 1)
    [System.Array]::Copy(
        $binaryEntropyPrefix,
        $binaryEntropyBytes,
        $binaryEntropyPrefix.Length
    )
    $binaryEntropyBytes[$binaryEntropyBytes.Length - 1] = 0x80
    [System.IO.File]::WriteAllBytes(
        $binaryEntropyCanaryPath,
        $binaryEntropyBytes
    )
    $binaryEntropyRejected = $false
    try {
        $null = Get-ValidatedUtf8TextFiles `
            -Files @($binaryEntropyCanaryPath) `
            -WorkingDirectory $tempDirectory
    }
    catch {
        $binaryEntropyRejected = $true
    }
    if (-not $binaryEntropyRejected) {
        throw "The binary inspection gate accepted a high-entropy invalid UTF-8 canary."
    }
    $compressedCanaryPath = Join-Path $tempDirectory "compressed-secret-canary.zip"
    $compressedCanaryArchive = [System.IO.Compression.ZipFile]::Open(
        $compressedCanaryPath,
        [System.IO.Compression.ZipArchiveMode]::Create
    )
    try {
        $compressedCanaryEntry = $compressedCanaryArchive.CreateEntry(
            "credentials.txt",
            [System.IO.Compression.CompressionLevel]::Optimal
        )
        $compressedCanaryWriter = [System.IO.StreamWriter]::new(
            $compressedCanaryEntry.Open(),
            [System.Text.UTF8Encoding]::new($false)
        )
        try {
            $compressedCanaryWriter.Write(
                [System.String]::Concat("opaque_value = `"", $entropyCanary, "`"")
            )
        }
        finally {
            $compressedCanaryWriter.Dispose()
        }
    }
    finally {
        $compressedCanaryArchive.Dispose()
    }
    $compressedCanaryRejected = $false
    try {
        $null = Get-ValidatedUtf8TextFiles `
            -Files @($compressedCanaryPath) `
            -WorkingDirectory $tempDirectory
    }
    catch {
        $compressedCanaryRejected = $true
    }
    if (-not $compressedCanaryRejected) {
        throw "The secret-scan gate accepted an uninspectable compressed project archive."
    }
    $binaryCompletionCanaryPath = Join-Path $tempDirectory "binary-completion-canary.png"
    $binaryCompletionCanaryBytes = [byte[]] @(0x89, 0x50, 0x4e, 0x47, 0x80)
    [System.IO.File]::WriteAllBytes(
        $binaryCompletionCanaryPath,
        $binaryCompletionCanaryBytes
    )
    $binaryCanaryRecords = [System.Collections.Generic.List[object]]::new()
    $binaryCanaryTextFiles = @(
        Get-ValidatedUtf8TextFiles `
            -Files @($binaryCompletionCanaryPath) `
            -WorkingDirectory $tempDirectory `
            -BinaryCompletionRecords $binaryCanaryRecords
    )
    if (
        $binaryCanaryTextFiles.Count -ne 0 -or
        $binaryCanaryRecords.Count -ne 1 -or
        $binaryCanaryRecords[0].full_path -cne $binaryCompletionCanaryPath -or
        [int64] $binaryCanaryRecords[0].size -ne $binaryCompletionCanaryBytes.Length -or
        $binaryCanaryRecords[0].sha256 -cne
            (Get-Sha256HexFromBytes -Bytes $binaryCompletionCanaryBytes)
    ) {
        throw "The binary inspection gate omitted an exact completion record."
    }

    $ignoredEnvironmentFiles = @(
        $repositoryFiles | Where-Object { $_.Name -like ".env*" }
    )
    $traceArchives = @(
        foreach ($root in $playwrightArtifactRoots) {
            Get-ChildItem -LiteralPath $root -Recurse -File -Filter "*.zip" -Force
        }
    )
    $traceArchivePaths = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($traceArchive in $traceArchives) {
        $null = $traceArchivePaths.Add(
            [System.IO.Path]::GetFullPath($traceArchive.FullName)
        )
    }
    $binaryCompletionRecords = [System.Collections.Generic.List[object]]::new()
    $traceTextFiles = @(
        Expand-TraceTextArtifacts `
            -Archives $traceArchives `
            -Destination (Join-Path $tempDirectory "trace-text") `
            -Sentinel $build.Sentinel `
            -ArchiveCompletionRecords $binaryCompletionRecords
    )

    $artifactFiles = @($repositoryFiles + $traceTextFiles)
    $scanFiles = @(
        $artifactFiles |
            Where-Object {
                -not $traceArchivePaths.Contains(
                    [System.IO.Path]::GetFullPath($_.FullName)
                )
            } |
            ForEach-Object { Convert-ToScanArgument -Path $_.FullName } |
            Sort-Object -Unique
    )
    $validatedTextScanFiles = @(
        Get-ValidatedUtf8TextFiles `
            -Files $scanFiles `
            -WorkingDirectory $repoRoot `
            -BinaryCompletionRecords $binaryCompletionRecords
    )
    $validatedTextScanArguments = @(
        $validatedTextScanFiles |
            ForEach-Object { Convert-ToScanArgument -Path $_.FullName } |
            Sort-Object -Unique
    )
    $scan = Invoke-DetectSecretsJson `
        -Files $validatedTextScanArguments `
        -OutputPath (Join-Path $tempDirectory "scan.json")
    Assert-SecretScanCompletionCoverage `
        -ExpectedFiles $artifactFiles `
        -TextCompletionRecords @($scan.serial_scan.completed) `
        -BinaryCompletionRecords @($binaryCompletionRecords)

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

    $inspectionFiles = @(
        $validatedTextScanFiles |
            Sort-Object -Property FullName -Unique
    )
    $patternHits = $inspectionFiles | Select-String -Pattern $sensitivePattern
    if ($patternHits) {
        $patternHits | Select-Object Path, LineNumber | Format-Table -AutoSize | Out-Host
        throw "High-confidence secret pattern detected."
    }

    $bundleHits = Get-ChildItem -LiteralPath $nextStaticRoot -Recurse -File -Force |
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
        Get-ChildItem -LiteralPath $nextRoot -Recurse -File -Force |
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
        $sentinelLeakFiles += @(
            Get-ChildItem -LiteralPath $root -Recurse -File -Force
        )
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

    $finalRepositoryFiles = @(
        Get-SecretScanRepositoryFiles `
            -Root $repoRoot `
            -ExcludedExactDirectories @($tempDirectory)
    )
    $initialRepositoryPaths = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    $finalRepositoryPaths = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($file in $repositoryFiles) {
        $null = $initialRepositoryPaths.Add(
            [System.IO.Path]::GetFullPath($file.FullName)
        )
    }
    foreach ($file in $finalRepositoryFiles) {
        $null = $finalRepositoryPaths.Add(
            [System.IO.Path]::GetFullPath($file.FullName)
        )
    }
    if (
        $initialRepositoryPaths.Count -ne $repositoryFiles.Count -or
        $finalRepositoryPaths.Count -ne $finalRepositoryFiles.Count -or
        -not $initialRepositoryPaths.SetEquals($finalRepositoryPaths)
    ) {
        throw "The repository file scope changed during the secret scan."
    }
    Assert-SecretScanCompletionCoverage `
        -ExpectedFiles $artifactFiles `
        -TextCompletionRecords @($scan.serial_scan.completed) `
        -BinaryCompletionRecords @($binaryCompletionRecords)
    Assert-GitIndexMatchesWorkingTree -Root $repoRoot

    Write-Host "Secret scan passed."
}
finally {
    Remove-TaskTempDirectory -Path $tempDirectory
}
