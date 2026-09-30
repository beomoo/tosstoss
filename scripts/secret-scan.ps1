param([switch] $GeneratedArtifactSelfTest, [switch] $FrozenDiagnosticSelfTest)

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
$sensitivePattern = '(?i)(sk-(?:(?:live|proj|svcacct)[_-][a-z0-9_-]{20,}|[a-z0-9]{32,})|github_pat_[a-z0-9_]{20,}|gh[pousr]_[a-z0-9]{20,}|glpat-[a-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._-]{20,}|eyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{10,}|(?:TOSS_CLIENT_SECRET|client_secret)\s*=\s*["'']?(?=[A-Za-z0-9._~+/\-]{12,})(?=[A-Za-z0-9._~+/\-]*[0-9.+/~\-])[A-Za-z0-9._~+/\-]+)'
$script:AllowedArtifactSecretHashes = @{}
$script:PublicChecksumPath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "scripts\linux_setup.py"))
$script:AllowedPublicChecksumFindingKeys = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::Ordinal
)
$script:GeneratedProofInputRecords = @{}
$script:GeneratedProofRoot = $null
$script:TypeScriptCanonicalState = $null
$script:GeneratedMypyTagContractsReady = $false
$script:FrozenDiagnosticSnapshotPath = [System.IO.Path]::GetFullPath(
    (Join-Path $repoRoot "qa/PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_SNAPSHOT.csv")
)
$script:FrozenDiagnosticFindingKeys = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::Ordinal
)
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

function Add-FrozenMigrationBlobExceptions {
    $legacySourcePaths = @(
        (Join-Path $repoRoot (
            "services\api\alembic\versions\" +
            "0006_phase_02_cp3_c2_b2_c_reviewer_operations.py"
        )),
        (Join-Path $repoRoot "tests\backend\test_reviewer_operation_migration.py")
    )
    $counterBootstrapSourcePaths = @(
        (Join-Path $repoRoot (
            "services\api\alembic\versions\" +
            "0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap.py"
        )),
        (Join-Path $repoRoot "tests\backend\test_counter_capability_migration.py")
    )
    $frozenMigrations = @(
        [pscustomobject]@{
            Path = "services/api/alembic/versions/0001_phase_01_foundation.py"
            Blob = [string]::Concat(
                "d00355c2", "456021e6", "ffb195e5", "0833adc3", "2c74a4ad"
            )
        },
        [pscustomobject]@{
            Path = "services/api/alembic/versions/0002_phase_02_cp3_foundation.py"
            Blob = [string]::Concat(
                "53f40664", "eca2ea24", "66cc6154", "b8579c5d", "b506e0ba"
            )
        },
        [pscustomobject]@{
            Path = "services/api/alembic/versions/0003_phase_02_cp3_b_invariants.py"
            Blob = [string]::Concat(
                "47d5a690", "09949b15", "5211cd68", "20964013", "6a7cacd9"
            )
        },
        [pscustomobject]@{
            Path = "services/api/alembic/versions/0004_phase_02_cp3_c1_security_master.py"
            Blob = [string]::Concat(
                "91b4d96a", "445be23e", "7aa55e08", "b9310dc7", "334a026d"
            )
        },
        [pscustomobject]@{
            Path = "services/api/alembic/versions/0005_phase_02_cp3_c2_b_issuer_authority.py"
            Blob = [string]::Concat(
                "81976b8f", "70a1f610", "7526a13a", "cadf23f3", "69b196e3"
            )
        },
        [pscustomobject]@{
            Path = (
                "services/api/alembic/versions/" +
                "0006_phase_02_cp3_c2_b2_c_reviewer_operations.py"
            )
            Blob = [string]::Concat(
                "f10e7f5b", "c21e232f", "c68b3814", "4f5b8fb1", "24f31698"
            )
        }
    )
    foreach ($frozenMigration in $frozenMigrations) {
        $actualBlob = @(
            & git -C $repoRoot hash-object --no-filters -- $frozenMigration.Path 2>&1
        )
        if (
            $LASTEXITCODE -ne 0 -or
            $actualBlob.Count -ne 1 -or
            ([string] $actualBlob[0]) -cne $frozenMigration.Blob
        ) {
            throw "A frozen predecessor migration does not match its approved Git blob."
        }
        $sourcePaths = if ($frozenMigration.Path -like "*/0006_*") {
            $counterBootstrapSourcePaths
        }
        else {
            @($legacySourcePaths) + @($counterBootstrapSourcePaths)
        }
        foreach ($sourcePath in $sourcePaths) {
            Add-AllowedArtifactSecretAtMatchingLines `
                -Path $sourcePath `
                -Value $frozenMigration.Blob
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

function Get-GeneratedSha256HexFromBytes {
    param(
        [Parameter(Mandatory = $true)][AllowNull()][AllowEmptyCollection()][byte[]] $Bytes
    )

    # Only generated proofs accept a non-null empty byte array; preserve the
    # existing common helper's caller contract. Never coerce missing input.
    if ($null -eq $Bytes) { throw "A generated hash input is null, not empty bytes." }
    return [System.Convert]::ToHexString(
        [System.Security.Cryptography.SHA256]::HashData($Bytes)
    ).ToLowerInvariant()
}

function Assert-GeneratedProofRootIdentity {
    param([Parameter(Mandatory = $true)][string] $Path)

    $root = [System.IO.Path]::GetFullPath($Path)
    $parent = [System.IO.Path]::GetFullPath([System.IO.Path]::GetDirectoryName($repoRoot))
    if (
        $root.Length -gt 120 -or
        [System.IO.Path]::GetFileName($root) -cnotmatch '^generated-proof-[0-9a-f]{32}$' -or
        -not [string]::Equals([System.IO.Path]::GetDirectoryName($root), $parent,
            [StringComparison]::OrdinalIgnoreCase) -or
        $root.StartsWith($repoRoot.TrimEnd([char] 92, [char] 47) +
            [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "A generated-artifact proof root is not an exact short external task path."
    }
    $drive = [System.IO.DriveInfo]::new([System.IO.Path]::GetPathRoot($root))
    if ($drive.DriveType -ne [System.IO.DriveType]::Fixed -or $drive.DriveFormat -cne "NTFS") {
        throw "A generated-artifact proof root requires fixed NTFS."
    }
    Assert-NoReparsePointInPath -Path $parent
    return $root
}

function Assert-SafeGeneratedProofInputPath {
    param([Parameter(Mandatory = $true)][string] $Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $repoPrefix = $repoRoot.TrimEnd([char] 92, [char] 47) +
        [System.IO.Path]::DirectorySeparatorChar
    if ($fullPath.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        Assert-SafeRepositoryPath -Path $fullPath
        return
    }
    if ($null -eq $script:GeneratedProofRoot) {
        throw "An external generated-artifact proof input has no owned root."
    }
    $proofPrefix = $script:GeneratedProofRoot.TrimEnd([char] 92, [char] 47) +
        [System.IO.Path]::DirectorySeparatorChar
    if (-not $fullPath.StartsWith($proofPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "A generated-artifact proof input is outside its owned root."
    }
    Assert-NoReparsePointInPath -Path $fullPath
}

function Assert-GeneratedProofTreeSafe {
    param([Parameter(Mandatory = $true)][string] $Path)

    $root = Assert-GeneratedProofRootIdentity -Path $Path
    Assert-NoReparsePointInPath -Path $root
    $pending = [System.Collections.Generic.Queue[string]]::new()
    $pending.Enqueue($root)
    while ($pending.Count -gt 0) {
        foreach ($item in @(Get-ChildItem -LiteralPath $pending.Dequeue() -Force)) {
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint -or
                (-not $item.PSIsContainer -and [string] $item.LinkType -ceq "HardLink")) {
                throw "A generated-artifact proof tree contains a link."
            }
            if ($item.PSIsContainer) { $pending.Enqueue($item.FullName) }
        }
    }
}

function Remove-GeneratedProofRoot {
    param([Parameter(Mandatory = $true)][string] $Path)

    $root = Assert-GeneratedProofRootIdentity -Path $Path
    if (-not [string]::Equals($root, $script:GeneratedProofRoot,
        [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove an unowned generated-artifact proof root."
    }
    if (Test-Path -LiteralPath $root) {
        Assert-GeneratedProofTreeSafe -Path $root
        Remove-Item -LiteralPath $root -Recurse -Force
    }
    $script:GeneratedProofRoot = $null
}

function Get-GeneratedArtifactSnapshot {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [switch] $Binary
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    Assert-SafeGeneratedProofInputPath -Path $fullPath
    $item = Get-Item -LiteralPath $fullPath -Force -ErrorAction Stop
    if ($item.PSIsContainer -or [string] $item.LinkType -ceq "HardLink") {
        throw "A generated-artifact proof input is not a regular, unlinked file."
    }
    $bytes = [System.IO.File]::ReadAllBytes($fullPath)
    $digest = Get-GeneratedSha256HexFromBytes -Bytes $bytes
    $text = $null
    if (-not $Binary) {
        $text = [System.Text.UTF8Encoding]::new($false, $true).GetString($bytes)
        if ($text.Contains([char] 0)) {
            throw "A generated-artifact proof input contains NUL."
        }
    }
    $key = $fullPath.ToLowerInvariant()
    if ($script:GeneratedProofInputRecords.ContainsKey($key)) {
        $previous = $script:GeneratedProofInputRecords[$key]
        if ($previous.Sha256 -cne $digest -or $previous.Size -ne $bytes.Length) {
            throw "A generated-artifact proof input changed during validation."
        }
    }
    $script:GeneratedProofInputRecords[$key] = [pscustomobject]@{
        Path = $fullPath; Sha256 = $digest; Size = $bytes.Length
    }
    return [pscustomobject]@{
        Path = $fullPath; Bytes = $bytes; Text = $text
        Sha256 = $digest; Size = $bytes.Length
    }
}

function Assert-GeneratedProofInputsUnchanged {
    foreach ($record in @($script:GeneratedProofInputRecords.Values)) {
        Assert-SafeGeneratedProofInputPath -Path $record.Path
        $item = Get-Item -LiteralPath $record.Path -Force -ErrorAction Stop
        if (
            $item.PSIsContainer -or [string] $item.LinkType -ceq "HardLink" -or
            $item.Length -ne $record.Size -or
            (Get-FileHash -LiteralPath $record.Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne
                $record.Sha256
        ) {
            throw "A generated-artifact proof source changed after validation."
        }
    }
}

function Assert-NoDuplicateGeneratedJsonKeys {
    param([Parameter(Mandatory = $true)][System.Text.Json.JsonElement] $Element)

    if ($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Object) {
        $keys = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::Ordinal
        )
        foreach ($property in $Element.EnumerateObject()) {
            if (-not $keys.Add($property.Name)) {
                throw "A generated artifact contains a duplicate JSON key."
            }
            Assert-NoDuplicateGeneratedJsonKeys -Element $property.Value
        }
    }
    elseif ($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Array) {
        foreach ($value in $Element.EnumerateArray()) {
            Assert-NoDuplicateGeneratedJsonKeys -Element $value
        }
    }
}

function ConvertFrom-StrictGeneratedJson {
    param([Parameter(Mandatory = $true)][string] $Text)

    $document = [System.Text.Json.JsonDocument]::Parse($Text)
    try { Assert-NoDuplicateGeneratedJsonKeys -Element $document.RootElement }
    finally { $document.Dispose() }
    return ConvertFrom-Json -InputObject $Text -AsHashtable -Depth 100
}

function ConvertTo-TypeScriptStructureToken {
    param([AllowNull()][object] $Value)

    if ($null -eq $Value) { return "null" }
    if ($Value -is [string]) {
        return ConvertTo-Json -InputObject $Value -Compress -EscapeHandling Default
    }
    if ($Value -is [bool]) {
        if ($Value) { return "true" }
        return "false"
    }
    if ($Value -is [System.Collections.IDictionary]) {
        $keys = [string[]] @($Value.Keys)
        [System.Array]::Sort($keys, [System.StringComparer]::Ordinal)
        $members = @(
            foreach ($key in $keys) {
                (ConvertTo-TypeScriptStructureToken -Value $key) + ":" +
                    (ConvertTo-TypeScriptStructureToken -Value $Value[$key])
            }
        )
        return "{" + ($members -join ",") + "}"
    }
    if ($Value -is [System.Collections.IEnumerable]) {
        $items = @(
            foreach ($item in $Value) {
                ConvertTo-TypeScriptStructureToken -Value $item
            }
        )
        return "[" + ($items -join ",") + "]"
    }
    if (
        $Value -is [byte] -or $Value -is [sbyte] -or
        $Value -is [short] -or $Value -is [ushort] -or
        $Value -is [int] -or $Value -is [uint] -or
        $Value -is [long] -or $Value -is [ulong]
    ) {
        return $Value.ToString([System.Globalization.CultureInfo]::InvariantCulture)
    }
    throw "TypeScript build-info contains an unsupported structure value."
}

function Get-ValidatedTypeScriptBuildInfoStructure {
    param([Parameter(Mandatory = $true)][string] $Text)

    # The current approved artifact is one minified line. Do not infer new
    # line-scoped exceptions from a differently serialized build-info file.
    if ($Text.Contains("`r") -or $Text.Contains("`n")) {
        throw "TypeScript build-info has an unproved serialization shape."
    }
    $data = ConvertFrom-StrictGeneratedJson -Text $Text
    if (
        $data -isnot [System.Collections.IDictionary] -or
        $data.version -cne "5.9.3" -or
        $data.fileNames -isnot [array] -or
        $data.fileInfos -isnot [array] -or
        $data.fileNames.Count -ne 704 -or
        $data.fileInfos.Count -ne 704
    ) {
        throw "TypeScript build-info has an unproved version or cardinality."
    }
    $values = [System.Collections.Generic.List[string]]::new()
    $projectionInfos = [System.Collections.Generic.List[object]]::new()
    foreach ($info in $data.fileInfos) {
        if ($info -is [string]) {
            $value = $info
            $projectionInfos.Add($null)
        }
        elseif ($info -is [System.Collections.IDictionary]) {
            $value = $info.version
            $projected = [System.Collections.Generic.Dictionary[string, object]]::new(
                [System.StringComparer]::Ordinal
            )
            foreach ($key in $info.Keys) {
                $projected[$key] = if ($key -ceq "version") {
                    $null
                }
                else {
                    $info[$key]
                }
            }
            $projectionInfos.Add($projected)
        }
        else {
            throw "TypeScript build-info has an unsupported file-info shape."
        }
        if ($value -isnot [string] -or $value -cnotmatch '^[0-9a-f]{64}$') {
            throw "TypeScript build-info contains an unproved source-version field."
        }
        $values.Add($value)
    }
    $uniqueValues = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::Ordinal
    )
    foreach ($value in $values) { $null = $uniqueValues.Add($value) }
    if ($uniqueValues.Count -ne 696) {
        throw "TypeScript build-info has an unproved distinct version population."
    }
    $projection = [System.Collections.Generic.Dictionary[string, object]]::new(
        [System.StringComparer]::Ordinal
    )
    foreach ($key in $data.Keys) {
        $projection[$key] = if ($key -ceq "fileInfos") {
            $projectionInfos.ToArray()
        }
        else {
            $data[$key]
        }
    }
    # This pins EVERY non-version field and file-info shape from the approved
    # snapshot, not merely top-level names. New signatures/options/paths/index
    # structures, unknown fields, and same-line hidden values fail closed.
    $expectedProjection = [string]::Concat(
        "c4797747", "e076aea6", "24913d93", "992a81c0",
        "bcbbe35b", "f35a2964", "9233c5e8", "55bb8cec"
    )
    $projectionBytes = [System.Text.Encoding]::UTF8.GetBytes(
        (ConvertTo-TypeScriptStructureToken -Value $projection)
    )
    if ((Get-Sha256HexFromBytes -Bytes $projectionBytes) -cne $expectedProjection) {
        throw "TypeScript build-info non-version structure is not the approved snapshot."
    }

    # Each approved file-info is flat (string or fixed scalar object), as
    # established by the full projection pin. Require its 704 values to be
    # unescaped literals, then prove every occurrence in the entire raw line
    # is one of those exact field occurrences. No pointer-less exception may
    # silently admit another location containing the same value.
    $segments = [regex]::Matches(
        $Text, '"fileInfos"\s*:\s*\[(?<items>[^\[\]]*)\]'
    )
    if ($segments.Count -ne 1) {
        throw "TypeScript build-info file-info field is not an exact literal."
    }
    $segment = $segments[0].Groups["items"].Value
    $literalValues = [regex]::Matches($segment, '"(?<value>[0-9a-f]{64})"')
    if ($literalValues.Count -ne 704) {
        throw "TypeScript build-info source-version literals are not exact."
    }
    $expectedOccurrences = @{}
    foreach ($value in $values) {
        if (-not $expectedOccurrences.ContainsKey($value)) {
            $expectedOccurrences[$value] = 0
        }
        $expectedOccurrences[$value] += 1
    }
    $actualOccurrences = @{}
    foreach ($literal in $literalValues) {
        $value = $literal.Groups["value"].Value
        if (-not $actualOccurrences.ContainsKey($value)) {
            $actualOccurrences[$value] = 0
        }
        $actualOccurrences[$value] += 1
    }
    if ($actualOccurrences.Count -ne 696) {
        throw "TypeScript build-info literals do not match the approved population."
    }
    foreach ($value in $uniqueValues) {
        if (
            -not $actualOccurrences.ContainsKey($value) -or
            $actualOccurrences[$value] -ne $expectedOccurrences[$value] -or
            [regex]::Matches($Text, [regex]::Escape($value)).Count -ne
                $expectedOccurrences[$value]
        ) {
            throw "TypeScript source-version value occurs outside its approved field."
        }
    }
    $allQuotedHex = [regex]::Matches($Text, '"(?<value>[0-9A-Fa-f]{32,})"')
    if ($allQuotedHex.Count -ne 704) {
        throw "TypeScript build-info contains unexplained quoted hexadecimal text."
    }
    foreach ($literal in $allQuotedHex) {
        if (-not $uniqueValues.Contains($literal.Groups["value"].Value)) {
            throw "TypeScript build-info contains an unproved hexadecimal value."
        }
    }
    return [pscustomobject]@{
        Data = $data
        Values = $values.ToArray()
        DistinctValues = [string[]] @($uniqueValues)
    }
}

function Get-ApprovedTypeScriptLibrarySha256 {
    return [string]::Concat(
        "3ae902c9", "2cc44dac", "e175c0e6", "9e13a4b0",
        "899f6983", "c6121d76", "b9ab8dd5", "795e7675"
    )
}

function Assert-ApprovedTypeScriptPackage {
    $package = Get-GeneratedArtifactSnapshot -Path (Join-Path $repoRoot "apps\web\package.json")
    $installed = Get-GeneratedArtifactSnapshot -Path (Join-Path $repoRoot "node_modules\typescript\package.json")
    $packageJson = ConvertFrom-StrictGeneratedJson -Text $package.Text
    $installedJson = ConvertFrom-StrictGeneratedJson -Text $installed.Text
    if (
        $packageJson.devDependencies.typescript -cne "5.9.3" -or
        $installedJson.name -cne "typescript" -or
        $installedJson.version -cne "5.9.3"
    ) {
        throw "TypeScript dependency pin or installed version is not approved."
    }
}

function Get-TypeScriptSourceVersionHashes {
    param(
        [Parameter(Mandatory = $true)][string] $LibraryPath,
        [Parameter(Mandatory = $true)][string[]] $SourcePaths
    )

    $expectedLibrary = Get-ApprovedTypeScriptLibrarySha256
    $library = Get-GeneratedArtifactSnapshot -Path $LibraryPath
    if ($library.Sha256 -cne $expectedLibrary) {
        throw "TypeScript generator code differs from the proved installed contract."
    }
    $node = Assert-PhaseNodeRuntime
    $driver = @'
const fs = require("fs");
const crypto = require("crypto");
try {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  const actual = crypto.createHash("sha256").update(fs.readFileSync(input.library)).digest("hex");
  if (actual !== input.expectedLibrary) throw new Error("generator mismatch");
  const ts = require(input.library);
  if (ts.version !== "5.9.3") throw new Error("version mismatch");
  const values = input.sources.map(path => {
    const text = ts.sys.readFile(path);
    if (typeof text !== "string") throw new Error("missing source");
    return ts.getSourceFileVersionAsHashFromText(ts.sys, text);
  });
  process.stdout.write(JSON.stringify(values));
} catch (_) {
  process.stderr.write("TypeScript source-version proof failed.\n");
  process.exitCode = 1;
}
'@
    $payload = @{
        library = $library.Path
        expectedLibrary = $expectedLibrary
        sources = $SourcePaths
    } | ConvertTo-Json -Depth 5 -Compress
    $output = @($payload | & $node -e $driver 2>&1)
    if ($LASTEXITCODE -ne 0 -or $output.Count -ne 1) {
        throw "TypeScript source-version computation did not complete exactly."
    }
    try {
        $computed = ConvertFrom-Json -InputObject ([string] $output[0]) -NoEnumerate
    }
    catch {
        throw "TypeScript source-version computation returned an invalid result."
    }
    if ($computed -isnot [array] -or $computed.Count -ne $SourcePaths.Count) {
        throw "TypeScript source-version computation returned the wrong cardinality."
    }
    foreach ($value in $computed) {
        if ($value -isnot [string] -or $value -cnotmatch '^[0-9a-f]{64}$') {
            throw "TypeScript source-version computation returned an invalid digest."
        }
    }
    $null = Get-GeneratedArtifactSnapshot -Path $LibraryPath
    return ,$computed
}

function Get-ValidatedTypeScriptBuildInfoProof {
    param(
        [string] $Path = (Join-Path $repoRoot "apps\web\.next\cache\tsconfig.tsbuildinfo")
    )

    $snapshot = Get-GeneratedArtifactSnapshot -Path $Path
    $structure = Get-ValidatedTypeScriptBuildInfoStructure -Text $snapshot.Text
    Assert-ApprovedTypeScriptPackage
    $sourceBase = [System.IO.Path]::GetFullPath(
        (Join-Path $repoRoot "apps\web\.next\cache")
    )
    $sourcePaths = [System.Collections.Generic.List[string]]::new()
    $seenPaths = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($name in $structure.Data.fileNames) {
        if ($name -isnot [string] -or [System.IO.Path]::IsPathRooted($name)) {
            throw "TypeScript build-info source path is not a proved relative path."
        }
        $sourcePath = [System.IO.Path]::GetFullPath((Join-Path $sourceBase $name))
        $source = Get-GeneratedArtifactSnapshot -Path $sourcePath
        if (-not $seenPaths.Add($source.Path)) {
            throw "TypeScript build-info repeats a resolved source path."
        }
        $sourcePaths.Add($source.Path)
    }
    $libraryPath = Join-Path $repoRoot "node_modules\typescript\lib\typescript.js"
    $computed = Get-TypeScriptSourceVersionHashes `
        -LibraryPath $libraryPath -SourcePaths $sourcePaths.ToArray()
    for ($index = 0; $index -lt 704; $index += 1) {
        if ($computed[$index] -cne $structure.Values[$index]) {
            throw "TypeScript build-info does not match an actual source version."
        }
    }
    foreach ($sourcePath in $sourcePaths) {
        $null = Get-GeneratedArtifactSnapshot -Path $sourcePath
    }
    $null = Get-GeneratedArtifactSnapshot -Path $Path
    return [pscustomobject]@{
        Path = $snapshot.Path
        Values = $structure.DistinctValues
        SourceVersionCount = 704
        InputRecords = @()
    }
}

function Assert-GeneratedMypyKeys {
    param([object] $Object, [string[]] $Expected)

    if ($Object -isnot [System.Collections.IDictionary]) {
        throw "A generated mypy object has an unexpected type."
    }
    $actual = @($Object.Keys | Sort-Object -CaseSensitive)
    $expectedKeys = @($Expected | Sort-Object -CaseSensitive)
    if ($actual.Count -ne $expectedKeys.Count) {
        throw "A generated mypy object has unexpected fields."
    }
    for ($index = 0; $index -lt $actual.Count; $index += 1) {
        if ($actual[$index] -cne $expectedKeys[$index]) {
            throw "A generated mypy object has unexpected fields."
        }
    }
}

function Initialize-GeneratedMypyTagContracts {
    if ($script:GeneratedMypyTagContractsReady) {
        return
    }
    $configuration = Get-GeneratedArtifactSnapshot -Path (
        Join-Path $repoRoot "pyproject.toml"
    )
    foreach ($versionPin in @('"mypy==1.17.1"', '"ruff==0.12.11"')) {
        if ([regex]::Matches(
            $configuration.Text,
            '(?m)^\s*' + [regex]::Escape($versionPin) + ',?\s*$'
        ).Count -ne 1) {
            throw "The generated-cache dependency pin is not approved."
        }
    }
    # Exact installed source bytes fix the generator contract, not just its name.
    $generatorFiles = @(
        @(".venv/Lib/site-packages/mypy/build.py", [string]::Concat(
            "39ab55ee", "435e3502", "746d0815", "3b58bec5",
            "3c1337f1", "e1866b2d", "d772d996", "07954109"
        )),
        @(".venv/Lib/site-packages/mypy/util.py", [string]::Concat(
            "e5b9c7c1", "61208a2d", "b1d3118c", "2fb68733",
            "d05c70a2", "fb0e5528", "767dc755", "88afef48"
        )),
        @(".venv/Lib/site-packages/mypy/fscache.py", [string]::Concat(
            "8332244b", "385dddbc", "0abac4b1", "a3322426",
            "915aef31", "bcc294a8", "c55aa7a7", "dd0297da"
        )),
        @(".venv/Lib/site-packages/mypy/version.py", [string]::Concat(
            "16b395e0", "3029ee19", "fe923579", "3ad30099",
            "af59b6ca", "a6020183", "0bef22ad", "6d79a803"
        )),
        @(".venv/Lib/site-packages/mypy-1.17.1.dist-info/METADATA", [string]::Concat(
            "21d96289", "f85dd46c", "b7314101", "54ed04ca",
            "3936aabb", "3d99d344", "ed73ad1a", "49c6bcd2"
        )),
        @(".venv/Lib/site-packages/ruff-0.12.11.dist-info/METADATA", [string]::Concat(
            "e23710ec", "38b3a13d", "0243d82c", "51ffb81c",
            "f509aa7b", "7472fb12", "e2e2cf1e", "e5a7d67e"
        ))
    )
    foreach ($generatorFile in $generatorFiles) {
        $snapshot = Get-GeneratedArtifactSnapshot -Path (
            Join-Path $repoRoot $generatorFile[0]
        )
        if ($snapshot.Sha256 -cne $generatorFile[1]) {
            throw "The installed mypy/cache-tag generator contract changed."
        }
    }
    $ruffGenerator = Get-GeneratedArtifactSnapshot -Binary -Path (
        Join-Path $repoRoot ".venv/Scripts/ruff.exe"
    )
    $ruffGeneratorHash = [string]::Concat(
        "66b0cc1f", "026238af", "404aa2a5", "b6e54362",
        "fec4b3e5", "116a9ade", "d367e28f", "85fd6657"
    )
    if ($ruffGenerator.Sha256 -cne $ruffGeneratorHash) {
        throw "The installed Ruff cache-tag generator contract changed."
    }
    $script:GeneratedMypyTagContractsReady = $true
}

function Assert-GeneratedMypyModuleName {
    param([object] $Value)

    if (
        $Value -isnot [string] -or
        $Value -cnotmatch '^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$' -or
        $Value -cmatch '[0-9a-f]{32,}'
    ) {
        throw "A generated mypy module reference is not canonical."
    }
}

function Get-ValidatedMypyCacheHashProof {
    param([Parameter(Mandatory = $true)][string] $Path)

    Initialize-GeneratedMypyTagContracts
    $metadata = Get-GeneratedArtifactSnapshot -Path $Path
    if (-not $metadata.Path.EndsWith(".meta.json", [StringComparison]::Ordinal)) {
        throw "A generated mypy metadata path is not approved."
    }
    $meta = ConvertFrom-StrictGeneratedJson -Text $metadata.Text
    Assert-GeneratedMypyKeys -Object $meta -Expected @(
        "data_mtime", "dep_lines", "dep_prios", "dependencies", "hash", "id",
        "ignore_all", "interface_hash", "mtime", "options", "path", "plugin_data",
        "size", "suppressed", "version_id"
    )
    if ($meta.version_id -isnot [string] -or $meta.version_id -cne "1.17.1") {
        throw "A generated mypy metadata version is not approved."
    }
    foreach ($field in @("mtime", "data_mtime", "size")) {
        if (
            $meta[$field] -isnot [long] -and $meta[$field] -isnot [int] -or
            $meta[$field] -lt 0
        ) {
            throw "A generated mypy numeric field is not canonical."
        }
    }
    if ($meta.ignore_all -isnot [bool]) {
        throw "A generated mypy Boolean field is not canonical."
    }
    Assert-GeneratedMypyModuleName -Value $meta.id
    foreach ($field in @("dependencies", "suppressed", "dep_prios", "dep_lines")) {
        if ($meta[$field] -isnot [array]) {
            throw "A generated mypy sequence has an unexpected type."
        }
    }
    if (
        ($meta.dependencies.Count + $meta.suppressed.Count) -ne $meta.dep_prios.Count -or
        ($meta.dependencies.Count + $meta.suppressed.Count) -ne $meta.dep_lines.Count
    ) {
        throw "Generated mypy dependency cardinalities do not match."
    }
    foreach ($field in @("dependencies", "suppressed")) {
        $seenModules = [System.Collections.Generic.HashSet[string]]::new(
            [StringComparer]::Ordinal
        )
        foreach ($module in $meta[$field]) {
            Assert-GeneratedMypyModuleName -Value $module
            if (-not $seenModules.Add($module)) {
                throw "A generated mypy dependency is duplicated."
            }
        }
    }
    foreach ($field in @("dep_prios", "dep_lines")) {
        foreach ($number in $meta[$field]) {
            if (($number -isnot [long] -and $number -isnot [int]) -or $number -lt 0) {
                throw "A generated mypy dependency number is not canonical."
            }
        }
    }
    $expectedOptions = @{
        allow_redefinition = $false; allow_redefinition_new = $false
        allow_untyped_globals = $false; bazel = $false; check_untyped_defs = $true
        disable_bytearray_promotion = $true; disable_memoryview_promotion = $true
        disallow_any_decorated = $false; disallow_any_explicit = $false
        disallow_any_expr = $false; disallow_any_generics = $true
        disallow_any_unimported = $false; disallow_incomplete_defs = $true
        disallow_subclassing_any = $true; disallow_untyped_calls = $true
        disallow_untyped_decorators = $true; disallow_untyped_defs = $true
        extra_checks = $true; follow_imports_for_stubs = $false
        follow_untyped_imports = $false; ignore_errors = $false
        ignore_missing_imports = $false; implicit_optional = $false
        implicit_reexport = $false; local_partial_types = $false; mypyc = $false
        old_type_inference = $false; strict_bytes = $true; strict_concatenate = $false
        strict_equality = $true; strict_optional = $true; warn_no_return = $true
        warn_return_any = $true; warn_unreachable = $false; warn_unused_ignores = $true
        follow_imports = "normal"; platform = "win32"
        always_false = @(); always_true = @(); disable_error_code = @()
        disabled_error_codes = @(); enable_error_code = @(); enabled_error_codes = @()
        plugins = @("pydantic.mypy")
    }
    Assert-GeneratedMypyKeys -Object $meta.options -Expected @($expectedOptions.Keys)
    foreach ($key in $expectedOptions.Keys) {
        $expected = $expectedOptions[$key]
        $actual = $meta.options[$key]
        if ($expected -is [bool]) {
            if ($actual -isnot [bool] -or $actual -ne $expected) {
                throw "A generated mypy option is not approved."
            }
        }
        elseif ($expected -is [string]) {
            if ($actual -isnot [string] -or $actual -cne $expected) {
                throw "A generated mypy option is not approved."
            }
        }
        else {
            if ($actual -isnot [array] -or $actual.Count -ne $expected.Count) {
                throw "A generated mypy option sequence is not approved."
            }
            for ($index = 0; $index -lt $expected.Count; $index += 1) {
                if ($actual[$index] -isnot [string] -or $actual[$index] -cne $expected[$index]) {
                    throw "A generated mypy option sequence is not approved."
                }
            }
        }
    }
    if (
        $meta.plugin_data -isnot [array] -or $meta.plugin_data.Count -ne 2 -or
        $null -ne $meta.plugin_data[1]
    ) {
        throw "Generated mypy plugin data is not approved."
    }
    $pluginKeys = @(
        "debug_dataclass_transform", "init_forbid_extra", "init_typed",
        "warn_required_dynamic_aliases"
    )
    Assert-GeneratedMypyKeys -Object $meta.plugin_data[0] -Expected $pluginKeys
    foreach ($key in $pluginKeys) {
        if ($meta.plugin_data[0][$key] -isnot [bool] -or $meta.plugin_data[0][$key]) {
            throw "Generated mypy plugin data is not approved."
        }
    }
    foreach ($field in @("hash", "interface_hash")) {
        if ($meta[$field] -isnot [string] -or $meta[$field] -cnotmatch '^[0-9a-f]{40}$') {
            throw "A generated mypy digest field is not canonical."
        }
    }
    if (
        $meta.path -isnot [string] -or [string]::IsNullOrWhiteSpace($meta.path) -or
        $meta.path -match '(^|[\\/])\.{1,2}([\\/]|$)' -or
        $meta.path.StartsWith("\\")
    ) {
        throw "A generated mypy source reference is not canonical."
    }
    $sourcePath = if ([IO.Path]::IsPathRooted($meta.path)) {
        [IO.Path]::GetFullPath($meta.path)
    }
    else {
        [IO.Path]::GetFullPath((Join-Path $repoRoot $meta.path))
    }
    $repositoryPrefix = [IO.Path]::GetFullPath($repoRoot).TrimEnd([char] 92, [char] 47) +
        [IO.Path]::DirectorySeparatorChar
    $sourceName = [IO.Path]::GetFileNameWithoutExtension($sourcePath)
    if (
        -not $sourcePath.StartsWith($repositoryPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        [IO.Path]::GetExtension($sourcePath) -cnotin @(".py", ".pyi") -or
        $sourcePath.Substring([IO.Path]::GetPathRoot($sourcePath).Length).Contains(":") -or
        ($sourceName -cne "__init__" -and $sourceName -cne $meta.id.Split(".")[-1])
    ) {
        throw "A generated mypy source is outside its approved scope."
    }
    $companionPath = $metadata.Path.Substring(0, $metadata.Path.Length - 10) + ".data.json"
    $source = Get-GeneratedArtifactSnapshot -Path $sourcePath
    $companion = Get-GeneratedArtifactSnapshot -Path $companionPath
    $sourceHash = [Convert]::ToHexString(
        [Security.Cryptography.SHA1]::HashData($source.Bytes)
    ).ToLowerInvariant()
    $interfaceHash = [Convert]::ToHexString(
        [Security.Cryptography.SHA1]::HashData($companion.Bytes)
    ).ToLowerInvariant()
    if (
        $meta.hash -cne $sourceHash -or $meta.interface_hash -cne $interfaceHash -or
        $meta.size -ne $source.Size
    ) {
        throw "A generated mypy digest does not match its exact input bytes."
    }
    # The exception key has no JSON pointer. Every literal occurrence must be
    # inside one of the two exact, unescaped digest fields; schema checks above
    # also reject escaped/duplicate/unknown-field attempts.
    $validatedValues = @($sourceHash, $interfaceHash | Sort-Object -Unique -CaseSensitive)
    foreach ($value in $validatedValues) {
        # A UUID-containing safe source path is not a blanket entropy exception.
        # The actual allowed digest may not occur in the parsed path, including
        # JSON-escaped representations invisible to the literal count below.
        if ($meta.path.Contains($value, [StringComparison]::Ordinal)) {
            throw "A generated mypy digest occurs in a forbidden source-reference field."
        }
        $expectedOccurrences = [int]($sourceHash -ceq $value) + [int]($interfaceHash -ceq $value)
        $literalOccurrences = [regex]::Matches($metadata.Text, [regex]::Escape($value)).Count
        $fieldOccurrences = [regex]::Matches(
            $metadata.Text,
            '"(?:hash|interface_hash)"\s*:\s*"' + [regex]::Escape($value) + '"'
        ).Count
        if ($literalOccurrences -ne $expectedOccurrences -or $fieldOccurrences -ne $expectedOccurrences) {
            throw "A generated mypy digest occurs outside its exact approved fields."
        }
    }
    foreach ($quotedHex in [regex]::Matches($metadata.Text, '"([0-9a-fA-F]{32,})"')) {
        if ($quotedHex.Groups[1].Value -cnotin $validatedValues) {
            throw "Generated mypy metadata contains an unexplained quoted hexadecimal value."
        }
    }
    return [pscustomobject]@{ Path = $metadata.Path; Values = $validatedValues; InputRecords = @() }
}

function Get-ValidatedCacheTagProof {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][ValidateSet("Mypy", "Ruff")][string] $Kind
    )

    Initialize-GeneratedMypyTagContracts
    $tag = Get-GeneratedArtifactSnapshot -Path $Path
    $publicMarker = [string]::Concat("8a477f59", "7d28d172", "789f0688", "6806bc55")
    $expectedText = "Signature: " + $publicMarker
    if ($Kind -ceq "Mypy") {
        $expectedText += "`r`n# This file is a cache directory tag automatically created by mypy."
        $expectedText += "`r`n# For information about cache directory tags see https://bford.info/cachedir/`r`n"
    }
    $expectedBytes = [Text.Encoding]::UTF8.GetBytes($expectedText)
    if ($tag.Bytes.Length -ne $expectedBytes.Length) {
        throw "A cache directory tag does not match its complete approved bytes."
    }
    for ($index = 0; $index -lt $expectedBytes.Length; $index += 1) {
        if ($tag.Bytes[$index] -ne $expectedBytes[$index]) {
            throw "A cache directory tag does not match its complete approved bytes."
        }
    }
    return [pscustomobject]@{ Path = $tag.Path; Values = @($publicMarker); InputRecords = @() }
}

function Get-ApprovedTypeScriptProofProducer {
    Assert-ApprovedTypeScriptPackage
    $libraryPath = Join-Path $repoRoot "node_modules\typescript\lib\typescript.js"
    $library = Get-GeneratedArtifactSnapshot -Path $libraryPath
    if ($library.Sha256 -cne (Get-ApprovedTypeScriptLibrarySha256)) {
        throw "TypeScript producer library differs from proved installed contract."
    }
    $node = Assert-PhaseNodeRuntime
    $npm = Get-PhaseNpmCommandPath
    $offlineGuard = Join-Path $repoRoot "scripts\node_offline_guard.cjs"
    $preflight = Join-Path $repoRoot "scripts\node_runtime_preflight.cjs"
    foreach ($path in @($offlineGuard, $preflight)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "An approved TypeScript producer guard is missing."
        }
        $null = Get-GeneratedArtifactSnapshot -Path $path
    }
    $null = Get-GeneratedArtifactSnapshot -Path (Join-Path $repoRoot "apps\web\tsconfig.json")
    Assert-SafeMutableRepositoryFile -Path (Join-Path $repoRoot "apps\web\next-env.d.ts")
    return [pscustomobject]@{
        Node = $node; Npm = $npm; OfflineGuard = $offlineGuard; Preflight = $preflight
    }
}

function New-TypeScriptGeneratedProofSnapshot {
    param([Parameter(Mandatory = $true)][string] $ProofRoot)

    $producer = Get-ApprovedTypeScriptProofProducer
    $canonical = [System.IO.Path]::GetFullPath(
        (Join-Path $repoRoot "apps\web\.next\cache\tsconfig.tsbuildinfo")
    )
    Assert-SafeMutableRepositoryFile -Path $canonical
    $existed = Test-Path -LiteralPath $canonical -PathType Leaf
    $original = if ($existed) { [System.IO.File]::ReadAllBytes($canonical) } else { $null }
    $script:TypeScriptCanonicalState = [pscustomobject]@{
        Path = $canonical
        Existed = $existed
        OriginalBytes = $original
        OriginalSize = if ($existed) { $original.Length } else { 0 }
        OriginalSha256 = if ($existed) { Get-GeneratedSha256HexFromBytes -Bytes $original } else { $null }
    }
    Write-Host "TypeScript canonical PRE: existed=$existed; size=$($script:TypeScriptCanonicalState.OriginalSize); sha256=$($script:TypeScriptCanonicalState.OriginalSha256)"
    if ($existed) { Remove-Item -LiteralPath $canonical -Force }

    $environmentNames = @("NODE_OPTIONS", "NPM_CONFIG_OFFLINE",
        "NEXT_IGNORE_INCORRECT_LOCKFILE", "NEXT_DISABLE_SWC_WASM")
    $previousEnvironment = @{}
    foreach ($name in $environmentNames) {
        $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
    }
    Push-Location -LiteralPath $repoRoot
    try {
        $env:NODE_OPTIONS = '--require="' + $producer.OfflineGuard.Replace("\", "/") + '"'
        $env:NPM_CONFIG_OFFLINE = "true"
        $env:NEXT_IGNORE_INCORRECT_LOCKFILE = "1"
        $env:NEXT_DISABLE_SWC_WASM = "1"
        Assert-NpmDependencyTreeClean
        Invoke-Checked -FilePath $producer.Node -ArgumentList @($producer.Preflight)
        Invoke-Checked -FilePath $producer.Npm -ArgumentList @(
            "run", "typecheck", "--workspace", "apps/web"
        )
    }
    finally {
        Pop-Location
        foreach ($name in $environmentNames) {
            [Environment]::SetEnvironmentVariable(
                $name, $previousEnvironment[$name], "Process"
            )
        }
    }
    if (-not (Test-Path -LiteralPath $canonical -PathType Leaf)) {
        throw "TYPESCRIPT BUILD-INFO NOT REPRODUCED"
    }
    Assert-SafeMutableRepositoryFile -Path $canonical
    $fresh = Get-GeneratedArtifactSnapshot -Path $canonical
    $proofDirectory = Join-Path $ProofRoot "typescript"
    [System.IO.Directory]::CreateDirectory($proofDirectory) | Out-Null
    Assert-NoReparsePointInPath -Path $proofDirectory
    $proofPath = Join-Path $proofDirectory "tsconfig.tsbuildinfo"
    if (Test-Path -LiteralPath $proofPath) {
        throw "A TypeScript proof snapshot already exists."
    }
    [System.IO.File]::WriteAllBytes($proofPath, $fresh.Bytes)
    $proof = Get-GeneratedArtifactSnapshot -Path $proofPath
    if ($proof.Size -ne $fresh.Size -or $proof.Sha256 -cne $fresh.Sha256) {
        throw "The TypeScript proof snapshot differs from fresh producer output."
    }
    Assert-GeneratedProofInputsUnchanged
    Write-Host "Fresh TypeScript proof produced and copied: size=$($proof.Size); sha256=$($proof.Sha256)"
}

function Restore-TypeScriptCanonicalState {
    if ($null -eq $script:TypeScriptCanonicalState) { return }
    $state = $script:TypeScriptCanonicalState
    Assert-SafeMutableRepositoryFile -Path $state.Path
    if (Test-Path -LiteralPath $state.Path) {
        Remove-Item -LiteralPath $state.Path -Force
    }
    if ($state.Existed) {
        [System.IO.File]::WriteAllBytes($state.Path, $state.OriginalBytes)
        Assert-SafeMutableRepositoryFile -Path $state.Path
        $restored = [System.IO.File]::ReadAllBytes($state.Path)
        if ($restored.Length -ne $state.OriginalSize -or
            (Get-GeneratedSha256HexFromBytes -Bytes $restored) -cne $state.OriginalSha256) {
            throw "The pre-existing TypeScript build-info was not restored exactly."
        }
    }
    elseif (Test-Path -LiteralPath $state.Path) {
        throw "The scanner-created TypeScript build-info was not removed."
    }
    $script:TypeScriptCanonicalState = $null
    Write-Host "TypeScript canonical build-info PRE state restored."
}

function Get-FreshCanonicalTypeScriptRegistrationProof {
    param([Parameter(Mandatory = $true)][object] $GeneratedProof)

    if ($null -eq $script:TypeScriptCanonicalState -or
        $GeneratedProof.Kind -cne "TypeScript") {
        throw "A fresh TypeScript proof is required for repository registration."
    }
    $canonical = Get-GeneratedArtifactSnapshot -Path $script:TypeScriptCanonicalState.Path
    $snapshot = Get-GeneratedArtifactSnapshot -Path $GeneratedProof.Proof.Path
    if ($canonical.Size -ne $snapshot.Size -or $canonical.Sha256 -cne $snapshot.Sha256) {
        throw "The repository TypeScript artifact differs from its scanner-owned proof."
    }
    return [pscustomobject]@{
        Kind = "TypeScript"
        Proof = [pscustomobject]@{
            Path = $canonical.Path
            Values = $GeneratedProof.Proof.Values
            SourceVersionCount = $GeneratedProof.Proof.SourceVersionCount
            InputRecords = @()
        }
    }
}

function New-GeneratedArtifactProofCorpus {
    param([Parameter(Mandatory = $true)][string] $ProofRoot)

    $root = Assert-GeneratedProofRootIdentity -Path $ProofRoot
    if (Test-Path -LiteralPath $root) {
        throw "A generated-artifact proof workspace already exists."
    }
    [System.IO.Directory]::CreateDirectory($root) | Out-Null
    Assert-NoReparsePointInPath -Path $root
    $script:GeneratedProofRoot = $root

    # Validate the existing exact tool and generator byte pins before either
    # producer runs. The native Ruff executable is the one pinned here.
    $script:GeneratedMypyTagContractsReady = $false
    Initialize-GeneratedMypyTagContracts
    $ruffExecutable = [System.IO.Path]::GetFullPath(
        (Join-Path $repoRoot ".venv\Scripts\ruff.exe")
    )
    $null = Get-GeneratedArtifactSnapshot -Path $ruffExecutable -Binary
    $ruffVersion = @(& $ruffExecutable --version) -join ""
    if ($LASTEXITCODE -ne 0 -or $ruffVersion -cne "ruff 0.12.11") {
        throw "The pinned Ruff producer version does not match."
    }

    $mypyCache = Join-Path $root "mypy-cache"
    $ruffCache = Join-Path $root "ruff-cache"
    Push-Location -LiteralPath $repoRoot
    try {
        Invoke-Checked -FilePath $python -ArgumentList @(
            Get-GuardedPythonModuleArguments -Module "mypy" -ArgumentList @(
                "--cache-dir", $mypyCache, "services/api/src"
            )
        )
        Invoke-Checked -FilePath $ruffExecutable -ArgumentList @(
            "check", "--cache-dir", $ruffCache, "services/api/src"
        )
    }
    finally { Pop-Location }
    New-TypeScriptGeneratedProofSnapshot -ProofRoot $root
    Assert-GeneratedProofInputsUnchanged
    Assert-GeneratedProofTreeSafe -Path $root
    Write-Host "Generated-artifact proof corpus produced by pinned mypy, Ruff and TypeScript."
}

function Get-GeneratedArtifactExceptionProofs {
    param([Parameter(Mandatory = $true)][string] $ProofRoot)

    $script:GeneratedProofInputRecords = @{}
    $script:GeneratedMypyTagContractsReady = $false
    $proofs = [System.Collections.Generic.List[object]]::new()
    $mypyRoot = Join-Path $ProofRoot "mypy-cache\3.13"
    Assert-SafeGeneratedProofInputPath -Path $mypyRoot
    $metadataFiles = @(Get-ChildItem -LiteralPath $mypyRoot -Recurse -File -Force -Filter "*.meta.json")
    if ($metadataFiles.Count -ne 861) {
        throw "The approved mypy artifact population has changed."
    }
    foreach ($file in $metadataFiles) {
        $proofs.Add([pscustomobject]@{
            Kind = "Mypy"; Proof = Get-ValidatedMypyCacheHashProof -Path $file.FullName
        })
    }
    foreach ($kind in @("Mypy", "Ruff")) {
        $tagPath = Join-Path $ProofRoot ($kind.ToLowerInvariant() + "-cache\CACHEDIR.TAG")
        $proofs.Add([pscustomobject]@{
            Kind = "Tag"; Proof = Get-ValidatedCacheTagProof -Path $tagPath -Kind $kind
        })
    }
    $proofs.Add([pscustomobject]@{
        Kind = "TypeScript"; Proof = Get-ValidatedTypeScriptBuildInfoProof -Path (
            Join-Path $ProofRoot "typescript\tsconfig.tsbuildinfo"
        )
    })
    Assert-GeneratedProofInputsUnchanged
    return $proofs.ToArray()
}

function Get-GeneratedArtifactRegistrationPlan {
    param([object[]] $Proofs, [object] $Scan, [string] $ScanJsonPath)

    Assert-GeneratedProofInputsUnchanged
    $scanSnapshot = Get-GeneratedArtifactSnapshot -Path $ScanJsonPath
    # Inspect raw JSON before ConvertFrom-Json can collapse duplicate properties.
    $null = ConvertFrom-StrictGeneratedJson -Text $scanSnapshot.Text
    $parsedScan = ConvertFrom-Json -InputObject $scanSnapshot.Text -ErrorAction Stop
    if (
        $Scan -isnot [pscustomobject] -or $parsedScan -isnot [pscustomobject] -or
        (ConvertTo-Json -InputObject $parsedScan -Depth 100 -Compress) -cne
            (ConvertTo-Json -InputObject $Scan -Depth 100 -Compress) -or
        $Scan.results -isnot [pscustomobject] -or
        $Scan.serial_scan.completed -isnot [array]
    ) {
        throw "The generated finding result is malformed or differs from its exact JSON snapshot."
    }

    $artifacts = @{}
    $proofKeys = @{}
    $proofCounts = @{ Mypy = 0; Tag = 0; TypeScript = 0 }
    $artifactCounts = @{ Mypy = 0; Tag = 0; TypeScript = 0 }
    foreach ($record in $Proofs) {
        if ($record.Kind -cnotin @("Mypy", "Tag", "TypeScript") -or
            $record.Proof.Values -isnot [array] -or $record.Proof.Values.Count -eq 0) {
            throw "A generated proof record is malformed."
        }
        $path = [System.IO.Path]::GetFullPath($record.Proof.Path).ToLowerInvariant()
        if ($artifacts.ContainsKey($path) -or -not $script:GeneratedProofInputRecords.ContainsKey($path)) {
            throw "A generated proof path is duplicated or lacks an exact input snapshot."
        }
        $artifacts[$path] = $record
        $artifactCounts[$record.Kind] += 1
        foreach ($value in $record.Proof.Values) {
            if ($value -isnot [string] -or $value -cnotmatch '^[0-9a-f]{32,64}$') {
                throw "A generated proof value is not canonical."
            }
            $fingerprint = Get-Sha1Hex -Value $value
            $key = $path + "|1|" + $fingerprint
            if ($proofKeys.ContainsKey($key)) { throw "A generated proof key is duplicated." }
            $proofKeys[$key] = [pscustomobject]@{
                Path = $path; FindingKey = ("1|" + $fingerprint); Kind = $record.Kind
            }
            $proofCounts[$record.Kind] += 1
        }
    }

    $completed = @{}
    foreach ($record in $Scan.serial_scan.completed) {
        $fields = @($record.PSObject.Properties.Name)
        if ($record -isnot [pscustomobject] -or $fields.Count -ne 4 -or
            @($fields | Where-Object { $_ -cnotin @("full_path", "scan_path", "size", "sha256") }).Count -ne 0 -or
            $record.full_path -isnot [string] -or $record.scan_path -isnot [string] -or
            $record.sha256 -isnot [string] -or $record.sha256 -cnotmatch '^[0-9a-f]{64}$' -or
            ($record.size -isnot [long] -and $record.size -isnot [int]) -or $record.size -lt 0) {
            throw "A generated scan completion record is malformed."
        }
        $path = [System.IO.Path]::GetFullPath($record.full_path).ToLowerInvariant()
        $scanPath = if ([System.IO.Path]::IsPathRooted($record.scan_path)) {
            [System.IO.Path]::GetFullPath($record.scan_path)
        }
        else { [System.IO.Path]::GetFullPath((Join-Path $repoRoot $record.scan_path)) }
        if ($path -cne $scanPath.ToLowerInvariant() -or $completed.ContainsKey($path)) {
            throw "A generated scan completion path is mismatched or duplicated."
        }
        $completed[$path] = $record
    }
    foreach ($path in $artifacts.Keys) {
        if (-not $completed.ContainsKey($path)) { throw "A generated proof input lacks detector completion." }
        $snapshot = $script:GeneratedProofInputRecords[$path]
        $record = $completed[$path]
        if ($record.sha256 -cne $snapshot.Sha256 -or $record.size -ne $snapshot.Size) {
            throw "Generated proof and detector input snapshots do not match."
        }
    }

    $findingKeys = @{}
    $counts = @{ Mypy = 0; Tag = 0; TypeScript = 0 }
    $resultPaths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($property in $Scan.results.PSObject.Properties) {
        $path = if ([System.IO.Path]::IsPathRooted($property.Name)) {
            [System.IO.Path]::GetFullPath($property.Name).ToLowerInvariant()
        }
        else { [System.IO.Path]::GetFullPath((Join-Path $repoRoot $property.Name)).ToLowerInvariant() }
        if (-not $resultPaths.Add($path) -or -not $completed.ContainsKey($path)) {
            throw "A generated result path is duplicated or is outside the completed scan."
        }
        if (-not $artifacts.ContainsKey($path)) {
            # Other families stay under their existing scanner handling. Never
            # extend generated exceptions to another file, even for the same value.
            $relative = [System.IO.Path]::GetRelativePath($repoRoot, $path).Replace("\", "/")
            $proofPrefix = if ($null -ne $script:GeneratedProofRoot) {
                $script:GeneratedProofRoot.TrimEnd([char] 92, [char] 47) +
                    [System.IO.Path]::DirectorySeparatorChar
            }
            if (($null -ne $proofPrefix -and
                $path.StartsWith($proofPrefix, [StringComparison]::OrdinalIgnoreCase)) -or
                $relative -match '^\.mypy_cache/3\.13/.+\.meta\.json$' -or
                $relative -in @(".mypy_cache/CACHEDIR.TAG", ".ruff_cache/CACHEDIR.TAG",
                    "apps/web/.next/cache/tsconfig.tsbuildinfo")) {
                throw "A generated-family result lacks a validated artifact proof."
            }
            continue
        }
        if ($property.Value -isnot [array] -or $property.Value.Count -eq 0) {
            throw "A generated finding list is malformed."
        }
        foreach ($finding in $property.Value) {
            $fields = @($finding.PSObject.Properties.Name)
            if ($finding -isnot [pscustomobject] -or $fields.Count -ne 5 -or
                @($fields | Where-Object { $_ -cnotin @("type", "filename", "hashed_secret", "is_verified", "line_number") }).Count -ne 0 -or
                $finding.type -cne "Hex High Entropy String" -or
                $finding.filename -isnot [string] -or
                $finding.hashed_secret -isnot [string] -or $finding.hashed_secret -cnotmatch '^[0-9a-f]{40}$' -or
                $finding.is_verified -isnot [bool] -or
                ($finding.line_number -isnot [long] -and $finding.line_number -isnot [int]) -or
                $finding.line_number -ne 1) {
                throw "A generated finding has an unapproved type, line, or schema."
            }
            $findingPath = if ([System.IO.Path]::IsPathRooted($finding.filename)) {
                [System.IO.Path]::GetFullPath($finding.filename).ToLowerInvariant()
            }
            else { [System.IO.Path]::GetFullPath((Join-Path $repoRoot $finding.filename)).ToLowerInvariant() }
            $key = $path + "|1|" + $finding.hashed_secret
            if ($findingPath -cne $path -or -not $proofKeys.ContainsKey($key) -or $findingKeys.ContainsKey($key)) {
                throw "A generated finding is unexplained, path-mismatched, or duplicated."
            }
            $findingKeys[$key] = $proofKeys[$key]
            $counts[$artifacts[$path].Kind] += 1
        }
    }
    Assert-GeneratedProofInputsUnchanged
    return [pscustomobject]@{
        ProofKeys = $proofKeys; FindingKeys = $findingKeys
        ProofCounts = $proofCounts; FindingCounts = $counts; ArtifactCounts = $artifactCounts
    }
}

function Publish-GeneratedArtifactRegistrationPlan {
    param([Parameter(Mandatory = $true)][object] $Plan)

    # Build a detached copy. No live exception map mutation can precede complete
    # proof/result validation, population checks (caller), and the final drift check.
    $next = @{}
    foreach ($path in $script:AllowedArtifactSecretHashes.Keys) {
        $next[$path] = [System.Collections.Generic.HashSet[string]]::new(
            $script:AllowedArtifactSecretHashes[$path], [System.StringComparer]::OrdinalIgnoreCase
        )
    }
    foreach ($key in $Plan.ProofKeys.Keys) {
        $record = $Plan.ProofKeys[$key]
        if ($next.ContainsKey($record.Path) -and $next[$record.Path].Contains($record.FindingKey)) {
            throw "A generated key already exists outside this new registration delta."
        }
    }
    foreach ($key in $Plan.FindingKeys.Keys) {
        if (-not $Plan.ProofKeys.ContainsKey($key)) { throw "A generated registration has no proof." }
        $record = $Plan.FindingKeys[$key]
        if (-not $next.ContainsKey($record.Path)) {
            $next[$record.Path] = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
        }
        if (-not $next[$record.Path].Add($record.FindingKey)) { throw "A generated registration key is duplicated." }
    }
    $applied = 0
    $proofOnly = 0
    foreach ($key in $Plan.ProofKeys.Keys) {
        $record = $Plan.ProofKeys[$key]
        $registered = $next.ContainsKey($record.Path) -and $next[$record.Path].Contains($record.FindingKey)
        if ($Plan.FindingKeys.ContainsKey($key)) {
            if (-not $registered) { throw "A generated finding did not receive its exact key." }
            $applied += 1
        }
        else {
            if ($registered) { throw "A proof-only value inherited an exception." }
            $proofOnly += 1
        }
    }
    Assert-GeneratedProofInputsUnchanged
    $script:AllowedArtifactSecretHashes = $next
    return [pscustomobject]@{
        ProofKeys = $Plan.ProofKeys.Count; Findings = $Plan.FindingKeys.Count
        NewKeys = $Plan.FindingKeys.Count; AppliedFindings = $applied; ProofOnlyUnregistered = $proofOnly
    }
}

function Add-ValidatedGeneratedArtifactExceptions {
    param([object[]] $Proofs, [object] $Scan, [string] $ScanJsonPath)

    $plan = Get-GeneratedArtifactRegistrationPlan -Proofs $Proofs -Scan $Scan -ScanJsonPath $ScanJsonPath
    if ($plan.FindingCounts.Mypy -ne 1717 -or $plan.FindingCounts.Tag -ne 2 -or
        $plan.FindingCounts.TypeScript -ne 696 -or $plan.ProofCounts.Mypy -ne 1722 -or
        $plan.ProofCounts.Tag -ne 2 -or $plan.ProofCounts.TypeScript -ne 696 -or
        $plan.ArtifactCounts.Mypy -ne 861 -or $plan.ArtifactCounts.Tag -ne 2 -or
        $plan.ArtifactCounts.TypeScript -ne 1) {
        throw "The approved generated-artifact proof or finding population has changed."
    }
    $summary = Publish-GeneratedArtifactRegistrationPlan -Plan $plan
    Write-Host "Generated-artifact proof: metadata=861; tags=2; TypeScript=704/704 sources"
    Write-Host "Generated-artifact sets: P=$($summary.ProofKeys) (1722/2/696); D=$($summary.Findings) (1717/2/696); E=$($summary.NewKeys); applied=$($summary.AppliedFindings); proof-only unregistered=$($summary.ProofOnlyUnregistered)"
}

function Resolve-FrozenDiagnosticScanPath {
    param([Parameter(Mandatory = $true)][string] $Path)

    # Accept the driver's slash/backslash and absolute/relative representations,
    # but not Windows path aliases that collapse to a different literal identity.
    if ([string]::IsNullOrWhiteSpace($Path) -or $Path.Contains([char]0) -or
        $Path -match '^[\\/]{2}' -or $Path -match '[\\/]{2}' -or
        $Path -match '(^|[\\/])\.{1,2}([\\/]|$)' -or
        $Path -match '[. ]([\\/]|$)' -or $Path -match '[\\/]$' -or
        $Path -match '[<>"|?*]' -or $Path -match '(?<!^[A-Za-z]):') {
        throw "A frozen diagnostic scan path is not a literal canonical identity."
    }
    $full = if ([System.IO.Path]::IsPathRooted($Path)) {
        [System.IO.Path]::GetFullPath($Path)
    } else { [System.IO.Path]::GetFullPath((Join-Path $repoRoot $Path)) }
    $relative = [System.IO.Path]::GetRelativePath($repoRoot, $full)
    $literal = $Path.Replace("/", "\")
    if (-not [string]::Equals($literal, $full, [StringComparison]::OrdinalIgnoreCase) -and
        -not [string]::Equals($literal, $relative, [StringComparison]::OrdinalIgnoreCase)) {
        throw "A frozen diagnostic scan path uses an alias."
    }
    Assert-SafeRepositoryPath -Path $full
    return $full.ToLowerInvariant()
}

function Get-FrozenDiagnosticCsvRows {
    param([Parameter(Mandatory = $true)][object] $Snapshot)

    # Pure structural parser, also exercised directly by private synthetic tests.
    # The production caller independently enforces the immutable whole-file pin.
    $text = [System.Text.UTF8Encoding]::new($false, $true).GetString($Snapshot.Bytes)
    $lines = $text.Split("`n")
    if ($text.Contains("`r") -or $text.Contains([char]0) -or
        $lines.Count -ne 261 -or $lines[260].Length -ne 0 -or
        -not [string]::Equals($lines[0], "path,before_sha256,after_scan_sha256,comparison", [StringComparison]::Ordinal)) {
        throw "The frozen diagnostic CSV has an invalid physical format or header."
    }
    $paths = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $rows = [System.Collections.Generic.List[object]]::new()
    for ($index = 1; $index -lt 260; $index += 1) {
        $match = [regex]::Match($lines[$index], '^"([^"\r\n]+)","([0-9a-f]{64})","([0-9a-f]{64})","UNCHANGED"$')
        if (-not $match.Success) { throw "A frozen diagnostic CSV row is malformed." }
        $sourcePath = $match.Groups[1].Value
        $before = $match.Groups[2].Value
        if ($before -cne $match.Groups[3].Value -or
            $sourcePath -cnotmatch '^[A-Za-z0-9_.\[\]-]+(?:/[A-Za-z0-9_.\[\]-]+)*$' -or
            $sourcePath -match '(^|/)\.{1,2}(/|$)|[.](/|$)|[0-9a-fA-F]{64}' -or
            -not $paths.Add($sourcePath)) {
            throw "A frozen diagnostic row has unequal digests, duplicate path, or a forbidden-field value."
        }
        # Do not read/re-hash current sources here. These are historical digests,
        # approved by the one-off direct source-byte provenance gate.
        $rows.Add([pscustomobject]@{ LineNumber = $index + 1; Fingerprint = (Get-Sha1Hex -Value $before) })
    }
    return ,$rows.ToArray()
}

function Get-FrozenDiagnosticSnapshotProof {
    # No production path/digest overrides and no TOFU receipt or classification.
    Assert-SafeRepositoryPath -Path $script:FrozenDiagnosticSnapshotPath
    if (-not (Test-Path -LiteralPath $script:FrozenDiagnosticSnapshotPath)) { return $null }
    $snapshot = Get-GeneratedArtifactSnapshot -Path $script:FrozenDiagnosticSnapshotPath
    $approvedDigest = [string]::Concat(
        "758fae48", "eb3aaff7", "61195dec", "da95e74d",
        "ed793770", "0f3dd1b9", "eec04a4e", "7b6d3cc9"
    )
    if ($snapshot.Size -ne 49504 -or $snapshot.Sha256 -cne $approvedDigest) {
        throw "The frozen diagnostic CSV differs from its sole approved byte version."
    }
    $rows = Get-FrozenDiagnosticCsvRows -Snapshot $snapshot
    return [pscustomobject]@{ Path = $snapshot.Path.ToLowerInvariant(); Snapshot = $snapshot; Rows = $rows }
}

function Get-FrozenDiagnosticFindingKey {
    param([string] $FindingPath, [object] $Finding)

    $fields = @($Finding.PSObject.Properties.Name)
    if ($Finding -isnot [pscustomobject] -or $fields.Count -ne 5 -or
        @($fields | Where-Object { $_ -cnotin @("type", "filename", "hashed_secret", "is_verified", "line_number") }).Count -ne 0 -or
        $Finding.type -isnot [string] -or -not [string]::Equals($Finding.type, "Hex High Entropy String", [StringComparison]::Ordinal) -or
        $Finding.filename -isnot [string] -or
        $Finding.hashed_secret -isnot [string] -or $Finding.hashed_secret -cnotmatch '^[0-9a-f]{40}$' -or
        $Finding.is_verified -isnot [bool] -or
        ($Finding.line_number -isnot [int] -and $Finding.line_number -isnot [long]) -or
        $Finding.line_number -lt 1 -or $Finding.line_number -gt [int]::MaxValue) {
        throw "A frozen diagnostic finding has an unapproved type, line, or schema."
    }
    $path = Resolve-FrozenDiagnosticScanPath -Path $FindingPath
    if (-not [string]::Equals((Resolve-FrozenDiagnosticScanPath -Path $Finding.filename), $path, [StringComparison]::Ordinal)) {
        throw "A frozen diagnostic finding filename differs from its result identity."
    }
    return $path + "|" + [string]$Finding.line_number + "|Hex High Entropy String|" + $Finding.hashed_secret
}

function Get-FrozenDiagnosticRegistrationPlan {
    param([object] $Proof, [object] $Scan, [string] $ScanJsonPath)

    Assert-GeneratedProofInputsUnchanged
    $scanSnapshot = Get-GeneratedArtifactSnapshot -Path $ScanJsonPath
    $null = ConvertFrom-StrictGeneratedJson -Text $scanSnapshot.Text
    $parsed = ConvertFrom-Json -InputObject $scanSnapshot.Text -ErrorAction Stop
    if ($Scan -isnot [pscustomobject] -or $parsed -isnot [pscustomobject] -or
        -not [string]::Equals((ConvertTo-Json -InputObject $parsed -Depth 100 -Compress),
            (ConvertTo-Json -InputObject $Scan -Depth 100 -Compress), [StringComparison]::Ordinal) -or
        $Scan.results -isnot [pscustomobject] -or $Scan.serial_scan.completed -isnot [array]) {
        throw "Frozen diagnostic result differs from its exact JSON snapshot or has invalid schema."
    }
    $target = $script:FrozenDiagnosticSnapshotPath.ToLowerInvariant()
    $proofKeys = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    if ($null -ne $Proof) {
        if (-not [string]::Equals($Proof.Path, $target, [StringComparison]::Ordinal) -or
            $Proof.Rows -isnot [array] -or $Proof.Rows.Count -ne 259 -or
            -not $script:GeneratedProofInputRecords.ContainsKey($target)) {
            throw "A frozen diagnostic proof has an invalid identity or population."
        }
        foreach ($row in $Proof.Rows) {
            if (-not $proofKeys.Add($target + "|" + [string]$row.LineNumber + "|Hex High Entropy String|" + $row.Fingerprint)) {
                throw "A frozen diagnostic proof key is duplicated."
            }
        }
    }
    $completed = [System.Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    foreach ($record in $Scan.serial_scan.completed) {
        $fields = @($record.PSObject.Properties.Name)
        if ($record -isnot [pscustomobject] -or $fields.Count -ne 4 -or
            @($fields | Where-Object { $_ -cnotin @("full_path", "scan_path", "size", "sha256") }).Count -ne 0 -or
            $record.full_path -isnot [string] -or $record.scan_path -isnot [string] -or
            $record.sha256 -isnot [string] -or $record.sha256 -cnotmatch '^[0-9a-f]{64}$' -or
            ($record.size -isnot [long] -and $record.size -isnot [int]) -or $record.size -lt 0) {
            throw "A frozen diagnostic completion record is malformed."
        }
        $path = [System.IO.Path]::GetFullPath($record.full_path).ToLowerInvariant()
        $scanPath = if ([System.IO.Path]::IsPathRooted($record.scan_path)) {
            [System.IO.Path]::GetFullPath($record.scan_path).ToLowerInvariant()
        } else { [System.IO.Path]::GetFullPath((Join-Path $repoRoot $record.scan_path)).ToLowerInvariant() }
        if ([string]::Equals($path, $target, [StringComparison]::Ordinal) -or
            [string]::Equals($scanPath, $target, [StringComparison]::Ordinal)) {
            $null = Resolve-FrozenDiagnosticScanPath -Path $record.full_path
            $null = Resolve-FrozenDiagnosticScanPath -Path $record.scan_path
            if (-not [string]::Equals($scanPath, $path, [StringComparison]::Ordinal)) {
                throw "A frozen diagnostic completion identity is mismatched or duplicated."
            }
        }
        if ($scanPath -cne $path -or $completed.ContainsKey($path)) {
            throw "A frozen diagnostic completion identity is mismatched or duplicated."
        }
        $completed[$path] = $record
    }
    if ($null -ne $Proof) {
        if (-not $completed.ContainsKey($target) -or
            $completed[$target].size -ne $Proof.Snapshot.Size -or
            $completed[$target].sha256 -cne $Proof.Snapshot.Sha256) {
            throw "Frozen diagnostic proof and detector completion do not match."
        }
    } elseif ($completed.ContainsKey($target)) {
        throw "The frozen diagnostic CSV appeared after the absent-input snapshot."
    }
    $findingKeys = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $resultPaths = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($property in $Scan.results.PSObject.Properties) {
        $path = if ([System.IO.Path]::IsPathRooted($property.Name)) {
            [System.IO.Path]::GetFullPath($property.Name).ToLowerInvariant()
        } else { [System.IO.Path]::GetFullPath((Join-Path $repoRoot $property.Name)).ToLowerInvariant() }
        if (-not $resultPaths.Add($path) -or -not $completed.ContainsKey($path)) {
            throw "A frozen diagnostic result path is duplicated or uncompleted."
        }
        $isTarget = [string]::Equals($path, $target, [StringComparison]::Ordinal)
        if ($isTarget -and ($property.Value -isnot [array] -or $property.Value.Count -eq 0)) {
            throw "A frozen diagnostic finding list is malformed."
        }
        foreach ($finding in $property.Value) {
            if (-not $isTarget) {
                # Never admit another file; also detect a target finding misfiled
                # under another result key rather than silently ignoring it.
                if ($finding.filename -is [string]) {
                    $filename = if ([System.IO.Path]::IsPathRooted($finding.filename)) {
                        [System.IO.Path]::GetFullPath($finding.filename).ToLowerInvariant()
                    } else { [System.IO.Path]::GetFullPath((Join-Path $repoRoot $finding.filename)).ToLowerInvariant() }
                    if ([string]::Equals($filename, $target, [StringComparison]::Ordinal)) {
                        throw "A frozen diagnostic finding is under the wrong result key."
                    }
                }
                continue
            }
            $key = Get-FrozenDiagnosticFindingKey -FindingPath $property.Name -Finding $finding
            if (-not $proofKeys.Contains($key) -or -not $findingKeys.Add($key)) {
                throw "A frozen diagnostic finding is unexplained or duplicated."
            }
        }
    }
    Assert-GeneratedProofInputsUnchanged
    return [pscustomobject]@{ ProofKeys = $proofKeys; FindingKeys = $findingKeys; Present = ($null -ne $Proof) }
}

function Publish-FrozenDiagnosticRegistrationPlan {
    param([Parameter(Mandatory = $true)][object] $Plan)

    $next = [System.Collections.Generic.HashSet[string]]::new($script:FrozenDiagnosticFindingKeys, [StringComparer]::Ordinal)
    foreach ($key in $Plan.ProofKeys) {
        if ($next.Contains($key)) { throw "A frozen diagnostic key was already registered." }
    }
    foreach ($key in $Plan.FindingKeys) {
        if (-not $Plan.ProofKeys.Contains($key) -or -not $next.Add($key)) {
            throw "A frozen diagnostic registration lacks proof or is duplicated."
        }
    }
    $applied = 0; $proofOnly = 0
    foreach ($key in $Plan.ProofKeys) {
        if ($Plan.FindingKeys.Contains($key)) {
            if (-not $next.Contains($key)) { throw "A frozen diagnostic finding lacks its exact exception." }
            $applied += 1
        } else {
            if ($next.Contains($key)) { throw "A frozen diagnostic proof-only key inherited an exception." }
            $proofOnly += 1
        }
    }
    Assert-GeneratedProofInputsUnchanged
    $script:FrozenDiagnosticFindingKeys = $next
    return [pscustomobject]@{ ProofKeys = $Plan.ProofKeys.Count; Findings = $Plan.FindingKeys.Count; NewKeys = $Plan.FindingKeys.Count; AppliedFindings = $applied; ProofOnlyUnregistered = $proofOnly }
}

function Add-ValidatedFrozenDiagnosticSnapshotExceptions {
    param([object] $Proof, [object] $Scan, [string] $ScanJsonPath)

    $plan = Get-FrozenDiagnosticRegistrationPlan -Proof $Proof -Scan $Scan -ScanJsonPath $ScanJsonPath
    if (($plan.Present -and ($plan.ProofKeys.Count -ne 259 -or $plan.FindingKeys.Count -ne 257)) -or
        (-not $plan.Present -and ($plan.ProofKeys.Count -ne 0 -or $plan.FindingKeys.Count -ne 0))) {
        throw "The approved frozen diagnostic proof or actual finding population has changed."
    }
    $summary = Publish-FrozenDiagnosticRegistrationPlan -Plan $plan
    Write-Host "Frozen diagnostic CSV sets: P=$($summary.ProofKeys); D=$($summary.Findings); E=$($summary.NewKeys); applied=$($summary.AppliedFindings); proof-only unregistered=$($summary.ProofOnlyUnregistered); type=Hex High Entropy String"
}

function Invoke-FrozenDiagnosticSelfCanaries {
    param([Parameter(Mandatory = $true)][string] $Directory)

    # Private, disposable fixtures only. The normal entry point never receives a
    # caller-supplied expected digest, path override, or preclassified finding.
    $null = [System.IO.Directory]::CreateDirectory($Directory)
    $originalPath = $script:FrozenDiagnosticSnapshotPath
    $originalKeys = $script:FrozenDiagnosticFindingKeys
    $originalRecords = $script:GeneratedProofInputRecords
    $originalGenericMap = $script:AllowedArtifactSecretHashes
    $privateGenericMap = @{}
    foreach ($path in $originalGenericMap.Keys) {
        $privateGenericMap[$path] = [System.Collections.Generic.HashSet[string]]::new(
            $originalGenericMap[$path], [StringComparer]::OrdinalIgnoreCase
        )
    }
    $script:AllowedArtifactSecretHashes = $privateGenericMap
    $state = @{ Positive = 0; Negative = 0; DetectorFiles = 0; Serial = 0 }
    $utf8 = [System.Text.UTF8Encoding]::new($false, $true)
    $fixturePath = Join-Path $Directory "synthetic-snapshot.csv"
    $sourcePath = Join-Path $Directory "historical-source.txt"
    $sourceText = "Safe synthetic historical source 1, not a credential.`n"
    [System.IO.File]::WriteAllText($sourcePath, $sourceText, $utf8)
    $sourceRelative = [System.IO.Path]::GetRelativePath($repoRoot, $sourcePath).Replace("\", "/")
    $syntheticLines = [System.Collections.Generic.List[string]]::new()
    $syntheticLines.Add("path,before_sha256,after_scan_sha256,comparison")
    for ($row = 1; $row -le 259; $row += 1) {
        $value = Get-GeneratedSha256HexFromBytes -Bytes ($utf8.GetBytes(
            "Safe synthetic historical source $row, not a credential.`n"
        ))
        $relative = if ($row -eq 1) { $sourceRelative } else { "synthetic/source-$row.txt" }
        $syntheticLines.Add('"' + $relative + '","' + $value + '","' + $value + '","UNCHANGED"')
    }
    $syntheticText = ($syntheticLines -join "`n") + "`n"
    $syntheticBytes = $utf8.GetBytes($syntheticText)

    function Reset-FrozenCanaryState {
        $script:GeneratedProofInputRecords = @{}
        $script:FrozenDiagnosticFindingKeys = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        $script:FrozenDiagnosticSnapshotPath = $fixturePath
    }
    function Write-FrozenCanaryJson {
        param([object] $Scan, [AllowNull()][object] $RawText)
        $state.Serial += 1
        $path = Join-Path $Directory ("result-{0:D4}.json" -f $state.Serial)
        $text = if ($null -ne $RawText) { $RawText } else { ConvertTo-Json -InputObject $Scan -Depth 100 -Compress }
        [System.IO.File]::WriteAllText($path, $text, $utf8)
        return $path
    }
    function New-FrozenCanaryFixture {
        Reset-FrozenCanaryState
        [System.IO.File]::WriteAllBytes($fixturePath, $syntheticBytes)
        $snapshot = Get-GeneratedArtifactSnapshot -Path $fixturePath
        $rows = Get-FrozenDiagnosticCsvRows -Snapshot $snapshot
        $proof = [pscustomobject]@{ Path = $fixturePath.ToLowerInvariant(); Snapshot = $snapshot; Rows = $rows }
        $findings = @(
            foreach ($row in $rows) {
                if ($row.LineNumber -in @(214, 257)) { continue }
                [pscustomobject]@{
                    type = "Hex High Entropy String"; filename = $fixturePath
                    hashed_secret = $row.Fingerprint; is_verified = $false; line_number = [int]$row.LineNumber
                }
            }
        )
        $results = [ordered]@{}
        $results[$fixturePath] = $findings
        $scan = [pscustomobject]@{
            version = "1.5.0"; results = [pscustomobject]$results
            serial_scan = [pscustomobject]@{ completed = @([pscustomobject]@{
                full_path = $fixturePath; scan_path = $fixturePath.Replace("\", "/")
                size = [long]$snapshot.Size; sha256 = $snapshot.Sha256
            }) }
        }
        return [pscustomobject]@{ Proof = $proof; Scan = $scan; JsonPath = (Write-FrozenCanaryJson -Scan $scan -RawText $null) }
    }
    function Assert-FrozenCanaryRejected {
        param([string] $Name, [scriptblock] $Action)
        $before = $script:FrozenDiagnosticFindingKeys
        $beforeValues = [System.Collections.Generic.HashSet[string]]::new($before, [StringComparer]::Ordinal)
        $rejected = $false
        try { $null = & $Action } catch { $rejected = $true }
        if (-not $rejected -or -not [object]::ReferenceEquals($before, $script:FrozenDiagnosticFindingKeys) -or
            -not $beforeValues.SetEquals($script:FrozenDiagnosticFindingKeys) -or
            -not [object]::ReferenceEquals($privateGenericMap, $script:AllowedArtifactSecretHashes)) {
            throw "A frozen diagnostic negative did not reject atomically: $Name"
        }
        $state.Negative += 1
        Write-Host "Frozen diagnostic negative PASS: $Name; new exception delta=0; existing maps preserved"
    }
    function Confirm-FrozenCanaryPositive {
        param([string] $Name)
        $state.Positive += 1
        Write-Host "Frozen diagnostic positive PASS: $Name"
    }
    try {
        Reset-FrozenCanaryState
        # An approved exact input also proves the split literal pin reconstructs
        # its independently read immutable bytes; never change that original.
        if (Test-Path -LiteralPath $originalPath -PathType Leaf) {
            Assert-SafeMutableRepositoryFile -Path $originalPath
            $approvedBytes = [System.IO.File]::ReadAllBytes($originalPath)
            [System.IO.File]::WriteAllBytes($fixturePath, $approvedBytes)
            $approvedProof = Get-FrozenDiagnosticSnapshotProof
            if ($approvedProof.Rows.Count -ne 259 -or $approvedProof.Snapshot.Size -ne 49504) {
                throw "The frozen diagnostic immutable-pin reconstruction canary failed."
            }
            Confirm-FrozenCanaryPositive -Name "exact approved bytes and reconstructed fixed pin; P=259"
            foreach ($name in @("one-byte", "append", "bom", "crlf", "row-order", "empty")) {
                Reset-FrozenCanaryState
                $bytes = [byte[]]$approvedBytes.Clone()
                switch ($name) {
                    "one-byte" { $bytes[0] = [byte][char]'P' }
                    "append" { $bytes = [byte[]](@($bytes) + @([byte]10)) }
                    "bom" { $bytes = [byte[]](@(239, 187, 191) + @($bytes)) }
                    "crlf" { $bytes = $utf8.GetBytes($utf8.GetString($bytes).Replace("`n", "`r`n")) }
                    "row-order" {
                        $lines = $utf8.GetString($bytes).Split("`n")
                        $temporary = $lines[1]; $lines[1] = $lines[2]; $lines[2] = $temporary
                        $bytes = $utf8.GetBytes($lines -join "`n")
                    }
                    "empty" { $bytes = [byte[]]::new(0) }
                }
                [System.IO.File]::WriteAllBytes($fixturePath, $bytes)
                Assert-FrozenCanaryRejected -Name ("fixed-version-" + $name) -Action { Get-FrozenDiagnosticSnapshotProof }
            }
        } else {
            Write-Host "Frozen diagnostic optional exact-input canary: absent at entry; no fabricated approved bytes"
        }

        # Structural mutations intentionally bypass only the outer fixed-byte
        # gate, not this production parser, to exercise its deeper branches.
        foreach ($name in @(
            "unknown-header", "duplicate-header", "header-order", "unknown-column", "duplicate-row",
            "missing-row", "extra-row", "embedded-newline", "no-final-lf", "bom", "crlf", "nul",
            "invalid-utf8", "empty", "final-format-character", "unquoted-row", "unequal-digests", "uppercase-digest",
            "hash-in-path", "hash-in-comparison", "path-traversal", "path-backslash", "path-trailing-dot"
        )) {
            Reset-FrozenCanaryState
            $lines = $syntheticLines.ToArray()
            $bytes = $null
            switch ($name) {
                "unknown-header" { $lines[0] += ",unknown" }
                "duplicate-header" { $lines[0] = "path,before_sha256,before_sha256,comparison" }
                "header-order" { $lines[0] = "path,after_scan_sha256,before_sha256,comparison" }
                "unknown-column" { $lines[1] += ',"unknown"' }
                "duplicate-row" { $lines[2] = $lines[1] }
                "missing-row" { $lines = @($lines | Select-Object -SkipLast 1) }
                "extra-row" { $lines = @($lines) + @($lines[1]) }
                "embedded-newline" { $lines[1] = $lines[1].Replace('"UNCHANGED"', '"UN' + "`n" + 'CHANGED"') }
                "no-final-lf" { $bytes = $utf8.GetBytes($lines -join "`n") }
                "bom" { $bytes = [byte[]](@(239, 187, 191) + @($syntheticBytes)) }
                "crlf" { $bytes = $utf8.GetBytes($syntheticText.Replace("`n", "`r`n")) }
                "nul" { $bytes = $utf8.GetBytes($syntheticText.Replace("UNCHANGED", "UNCHANGED" + [char]0)) }
                "invalid-utf8" { $bytes = [byte[]]$syntheticBytes.Clone(); $bytes[0] = 0x80 }
                "empty" { $bytes = [byte[]]::new(0) }
                "final-format-character" { $bytes = $utf8.GetBytes($syntheticText + [char]0x200b) }
                "unquoted-row" { $lines[1] = $lines[1].Replace('"', '') }
                "unequal-digests" {
                    $parts = $lines[1].Split(','); $parts[2] = '"' + ('0' * 64) + '"'; $lines[1] = $parts -join ','
                }
                "uppercase-digest" {
                    $parts = $lines[1].Split(','); $parts[1] = $parts[1].ToUpperInvariant(); $parts[2] = $parts[1]; $lines[1] = $parts -join ','
                }
                "hash-in-path" { $parts = $lines[1].Split(','); $parts[0] = $parts[1]; $lines[1] = $parts -join ',' }
                "hash-in-comparison" { $parts = $lines[1].Split(','); $parts[3] = $parts[1]; $lines[1] = $parts -join ',' }
                "path-traversal" { $lines[1] = $lines[1].Replace($sourceRelative, "../synthetic.txt") }
                "path-backslash" { $lines[1] = $lines[1].Replace($sourceRelative, "synthetic\source.txt") }
                "path-trailing-dot" { $lines[1] = $lines[1].Replace($sourceRelative, "synthetic/source.") }
            }
            if ($null -eq $bytes) { $bytes = $utf8.GetBytes(($lines -join "`n") + "`n") }
            $badSnapshot = [pscustomobject]@{ Bytes = $bytes }
            Assert-FrozenCanaryRejected -Name ("parser-" + $name) -Action { Get-FrozenDiagnosticCsvRows -Snapshot $badSnapshot }
        }

        $fixture = New-FrozenCanaryFixture
        $plan = Get-FrozenDiagnosticRegistrationPlan -Proof $fixture.Proof -Scan $fixture.Scan -ScanJsonPath $fixture.JsonPath
        $summary = Publish-FrozenDiagnosticRegistrationPlan -Plan $plan
        if ($summary.ProofKeys -ne 259 -or $summary.Findings -ne 257 -or $summary.NewKeys -ne 257 -or
            $summary.AppliedFindings -ne 257 -or $summary.ProofOnlyUnregistered -ne 2) {
            throw "The frozen diagnostic synthetic P/D/E proof failed."
        }
        foreach ($finding in $fixture.Scan.results.PSObject.Properties[$fixturePath].Value) {
            if (-not (Test-AllowedArtifactFinding -FindingPath $fixturePath -Finding $finding)) {
                throw "A frozen diagnostic synthetic finding did not receive its exact exception."
            }
            $finding.line_number = [long]$finding.line_number
            if (-not (Test-AllowedArtifactFinding -FindingPath $fixturePath -Finding $finding)) {
                throw "A frozen diagnostic positive Int64 line was rejected."
            }
        }
        foreach ($row in $fixture.Proof.Rows | Where-Object { $_.LineNumber -in @(214, 257) }) {
            $finding = [pscustomobject]@{
                type = "Hex High Entropy String"; filename = $fixturePath
                hashed_secret = $row.Fingerprint; is_verified = $false; line_number = [int]$row.LineNumber
            }
            if (Test-AllowedArtifactFinding -FindingPath $fixturePath -Finding $finding) {
                throw "A frozen diagnostic proof-only finding inherited an exception."
            }
        }
        $fixture.Scan.serial_scan.completed[0].size = [int]$fixture.Scan.serial_scan.completed[0].size
        $longPlan = Get-FrozenDiagnosticRegistrationPlan -Proof $fixture.Proof -Scan $fixture.Scan -ScanJsonPath $fixture.JsonPath
        if ($longPlan.FindingKeys.Count -ne 257) { throw "Positive Int64 lines or Int32 completion size were rejected." }
        Confirm-FrozenCanaryPositive -Name "P=259; D=E=applied=257; proof-only unregistered=2; Int32 and Int64 lines"

        $matching = $fixture.Scan.results.PSObject.Properties[$fixturePath].Value[0]
        [System.IO.File]::WriteAllBytes((Join-Path $Directory "another.csv"), $syntheticBytes)
        [System.IO.File]::WriteAllBytes((Join-Path $Directory "another.txt"), $syntheticBytes)
        foreach ($name in @("base64", "keyword", "wrong-line", "wrong-filename", "other-csv", "other-txt", "other-three-1", "other-three-2", "other-three-3")) {
            $finding = ConvertFrom-Json (ConvertTo-Json $matching -Compress)
            $path = $fixturePath
            switch ($name) {
                "base64" { $finding.type = "Base64 High Entropy String" }
                "keyword" { $finding.type = "Secret Keyword" }
                "wrong-line" { $finding.line_number = 1 }
                "wrong-filename" { $finding.filename = Join-Path $Directory "another.csv" }
                "other-csv" { $path = Join-Path $Directory "another.csv"; $finding.filename = $path }
                "other-txt" { $path = Join-Path $Directory "another.txt"; $finding.filename = $path }
                "other-three-1" { $path = Join-Path $repoRoot "qa/PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_FINDINGS.csv"; $finding.filename = $path }
                "other-three-2" { $path = Join-Path $repoRoot "qa/PHASE_02_CP3_C2_B2_C_R1_HISTORICAL_FINDINGS.csv"; $finding.filename = $path }
                "other-three-3" { $path = Join-Path $repoRoot "qa/PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_FILE_COUNTS.csv"; $finding.filename = $path }
            }
            if (Test-AllowedArtifactFinding -FindingPath $path -Finding $finding) {
                throw "A frozen diagnostic key escaped its path/line/type boundary: $name"
            }
            $state.Negative += 1
            Write-Host "Frozen diagnostic negative PASS: matcher-$name; no inherited exception"
        }
        # Even an existing generic same-value key cannot authorize a CSV type.
        $genericHash = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        $null = $genericHash.Add([string]$matching.line_number + "|" + $matching.hashed_secret)
        $privateGenericMap[$fixturePath.ToLowerInvariant()] = $genericHash
        $wrongType = ConvertFrom-Json (ConvertTo-Json $matching -Compress)
        $wrongType.type = "Base64 High Entropy String"
        if (Test-AllowedArtifactFinding -FindingPath $fixturePath -Finding $wrongType) {
            throw "A frozen diagnostic finding inherited a generic Base64 exception."
        }
        $null = $privateGenericMap.Remove($fixturePath.ToLowerInvariant())
        Confirm-FrozenCanaryPositive -Name "CSV explicit type boundary blocks generic-map inheritance"
        $genericRejected = ConvertFrom-Json (ConvertTo-Json $matching -Compress)
        $genericRejected.type = "Secret Keyword"
        if (Test-AllowedArtifactFinding -FindingPath ([string][char]0) -Finding $genericRejected) {
            throw "An unrelated generic type bypassed its original early rejection."
        }
        Confirm-FrozenCanaryPositive -Name "unrelated generic type rejection still precedes path parsing"

        foreach ($name in @(
            "type-base64", "type-keyword", "type-array", "type-format-character", "line-bool", "line-string", "line-float", "line-null", "line-zero", "line-negative", "line-overflow",
            "wrong-line", "wrong-filename", "unexplained", "uppercase-fingerprint", "missing-field", "unknown-field", "verified-string",
            "duplicate-finding", "missing-finding", "empty-results", "malformed-list", "wrong-result-key", "duplicate-result-alias",
            "completion-missing", "completion-duplicate", "completion-size", "completion-hash", "completion-size-string", "completion-size-bool",
            "completion-schema", "completion-scan-path", "completion-full-path", "stale-object", "duplicate-json-key", "malformed-json",
            "line-with-int64", "late-invalid-finding", "proof-missing", "proof-duplicate", "proof-snapshot-missing",
            "filename-format-character", "result-format-character", "completion-full-format-character",
            "completion-scan-format-character", "completion-both-format-character", "proof-path-format-character"
        )) {
            $fixture = New-FrozenCanaryFixture
            $bad = ConvertFrom-Json (ConvertTo-Json $fixture.Scan -Depth 100 -Compress)
            $entry = $bad.results.PSObject.Properties[$fixturePath].Value[0]
            $proof = $fixture.Proof
            $raw = $null
            switch ($name) {
                "type-base64" { $entry.type = "Base64 High Entropy String" }
                "type-keyword" { $entry.type = "Secret Keyword" }
                "type-array" { $entry.type = @("Hex High Entropy String") }
                "type-format-character" { $entry.type = "Hex" + [char]0x200b + " High Entropy String" }
                "line-bool" { $entry.line_number = $true }
                "line-string" { $entry.line_number = "2" }
                "line-float" { $entry.line_number = [double]2.5 }
                "line-null" { $entry.line_number = $null }
                "line-zero" { $entry.line_number = 0 }
                "line-negative" { $entry.line_number = -1 }
                "line-overflow" { $entry.line_number = [long][int]::MaxValue + 1 }
                "wrong-line" { $entry.line_number = 1 }
                "wrong-filename" { $entry.filename = Join-Path $Directory "wrong-file.csv" }
                "unexplained" { $entry.hashed_secret = Get-Sha1Hex -Value "An unproved synthetic value, not a credential." }
                "uppercase-fingerprint" { $entry.hashed_secret = $entry.hashed_secret.ToUpperInvariant() }
                "missing-field" { $entry.PSObject.Properties.Remove("type") }
                "unknown-field" { $entry | Add-Member -NotePropertyName unexpected -NotePropertyValue $true }
                "verified-string" { $entry.is_verified = "false" }
                "duplicate-finding" { $bad.results.PSObject.Properties[$fixturePath].Value = @($bad.results.PSObject.Properties[$fixturePath].Value) + @($entry) }
                "missing-finding" { $bad.results.PSObject.Properties[$fixturePath].Value = @($bad.results.PSObject.Properties[$fixturePath].Value | Select-Object -Skip 1) }
                "empty-results" { $bad.results = [pscustomobject]@{} }
                "malformed-list" { $bad.results.PSObject.Properties[$fixturePath].Value = $entry }
                "wrong-result-key" {
                    $other = Join-Path $Directory "misfiled.csv"
                    $findings = $bad.results.PSObject.Properties[$fixturePath].Value
                    $bad.results = [pscustomobject]@{}; $bad.results | Add-Member -NotePropertyName $other -NotePropertyValue $findings
                    $bad.serial_scan.completed = @($bad.serial_scan.completed) + @([pscustomobject]@{
                        full_path = $other; scan_path = $other; size = 0; sha256 = ('0' * 64)
                    })
                }
                "duplicate-result-alias" { $bad.results | Add-Member -NotePropertyName $fixturePath.Replace("\", "/") -NotePropertyValue @($entry) }
                "completion-missing" { $bad.serial_scan.completed = @() }
                "completion-duplicate" { $bad.serial_scan.completed = @($bad.serial_scan.completed) + @($bad.serial_scan.completed[0]) }
                "completion-size" { $bad.serial_scan.completed[0].size += 1 }
                "completion-hash" { $bad.serial_scan.completed[0].sha256 = '0' * 64 }
                "completion-size-string" { $bad.serial_scan.completed[0].size = [string]$bad.serial_scan.completed[0].size }
                "completion-size-bool" { $bad.serial_scan.completed[0].size = $true }
                "completion-schema" { $bad.serial_scan.completed[0].PSObject.Properties.Remove("sha256") }
                "completion-scan-path" { $bad.serial_scan.completed[0].scan_path = Join-Path $Directory "wrong.csv" }
                "completion-full-path" { $bad.serial_scan.completed[0].full_path = Join-Path $Directory "wrong.csv" }
                "stale-object" { $raw = ConvertTo-Json $bad -Depth 100 -Compress; $entry.line_number = 1 }
                "duplicate-json-key" { $raw = '{"results":{},' + (ConvertTo-Json $bad -Depth 100 -Compress).Substring(1) }
                "malformed-json" { $raw = (ConvertTo-Json $bad -Depth 100 -Compress); $raw = $raw.Substring(0, $raw.Length - 1) }
                "line-with-int64" { $entry.line_number = [long]2; $entry.type = "Base64 High Entropy String" }
                "late-invalid-finding" { $bad.results.PSObject.Properties[$fixturePath].Value[-1].type = "Base64 High Entropy String" }
                "proof-missing" { $proof = $null }
                "proof-duplicate" { $proof.Rows[258] = $proof.Rows[0] }
                "proof-snapshot-missing" { $script:GeneratedProofInputRecords = @{} }
                "filename-format-character" { $entry.filename = $fixturePath.Replace("synthetic-snapshot", "synthetic" + [char]0x200b + "-snapshot") }
                "result-format-character" {
                    $alias = $fixturePath.Replace("synthetic-snapshot", "synthetic" + [char]0x200b + "-snapshot")
                    $bad.results = [pscustomobject]@{}; $bad.results | Add-Member -NotePropertyName $alias -NotePropertyValue @($entry)
                    $bad.serial_scan.completed = @($bad.serial_scan.completed) + @([pscustomobject]@{
                        full_path = $alias; scan_path = $alias
                        size = $proof.Snapshot.Size; sha256 = $proof.Snapshot.Sha256
                    })
                }
                "completion-full-format-character" { $bad.serial_scan.completed[0].full_path = $fixturePath + [char]0x200b }
                "completion-scan-format-character" { $bad.serial_scan.completed[0].scan_path = $fixturePath + [char]0x200b }
                "completion-both-format-character" {
                    $bad.serial_scan.completed[0].full_path = $fixturePath + [char]0x200b
                    $bad.serial_scan.completed[0].scan_path = $fixturePath + [char]0x200b
                }
                "proof-path-format-character" { $proof.Path += [char]0x200b }
            }
            $path = Write-FrozenCanaryJson -Scan $bad -RawText $raw
            Assert-FrozenCanaryRejected -Name ("plan-" + $name) -Action {
                Add-ValidatedFrozenDiagnosticSnapshotExceptions -Proof $proof -Scan $bad -ScanJsonPath $path
            }
        }

        foreach ($name in @("dot", "dotdot", "device", "ads", "trailing-dot", "trailing-space", "repeated-separator")) {
            $fixture = New-FrozenCanaryFixture
            $bad = ConvertFrom-Json (ConvertTo-Json $fixture.Scan -Depth 100 -Compress)
            $alias = switch ($name) {
                "dot" { $Directory + "\.\synthetic-snapshot.csv" }
                "dotdot" { $Directory + "\unused\..\synthetic-snapshot.csv" }
                "device" { "\\?\" + $fixturePath }
                "ads" { $fixturePath + ":stream" }
                "trailing-dot" { $fixturePath + "." }
                "trailing-space" { $fixturePath + " " }
                "repeated-separator" { $Directory + "\\synthetic-snapshot.csv" }
            }
            $bad.results.PSObject.Properties[$fixturePath].Value[0].filename = $alias
            $path = Write-FrozenCanaryJson -Scan $bad -RawText $null
            Assert-FrozenCanaryRejected -Name ("windows-alias-" + $name) -Action {
                Add-ValidatedFrozenDiagnosticSnapshotExceptions -Proof $fixture.Proof -Scan $bad -ScanJsonPath $path
            }
            if (Test-AllowedArtifactFinding -FindingPath $alias -Finding $bad.results.PSObject.Properties[$fixturePath].Value[0]) {
                throw "A frozen diagnostic matcher admitted a Windows alias: $name"
            }
        }

        foreach ($name in @("after-proof", "pre-publication", "json-pre-publication", "final-coverage")) {
            $fixture = New-FrozenCanaryFixture
            if ($name -ne "after-proof") {
                $plan = Get-FrozenDiagnosticRegistrationPlan -Proof $fixture.Proof -Scan $fixture.Scan -ScanJsonPath $fixture.JsonPath
            }
            if ($name -eq "final-coverage") {
                $null = Publish-FrozenDiagnosticRegistrationPlan -Plan $plan
                $binaryPath = Join-Path $Directory "coverage-control.bin"
                $binaryBytes = [byte[]]@(65, 0, 66, 67)
                [System.IO.File]::WriteAllBytes($binaryPath, $binaryBytes)
                $binaryRecords = [System.Collections.Generic.List[object]]::new()
                Add-ValidatedBinaryCompletionRecord -File (Get-Item -LiteralPath $binaryPath) `
                    -Bytes $binaryBytes -CompletionRecords $binaryRecords
                $coverageFiles = @((Get-Item -LiteralPath $fixturePath), (Get-Item -LiteralPath $binaryPath))
                Assert-SecretScanCompletionCoverage -ExpectedFiles $coverageFiles `
                    -TextCompletionRecords @($fixture.Scan.serial_scan.completed) -BinaryCompletionRecords @($binaryRecords)
                Confirm-FrozenCanaryPositive -Name "exact text and binary coverage succeeds before input drift"
            }
            $driftPath = if ($name -eq "json-pre-publication") { $fixture.JsonPath } else { $fixturePath }
            [System.IO.File]::AppendAllText($driftPath, "`n", $utf8)
            Assert-FrozenCanaryRejected -Name ("input-drift-" + $name) -Action {
                switch ($name) {
                    "after-proof" { Get-FrozenDiagnosticRegistrationPlan -Proof $fixture.Proof -Scan $fixture.Scan -ScanJsonPath $fixture.JsonPath }
                    "final-coverage" {
                        Assert-SecretScanCompletionCoverage -ExpectedFiles $coverageFiles `
                            -TextCompletionRecords @($fixture.Scan.serial_scan.completed) -BinaryCompletionRecords @($binaryRecords)
                    }
                    default { Publish-FrozenDiagnosticRegistrationPlan -Plan $plan }
                }
            }
        }

        $fixture = New-FrozenCanaryFixture
        $directoryPrefix = [System.IO.Path]::GetFullPath($Directory).TrimEnd('\') + '\'
        if (-not [System.IO.Path]::GetFullPath($fixturePath).StartsWith($directoryPrefix, [StringComparison]::OrdinalIgnoreCase) -or
            [System.IO.Path]::GetFullPath($fixturePath) -ceq [System.IO.Path]::GetFullPath($originalPath)) {
            throw "A disappearance canary is not this invocation's private disposable file."
        }
        Assert-SafeMutableRepositoryFile -Path $fixturePath
        # Only our newly created private fixture is removed. Original CSVs,
        # other invocations' resources, and preserved evidence are never targets.
        Remove-Item -LiteralPath $fixturePath -Force -ErrorAction Stop
        Assert-FrozenCanaryRejected -Name "private-fixture-disappearance-after-proof" -Action {
            Get-FrozenDiagnosticRegistrationPlan -Proof $fixture.Proof -Scan $fixture.Scan -ScanJsonPath $fixture.JsonPath
        }

        foreach ($name in @("late-unproved-plan-key", "preexisting-proof-only-map-key")) {
            $fixture = New-FrozenCanaryFixture
            $plan = Get-FrozenDiagnosticRegistrationPlan -Proof $fixture.Proof -Scan $fixture.Scan -ScanJsonPath $fixture.JsonPath
            if ($name -eq "late-unproved-plan-key") {
                $unproved = $fixturePath.ToLowerInvariant() + "|261|Hex High Entropy String|" +
                    (Get-Sha1Hex -Value "Late synthetic unproved plan value, not a credential.")
                $null = $plan.FindingKeys.Add($unproved)
            } else {
                $proofOnly = @($plan.ProofKeys | Where-Object { -not $plan.FindingKeys.Contains($_) })
                $null = $script:FrozenDiagnosticFindingKeys.Add($proofOnly[0])
            }
            Assert-FrozenCanaryRejected -Name ("publication-" + $name) -Action {
                Publish-FrozenDiagnosticRegistrationPlan -Plan $plan
            }
        }

        $fixture = New-FrozenCanaryFixture
        [System.IO.File]::WriteAllText($sourcePath, "A changed current source; historical bytes remain unchanged.`n", $utf8)
        Add-ValidatedFrozenDiagnosticSnapshotExceptions -Proof $fixture.Proof -Scan $fixture.Scan -ScanJsonPath $fixture.JsonPath
        if ($script:FrozenDiagnosticFindingKeys.Count -ne 257) { throw "A current source change invalidated historical proof." }
        Confirm-FrozenCanaryPositive -Name "changed current source does not rewrite or invalidate historical CSV"

        Reset-FrozenCanaryState
        $script:FrozenDiagnosticSnapshotPath = Join-Path $Directory "initially-absent.csv"
        $absentProof = Get-FrozenDiagnosticSnapshotProof
        if ($null -ne $absentProof) { throw "An initially absent frozen CSV produced proof." }
        $scan = [pscustomobject]@{ version = "1.5.0"; results = [pscustomobject]@{}; serial_scan = [pscustomobject]@{ completed = @() } }
        $path = Write-FrozenCanaryJson -Scan $scan -RawText $null
        Add-ValidatedFrozenDiagnosticSnapshotExceptions -Proof $absentProof -Scan $scan -ScanJsonPath $path
        if ($script:FrozenDiagnosticFindingKeys.Count -ne 0) { throw "An absent CSV registered exceptions." }
        Confirm-FrozenCanaryPositive -Name "clean initial absence yields zero CSV exceptions and continues"
        Assert-FrozenCanaryRejected -Name "separate-current-evidence-preservation-missing" -Action {
            if ($null -eq (Get-FrozenDiagnosticSnapshotProof)) { throw "This preservation-gated run requires its original CSV evidence." }
        }

        # The unchanged real detector must still reject a synthetic entropy value
        # in both CSV and non-CSV inputs outside the frozen exception. It is
        # random disposable test data, never a real credential or a logged value.
        $canaryBytes = [byte[]]::new(48)
        [System.Security.Cryptography.RandomNumberGenerator]::Fill($canaryBytes)
        $canaryValue = [System.Convert]::ToBase64String($canaryBytes)
        $canaryPaths = @((Join-Path $Directory "outside-secret.csv"), (Join-Path $Directory "outside-secret.txt"))
        foreach ($path in $canaryPaths) {
            [System.IO.File]::WriteAllText($path, ('opaque_value = "' + $canaryValue + '"' + "`n"), $utf8)
        }
        $scanPath = Join-Path $Directory "outside-detector.json"
        $scan = Invoke-DetectSecretsJson -Files $canaryPaths -OutputPath $scanPath
        Add-ValidatedFrozenDiagnosticSnapshotExceptions -Proof $null -Scan $scan -ScanJsonPath $scanPath
        foreach ($path in $canaryPaths) {
            $matched = @($scan.results.PSObject.Properties | Where-Object {
                (Resolve-FrozenDiagnosticScanPath -Path $_.Name) -ceq $path.ToLowerInvariant()
            })
            if ($matched.Count -ne 1 -or @($matched[0].Value).Count -eq 0) {
                throw "The unchanged detector omitted an outside-scope synthetic secret canary."
            }
            foreach ($finding in $matched[0].Value) {
                if (Test-AllowedArtifactFinding -FindingPath $matched[0].Name -Finding $finding) {
                    throw "An outside-scope synthetic detector finding inherited a frozen CSV exception."
                }
            }
            $state.DetectorFiles += 1
        }
        if ($script:FrozenDiagnosticFindingKeys.Count -ne 0) { throw "An outside secret canary registered CSV exceptions." }
        Confirm-FrozenCanaryPositive -Name "unchanged detector retained CSV and text secret canaries; no exceptions"
        foreach ($path in $originalGenericMap.Keys) {
            if (-not $privateGenericMap.ContainsKey($path) -or -not $originalGenericMap[$path].SetEquals($privateGenericMap[$path])) {
                throw "Frozen diagnostic canaries changed an existing generic exception family."
            }
        }
        Write-Host "Frozen diagnostic self-canaries passed: positive=$($state.Positive); negative=$($state.Negative); unchanged-driver secret canary files=$($state.DetectorFiles). Synthetic results are not the actual historical CSV detector population."
    }
    finally {
        $script:FrozenDiagnosticSnapshotPath = $originalPath
        $script:FrozenDiagnosticFindingKeys = $originalKeys
        $script:GeneratedProofInputRecords = $originalRecords
        $script:AllowedArtifactSecretHashes = $originalGenericMap
    }
}

function Assert-GeneratedCanaryRejected {
    param(
        [string] $Name, [scriptblock] $Action,
        [Parameter(Mandatory = $true)][string] $ArtifactPath,
        [string[]] $OtherInputPaths = @()
    )

    $script:GeneratedProofInputRecords = @{}
    $inputHashes = @{}
    foreach ($inputPath in @($ArtifactPath) + $OtherInputPaths) {
        $inputHashes[$inputPath] = Get-GeneratedSha256HexFromBytes -Bytes ([System.IO.File]::ReadAllBytes($inputPath))
    }
    $outputs = [System.Collections.Generic.List[object]]::new()
    $rejected = $false
    try { & $Action | ForEach-Object { $outputs.Add($_) } }
    catch { $rejected = $true }
    if (-not $rejected) { throw "Generated-artifact negative canary accepted: $Name" }
    if ($outputs.Count -ne 0) { throw "A rejected generated canary emitted partial proof: $Name" }
    $key = [System.IO.Path]::GetFullPath($ArtifactPath).ToLowerInvariant()
    if ($script:AllowedArtifactSecretHashes.ContainsKey($key)) {
        throw "A rejected generated artifact inherited an exception: $Name"
    }
    foreach ($inputPath in $inputHashes.Keys) {
        $afterHash = Get-GeneratedSha256HexFromBytes -Bytes ([System.IO.File]::ReadAllBytes($inputPath))
        if ($afterHash -cne $inputHashes[$inputPath]) { throw "Canary validation rewrote an input: $Name" }
    }
    Write-Host "Generated-artifact negative PASS: $Name; proof=0; exception=0; input unchanged"
}

function New-GeneratedMypyCanary {
    param([string] $Directory, [string] $Template, [string] $SourcePath = "")

    $null = [System.IO.Directory]::CreateDirectory($Directory)
    $meta = ConvertFrom-StrictGeneratedJson -Text $Template
    $sourceText = "value = 23`n"
    $dataText = '{"synthetic":0}'
    if ($SourcePath -eq "") {
        $SourcePath = Join-Path $Directory "probe.py"
        [System.IO.File]::WriteAllText($SourcePath, $sourceText)
    }
    $meta.id = "probe"
    $meta.path = $SourcePath
    $meta.hash = Get-Sha1Hex -Value $sourceText
    $meta.interface_hash = Get-Sha1Hex -Value $dataText
    $meta.size = [System.Text.Encoding]::UTF8.GetByteCount($sourceText)
    $meta.dependencies = @(); $meta.suppressed = @()
    $meta.dep_lines = @(); $meta.dep_prios = @()
    $path = Join-Path $Directory "probe.meta.json"
    $dataPath = Join-Path $Directory "probe.data.json"
    [System.IO.File]::WriteAllText($dataPath, $dataText)
    [System.IO.File]::WriteAllText($path, (ConvertTo-Json -InputObject $meta -Depth 20 -Compress))
    return [pscustomobject]@{
        Path = $path; SourcePath = $SourcePath; DataPath = $dataPath; Meta = $meta
    }
}

function Invoke-GeneratedEmptyInputSelfCanaries {
    param(
        [Parameter(Mandatory = $true)][string] $Directory,
        [Parameter(Mandatory = $true)][string] $Template
    )

    $emptyBytes = [byte[]]::new(0)
    $emptySha1 = [string]::Concat("da39a3ee", "5e6b4b0d", "3255bfef", "95601890", "afd80709")
    $emptySha256 = [string]::Concat(
        "e3b0c442", "98fc1c14", "9afbf4c8", "996fb924",
        "27ae41e4", "649b934c", "a495991b", "7852b855"
    )
    if (
        (Get-GeneratedSha256HexFromBytes -Bytes $emptyBytes) -cne $emptySha256 -or
        [Convert]::ToHexString([Security.Cryptography.SHA1]::HashData($emptyBytes)).ToLowerInvariant() -cne $emptySha1
    ) { throw "Generated empty exact-byte SHA-1/SHA-256 canary failed." }
    $nonemptyBytes = [Text.Encoding]::UTF8.GetBytes("value = 23`n")
    if (
        (Get-GeneratedSha256HexFromBytes -Bytes $nonemptyBytes) -cne
            (Get-Sha256HexFromBytes -Bytes $nonemptyBytes)
    ) { throw "Generated nonempty hashing differs from the preserved common helper." }
    Write-Host "Generated empty-input positive PASS: exact empty SHA-1/SHA-256; nonempty equivalence"

    $positives = [System.Collections.Generic.List[object]]::new()
    foreach ($extension in @("py", "pyi")) {
        foreach ($companionKind in @("empty", "nonempty")) {
            $caseDirectory = Join-Path $Directory ($extension + "-" + $companionKind)
            $null = [IO.Directory]::CreateDirectory($caseDirectory)
            $sourcePath = Join-Path $caseDirectory ("probe." + $extension)
            [IO.File]::WriteAllBytes($sourcePath, $emptyBytes)
            $case = New-GeneratedMypyCanary -Directory $caseDirectory -Template $Template -SourcePath $sourcePath
            if ($companionKind -ceq "empty") { [IO.File]::WriteAllBytes($case.DataPath, $emptyBytes) }
            $case.Meta.hash = $emptySha1
            $case.Meta.size = 0
            $case.Meta.interface_hash = [Convert]::ToHexString(
                [Security.Cryptography.SHA1]::HashData([IO.File]::ReadAllBytes($case.DataPath))
            ).ToLowerInvariant()
            [IO.File]::WriteAllText($case.Path, (ConvertTo-Json -InputObject $case.Meta -Depth 20 -Compress))
            $script:GeneratedProofInputRecords = @{}
            $proof = Get-ValidatedMypyCacheHashProof -Path $case.Path
            $source = Get-GeneratedArtifactSnapshot -Path $sourcePath
            $companion = Get-GeneratedArtifactSnapshot -Path $case.DataPath
            if (
                $source.Bytes -isnot [byte[]] -or $null -eq $source.Bytes -or
                $source.Size -ne 0 -or $source.Bytes.Length -ne 0 -or $source.Text -cne "" -or
                $source.Sha256 -cne $emptySha256 -or $emptySha1 -cnotin $proof.Values -or
                $case.Meta.interface_hash -cnotin $proof.Values -or
                ($companionKind -ceq "empty" -and (
                    $companion.Bytes -isnot [byte[]] -or $null -eq $companion.Bytes -or
                    $companion.Size -ne 0 -or $companion.Sha256 -cne $emptySha256
                ))
            ) { throw "An empty generated source/companion lost its exact bytes or proof." }
            Assert-GeneratedProofInputsUnchanged
            $positives.Add($case)
            Write-Host "Generated empty-input positive PASS: .$extension source size=0; $companionKind exact companion"
        }
    }

    # The marker is set inside the actual validation action, after the existing
    # negative harness hashes every supplied input. Empty inputs must not produce
    # a false negative PASS by failing in that pre-validation hash step.
    $assertRejected = {
        param($Name, $ArtifactPath, $OtherPaths, $ValidationAction, $ExpectedMessage = "")
        $observation = @{ Entered = $false; Message = "" }
        Assert-GeneratedCanaryRejected -Name ("empty-input-" + $Name) -ArtifactPath $ArtifactPath `
            -OtherInputPaths $OtherPaths -Action {
                $observation.Entered = $true
                try { & $ValidationAction }
                catch { $observation.Message = $_.Exception.Message; throw }
            }
        if (-not $observation.Entered) { throw "An empty-input negative did not reach its validator: $Name" }
        if ($ExpectedMessage -ne "" -and -not $observation.Message.Contains($ExpectedMessage, [StringComparison]::Ordinal)) {
            throw "An empty-input negative failed outside its required validation guard: $Name"
        }
    }
    & $assertRejected "null-bytes" $positives[0].SourcePath @() {
        Get-GeneratedSha256HexFromBytes -Bytes $null
    } "A generated hash input is null"
    $absentPath = Join-Path $Directory "never-created.py"
    & $assertRejected "missing-file" $positives[0].SourcePath @() {
        Get-GeneratedArtifactSnapshot -Path $absentPath
    }

    foreach ($name in @("size", "source-hash", "interface-hash", "missing-source", "missing-companion", "invalid-utf8", "nul-bytes")) {
        $case = New-GeneratedMypyCanary -Directory (Join-Path $Directory $name) -Template $Template
        [IO.File]::WriteAllBytes($case.SourcePath, $emptyBytes)
        [IO.File]::WriteAllBytes($case.DataPath, $emptyBytes)
        $case.Meta.hash = $emptySha1; $case.Meta.interface_hash = $emptySha1; $case.Meta.size = 0
        $expectedMessage = ""
        switch ($name) {
            "size" { $case.Meta.size = 1 }
            "source-hash" { $case.Meta.hash = Get-Sha1Hex -Value "not the empty source" }
            "interface-hash" { $case.Meta.interface_hash = Get-Sha1Hex -Value "not the empty companion" }
            "missing-source" { $case.Meta.path = Join-Path $Directory "absent\probe.py" }
            "missing-companion" { $case.Path = Join-Path ([IO.Path]::GetDirectoryName($case.Path)) "absent.meta.json" }
            "invalid-utf8" { [IO.File]::WriteAllBytes($case.SourcePath, [byte[]] @(0xc3, 0x28)) }
            "nul-bytes" { [IO.File]::WriteAllBytes($case.DataPath, [byte[]] @(0)); $expectedMessage = "contains NUL" }
        }
        if ($name -in @("size", "source-hash", "interface-hash")) {
            $expectedMessage = "A generated mypy digest does not match its exact input bytes."
        }
        [IO.File]::WriteAllText($case.Path, (ConvertTo-Json -InputObject $case.Meta -Depth 20 -Compress))
        $otherPaths = @($case.SourcePath, $case.DataPath)
        & $assertRejected $name $case.Path $otherPaths {
            Get-ValidatedMypyCacheHashProof -Path $case.Path
        } $expectedMessage
    }

    foreach ($kind in @("metadata", "build-info", "Mypy-tag", "Ruff-tag")) {
        $extension = if ($kind -ceq "metadata") { ".meta.json" } else { ".empty" }
        $path = Join-Path $Directory ($kind + $extension)
        [IO.File]::WriteAllBytes($path, $emptyBytes)
        & $assertRejected $kind $path @() {
            switch ($kind) {
                "metadata" { Get-ValidatedMypyCacheHashProof -Path $path }
                "build-info" { Get-ValidatedTypeScriptBuildInfoProof -Path $path }
                "Mypy-tag" { Get-ValidatedCacheTagProof -Path $path -Kind Mypy }
                "Ruff-tag" { Get-ValidatedCacheTagProof -Path $path -Kind Ruff }
            }
        }
    }

    foreach ($inputKind in @("source", "companion")) {
        foreach ($direction in @("empty-to-nonempty", "nonempty-to-empty")) {
            $case = New-GeneratedMypyCanary -Directory (Join-Path $Directory ($inputKind + "-" + $direction)) -Template $Template
            $path = if ($inputKind -ceq "source") { $case.SourcePath } else { $case.DataPath }
            if ($direction -ceq "empty-to-nonempty") { [IO.File]::WriteAllBytes($path, $emptyBytes) }
            $case.Meta.hash = [Convert]::ToHexString(
                [Security.Cryptography.SHA1]::HashData([IO.File]::ReadAllBytes($case.SourcePath))
            ).ToLowerInvariant()
            $case.Meta.interface_hash = [Convert]::ToHexString(
                [Security.Cryptography.SHA1]::HashData([IO.File]::ReadAllBytes($case.DataPath))
            ).ToLowerInvariant()
            $case.Meta.size = ([IO.File]::ReadAllBytes($case.SourcePath)).Length
            [IO.File]::WriteAllText($case.Path, (ConvertTo-Json -InputObject $case.Meta -Depth 20 -Compress))
            $script:GeneratedProofInputRecords = @{}
            $null = Get-ValidatedMypyCacheHashProof -Path $case.Path
            Assert-GeneratedProofInputsUnchanged
            if ($direction -ceq "empty-to-nonempty") { [IO.File]::WriteAllBytes($path, $nonemptyBytes) }
            else { [IO.File]::WriteAllBytes($path, $emptyBytes) }
            $snapshotRejected = $false; $driftRejected = $false
            try { $null = Get-GeneratedArtifactSnapshot -Path $path }
            catch { $snapshotRejected = $_.Exception.Message.Contains("changed during validation", [StringComparison]::Ordinal) }
            try { Assert-GeneratedProofInputsUnchanged }
            catch { $driftRejected = $_.Exception.Message.Contains("changed after validation", [StringComparison]::Ordinal) }
            if (-not $snapshotRejected -or -not $driftRejected) {
                throw "Generated $inputKind $direction drift did not fail both snapshot and final guards."
            }
            Write-Host "Generated empty-input negative PASS: $inputKind $direction; snapshot/final drift rejected"
        }
    }
    $script:GeneratedProofInputRecords = @{}
    Write-Host "Generated empty-input self-canaries passed; positive=5; negative=17; existing link canaries retained"
}

function Invoke-GeneratedArtifactSelfCanaries {
    param(
        [Parameter(Mandatory = $true)][string] $Directory,
        [Parameter(Mandatory = $true)][string] $ProofRoot
    )

    $script:GeneratedProofInputRecords = @{}
    $script:GeneratedMypyTagContractsReady = $false
    Initialize-GeneratedMypyTagContracts
    $templatePath = (Get-ChildItem -LiteralPath (Join-Path $ProofRoot "mypy-cache\3.13") `
        -Recurse -File -Filter "*.meta.json" | Select-Object -First 1).FullName
    $template = (Get-GeneratedArtifactSnapshot -Path $templatePath).Text
    $positive = New-GeneratedMypyCanary -Directory (Join-Path $Directory "positive") -Template $template
    $null = Get-ValidatedMypyCacheHashProof -Path $positive.Path
    Write-Host "Generated-artifact positive PASS: synthetic mypy source/interface"
    $negativeFiles = [System.Collections.Generic.List[object]]::new()
    $hexCanary = Get-Sha256HexFromBytes -Bytes ([System.Text.Encoding]::UTF8.GetBytes(
        "generated-artifact synthetic entropy canary, not a credential"
    ))
    $mypyCases = @(
        "source-byte", "interface-byte", "stored-hash-byte", "unknown-hex", "unknown-hex-before-version",
        "same-line-copy", "duplicate-key", "malformed-json", "external-source",
        "missing-source", "missing-data", "version", "nested-extra", "case-extra"
    )
    foreach ($name in $mypyCases) {
        $case = New-GeneratedMypyCanary -Directory (Join-Path $Directory $name) -Template $template
        $candidate = $case.Meta.hash
        switch ($name) {
            "source-byte" { [System.IO.File]::WriteAllText($case.SourcePath, "value = 24`n") }
            "interface-byte" { [System.IO.File]::WriteAllText($case.DataPath, '{"synthetic":1}') }
            "stored-hash-byte" {
                $first = if ($candidate[0] -ceq 'a') { 'b' } else { 'a' }
                $case.Meta.hash = $first + $candidate.Substring(1)
                $candidate = $case.Meta.hash
            }
            "unknown-hex" { $case.Meta["opaque"] = $hexCanary; $candidate = $hexCanary }
            "unknown-hex-before-version" {
                # Keep the historical adverse case unchanged; A is a separate
                # witness with the same candidate and otherwise preserved order.
                $ordered = [ordered]@{}
                foreach ($key in $case.Meta.Keys) {
                    if ($key -ceq "version_id") { $ordered["opaque"] = $hexCanary }
                    $ordered[$key] = $case.Meta[$key]
                }
                $case.Meta = $ordered
                $candidate = $hexCanary
            }
            "same-line-copy" { $case.Meta["opaque"] = $candidate }
            "external-source" { $case.Meta.path = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "..\probe.py")) }
            "missing-source" { $case.Meta.path = Join-Path $case.Path "absent\probe.py" }
            "missing-data" {
                # A new metadata name has no companion; do not delete any file.
                $case.Path = Join-Path ([System.IO.Path]::GetDirectoryName($case.Path)) "absent.meta.json"
            }
            "version" { $case.Meta.version_id = "0.0.0" }
            "nested-extra" { $case.Meta.options["opaque"] = $hexCanary; $candidate = $hexCanary }
            "case-extra" { $case.Meta["HASH"] = $candidate }
        }
        $text = ConvertTo-Json -InputObject $case.Meta -Depth 20 -Compress
        if ($name -ceq "duplicate-key") { $text = '{"hash":"' + $candidate + '",' + $text.Substring(1) }
        if ($name -ceq "malformed-json") { $text = $text.Substring(0, $text.Length - 1) }
        if ($name -in @("unknown-hex", "unknown-hex-before-version")) {
            $candidateOffset = $text.IndexOf($hexCanary, [System.StringComparison]::Ordinal)
            $versionOffset = $text.IndexOf('"version_id":', [System.StringComparison]::Ordinal)
            if ($candidateOffset -lt 0 -or $versionOffset -lt 0 -or
                ($name -ceq "unknown-hex" -and $candidateOffset -le $versionOffset) -or
                ($name -ceq "unknown-hex-before-version" -and $candidateOffset -ge $versionOffset)) {
                throw "The R1-SCAN-01 A/B canary field ordering changed."
            }
        }
        [System.IO.File]::WriteAllText($case.Path, $text)
        $otherInputs = @($case.SourcePath, $case.DataPath | Where-Object { [System.IO.File]::Exists($_) })
        Assert-GeneratedCanaryRejected -Name ("mypy-" + $name) -ArtifactPath $case.Path -OtherInputPaths $otherInputs -Action {
            Get-ValidatedMypyCacheHashProof -Path $case.Path
        }
        $negativeFiles.Add([pscustomobject]@{
            Path = $case.Path; Candidate = $candidate
            # F.3 revised: unknown mypy fields (including nested unknown fields)
            # must fail admission even when the unchanged ID heuristic omits them.
            ObserveCandidateOnly = $name -in @("unknown-hex", "unknown-hex-before-version", "nested-extra")
        })
    }

    # Real link canaries use only this scanner invocation's disposable resources.
    # Remove exactly those new link entries before the existing safe final cleanup.
    $links = [System.Collections.Generic.List[string]]::new()
    try {
        $hardDirectory = Join-Path $Directory "hard-link"
        $null = [System.IO.Directory]::CreateDirectory($hardDirectory)
        $hardPath = Join-Path $hardDirectory "probe.py"
        $null = New-Item -ItemType HardLink -Path $hardPath -Target $positive.SourcePath
        $links.Add($hardPath)
        $case = New-GeneratedMypyCanary -Directory $hardDirectory -Template $template -SourcePath $hardPath
        Assert-GeneratedCanaryRejected -Name "mypy-hard-linked-source" -ArtifactPath $case.Path -Action {
            Get-ValidatedMypyCacheHashProof -Path $case.Path
        }
        $junction = Join-Path $Directory "junction"
        $null = New-Item -ItemType Junction -Path $junction -Target ([System.IO.Path]::GetDirectoryName($positive.SourcePath))
        $links.Add($junction)
        $case = New-GeneratedMypyCanary -Directory (Join-Path $Directory "reparse") `
            -Template $template -SourcePath (Join-Path $junction "probe.py")
        Assert-GeneratedCanaryRejected -Name "mypy-reparse-source" -ArtifactPath $case.Path -Action {
            Get-ValidatedMypyCacheHashProof -Path $case.Path
        }
    }
    finally {
        foreach ($link in $links) {
            $relative = [System.IO.Path]::GetRelativePath($Directory, $link)
            if ($relative.StartsWith("..") -or [System.IO.Path]::IsPathRooted($relative)) {
                throw "A generated canary link escaped its own temporary directory."
            }
            Remove-Item -LiteralPath $link -Force
        }
    }

    foreach ($kind in @("Mypy", "Ruff")) {
        $original = [System.IO.File]::ReadAllBytes((Join-Path $ProofRoot (
            $kind.ToLowerInvariant() + "-cache\CACHEDIR.TAG"
        )))
        $positiveTag = Join-Path $Directory ($kind + "-positive.tag")
        [System.IO.File]::WriteAllBytes($positiveTag, $original)
        $script:GeneratedProofInputRecords = @{}
        $proof = Get-ValidatedCacheTagProof -Path $positiveTag -Kind $kind
        foreach ($mutation in @("byte", "extra")) {
            $path = Join-Path $Directory ($kind + "-" + $mutation + ".tag")
            $bytes = [byte[]] $original.Clone()
            if ($mutation -ceq "byte") { $bytes[0] = [byte][char]'s' }
            else { $bytes = $bytes + [System.Text.Encoding]::UTF8.GetBytes(' "' + $hexCanary + '"') }
            [System.IO.File]::WriteAllBytes($path, $bytes)
            Assert-GeneratedCanaryRejected -Name ($kind + "-tag-" + $mutation) -ArtifactPath $path -Action {
                Get-ValidatedCacheTagProof -Path $path -Kind $kind
            }
            $candidate = if ($mutation -ceq "byte") { $proof.Values[0] } else { $hexCanary }
            $negativeFiles.Add([pscustomobject]@{ Path = $path; Candidate = $candidate })
        }
    }

    $tsOriginal = [System.IO.File]::ReadAllText((Join-Path $ProofRoot "typescript\tsconfig.tsbuildinfo"))
    $tsStructure = Get-ValidatedTypeScriptBuildInfoStructure -Text $tsOriginal
    foreach ($name in @("version-byte", "unknown-hex", "same-line-copy", "duplicate-key", "case-extra", "version", "cardinality")) {
        $data = ConvertFrom-StrictGeneratedJson -Text $tsOriginal
        $candidate = $tsStructure.DistinctValues[0]
        switch ($name) {
            "version-byte" {
                $index = 0
                while (@($tsStructure.Values | Where-Object { $_ -ceq $tsStructure.Values[$index] }).Count -ne 1) { $index += 1 }
                $value = $tsStructure.Values[$index]
                $candidate = $(if ($value[0] -ceq 'a') { 'b' } else { 'a' }) + $value.Substring(1)
                if ($data.fileInfos[$index] -is [string]) { $data.fileInfos[$index] = $candidate }
                else { $data.fileInfos[$index].version = $candidate }
            }
            "unknown-hex" { $data["opaque"] = $hexCanary; $candidate = $hexCanary }
            "same-line-copy" { $data["opaque"] = $candidate }
            "case-extra" { $data["VERSION"] = $null }
            "version" { $data.version = "0.0.0" }
            "cardinality" { $data.fileNames = @($data.fileNames | Select-Object -Skip 1) }
        }
        $text = ConvertTo-Json -InputObject $data -Depth 30 -Compress
        if ($name -ceq "duplicate-key") { $text = '{"version":"5.9.3",' + $text.Substring(1) }
        $path = Join-Path $Directory ("ts-" + $name + ".tsbuildinfo")
        [System.IO.File]::WriteAllText($path, $text)
        Assert-GeneratedCanaryRejected -Name ("TypeScript-" + $name) -ArtifactPath $path -Action {
            Get-ValidatedTypeScriptBuildInfoProof -Path $path
        }
        $negativeFiles.Add([pscustomobject]@{ Path = $path; Candidate = $candidate })
    }
    $sourcePath = Join-Path $Directory "version-source.ts"
    $libraryPath = Join-Path $repoRoot "node_modules\typescript\lib\typescript.js"
    [System.IO.File]::WriteAllText($sourcePath, "export const value = 23;`n")
    $script:GeneratedProofInputRecords = @{}
    $before = Get-TypeScriptSourceVersionHashes -LibraryPath $libraryPath -SourcePaths @($sourcePath)
    [System.IO.File]::WriteAllText($sourcePath, "export const value = 24;`n")
    $after = Get-TypeScriptSourceVersionHashes -LibraryPath $libraryPath -SourcePaths @($sourcePath)
    if ($before[0] -ceq $after[0]) { throw "TypeScript ignored a synthetic source-byte mutation." }
    Write-Host "Generated-artifact negative PASS: TypeScript-source-byte"

    $securityShapes = @(
        [string]::Concat("Bearer ", "syntheticBearerToken1234567890"),
        [string]::Concat("sk-", "proj-", $hexCanary),
        [string]::Concat("-----BEGIN ", "PRIVATE KEY-----")
    )
    $shapeIndex = 0
    foreach ($shape in $securityShapes) {
        foreach ($kind in @("mypy", "typescript")) {
            $shapeIndex += 1
            $text = if ($kind -ceq "mypy") { [System.IO.File]::ReadAllText($positive.Path) } else { $tsOriginal }
            $data = ConvertFrom-StrictGeneratedJson -Text $text
            $data["opaque"] = $shape
            $text = ConvertTo-Json -InputObject $data -Depth 30 -Compress
            $extension = if ($kind -ceq "mypy") { ".meta.json" } else { ".tsbuildinfo" }
            $path = Join-Path $Directory ("security-shape-" + $shapeIndex + $extension)
            [System.IO.File]::WriteAllText($path, $text)
            Assert-GeneratedCanaryRejected -Name ("security-shape-schema-" + $shapeIndex) -ArtifactPath $path -Action {
                if ($kind -ceq "mypy") { Get-ValidatedMypyCacheHashProof -Path $path }
                else { Get-ValidatedTypeScriptBuildInfoProof -Path $path }
            }
            Assert-GeneratedCanaryRejected -Name ("security-shape-high-confidence-" + $shapeIndex) -ArtifactPath $path -Action {
                Assert-NoHighConfidenceSecretInBytes -Bytes ([System.Text.Encoding]::UTF8.GetBytes($text)) `
                    -SourceLabel "synthetic generated-artifact canary"
            }
            $candidate = if ($kind -ceq "mypy") { $positive.Meta.hash } else { $tsStructure.DistinctValues[0] }
            $negativeFiles.Add([pscustomobject]@{ Path = $path; Candidate = $candidate })
        }
    }

    $scan = Invoke-DetectSecretsJson -Files @($negativeFiles.Path) `
        -WorkingDirectory $Directory -OutputPath (Join-Path $Directory "generated-negative-scan.json")
    foreach ($case in $negativeFiles) {
        $findings = @(
            foreach ($property in $scan.results.PSObject.Properties) {
                $fullPath = if ([System.IO.Path]::IsPathRooted($property.Name)) {
                    [System.IO.Path]::GetFullPath($property.Name)
                }
                else { [System.IO.Path]::GetFullPath((Join-Path $Directory $property.Name)) }
                if ($fullPath -ieq $case.Path) { $property.Value }
            }
        )
        $candidateHash = Get-Sha1Hex -Value $case.Candidate
        $candidateRetained = @($findings | Where-Object { $_.hashed_secret -ceq $candidateHash }).Count -gt 0
        $label = [System.IO.Path]::GetRelativePath($Directory, $case.Path)
        $observeOnly = $case.PSObject.Properties["ObserveCandidateOnly"] -and $case.ObserveCandidateOnly
        if ($observeOnly) {
            # Retention AND omission are observations, never the admission PASS condition.
            Write-Host "R1-SCAN-01 detector observation: $label; candidate retained=$candidateRetained; admission rejected"
        }
        elseif (-not $candidateRetained) {
            throw "The unchanged detector did not retain generated negative candidate: $label; findings=$($findings.Count)."
        }
        # F.4 revised: the exception key has no JSON pointer. Even a hypothetical
        # finding for the entire candidate must not inherit an allowed occurrence.
        $candidateFinding = [pscustomobject]@{
            type = "Hex High Entropy String"; line_number = 1; hashed_secret = $candidateHash
        }
        if (Test-AllowedArtifactFinding -FindingPath $case.Path -Finding $candidateFinding) {
            throw "A forbidden generated candidate inherited an occurrence-aliased exception."
        }
        foreach ($finding in $findings) {
            if (Test-AllowedArtifactFinding -FindingPath $case.Path -Finding $finding) {
                throw "A rejected generated artifact inherited an exact exception."
            }
        }
    }
    $script:GeneratedProofInputRecords = @{}
    $null = Get-GeneratedArtifactSnapshot -Path $positive.SourcePath
    [System.IO.File]::WriteAllText($positive.SourcePath, "value = 25`n")
    $driftRejected = $false
    try { Assert-GeneratedProofInputsUnchanged }
    catch { $driftRejected = $true }
    if (-not $driftRejected) { throw "A generated proof accepted post-validation source drift." }
    Write-Host "Generated-artifact negative PASS: post-validation-source-drift"
    Invoke-GeneratedEmptyInputSelfCanaries -Directory (Join-Path $Directory "empty-inputs") -Template $template
    Invoke-GeneratedRegistrationSelfCanaries -Directory (Join-Path $Directory "registration") -Template $template
    Write-Host "Generated-artifact self-canaries passed; negative detector files=$($negativeFiles.Count)"
    $script:GeneratedProofInputRecords = @{}
    $script:GeneratedMypyTagContractsReady = $false
}

function Invoke-GeneratedRegistrationSelfCanaries {
    param([string] $Directory, [string] $Template)

    $null = [System.IO.Directory]::CreateDirectory($Directory)
    $originalMap = $script:AllowedArtifactSecretHashes
    $savedMap = @{}
    foreach ($oldPath in $originalMap.Keys) {
        $savedMap[$oldPath] = [System.Collections.Generic.HashSet[string]]::new(
            $originalMap[$oldPath], [System.StringComparer]::OrdinalIgnoreCase
        )
    }
    $script:AllowedArtifactSecretHashes = $savedMap
    $existingPath = Join-Path $Directory "preexisting-family.txt"
    $existingValue = "synthetic preexisting exception, not a credential"
    [System.IO.File]::WriteAllText($existingPath, $existingValue)
    Add-AllowedArtifactSecret -Path $existingPath -Value $existingValue -LineNumber 1
    $script:GeneratedProofInputRecords = @{}
    try {
        $first = New-GeneratedMypyCanary -Directory (Join-Path $Directory "first") -Template $Template
        $second = New-GeneratedMypyCanary -Directory (Join-Path $Directory "second") -Template $Template
        $proofs = @(
            [pscustomobject]@{ Kind = "Mypy"; Proof = (Get-ValidatedMypyCacheHashProof -Path $first.Path) }
            [pscustomobject]@{ Kind = "Mypy"; Proof = (Get-ValidatedMypyCacheHashProof -Path $second.Path) }
        )
        $results = [ordered]@{}
        $results[$first.Path] = @([pscustomobject]@{
            type = "Hex High Entropy String"; filename = $first.Path
            hashed_secret = (Get-Sha1Hex -Value $first.Meta.hash); is_verified = $false; line_number = 1
        })
        $results[$second.Path] = @([pscustomobject]@{
            type = "Hex High Entropy String"; filename = $second.Path
            hashed_secret = (Get-Sha1Hex -Value $second.Meta.interface_hash); is_verified = $false; line_number = 1
        })
        $completed = @($proofs | ForEach-Object {
            $record = $script:GeneratedProofInputRecords[$_.Proof.Path.ToLowerInvariant()]
            [pscustomobject]@{ scan_path = $_.Proof.Path; full_path = $_.Proof.Path; size = $record.Size; sha256 = $record.Sha256 }
        })
        $scan = [pscustomobject]@{
            version = "1.5.0"; results = [pscustomobject]$results
            serial_scan = [pscustomobject]@{ completed = $completed }
        }
        $json = ConvertTo-Json -InputObject $scan -Depth 30 -Compress
        $path = Join-Path $Directory "positive-result.json"
        [System.IO.File]::WriteAllText($path, $json)
        $plan = Get-GeneratedArtifactRegistrationPlan -Proofs $proofs -Scan $scan -ScanJsonPath $path
        $summary = Publish-GeneratedArtifactRegistrationPlan -Plan $plan
        if ($summary.ProofKeys -ne 4 -or $summary.Findings -ne 2 -or
            $summary.NewKeys -ne 2 -or $summary.AppliedFindings -ne 2 -or $summary.ProofOnlyUnregistered -ne 2) {
            throw "Generated intersection canary did not establish P>D and E=D."
        }
        foreach ($property in $scan.results.PSObject.Properties) {
            if (-not (Test-AllowedArtifactFinding -FindingPath $property.Name -Finding $property.Value[0])) {
                throw "A matching generated finding was not applied."
            }
        }
        $sameValue = [pscustomobject]@{
            type = "Hex High Entropy String"; hashed_secret = (Get-Sha1Hex -Value $first.Meta.hash); line_number = 1
        }
        if (Test-AllowedArtifactFinding -FindingPath $second.Path -Finding $sameValue) {
            throw "A proof-only value inherited another file's exception."
        }
        $sameValue.line_number = 2
        if (Test-AllowedArtifactFinding -FindingPath $first.Path -Finding $sameValue) {
            throw "A generated exception crossed its exact line."
        }
        foreach ($oldPath in $savedMap.Keys) {
            if (-not $script:AllowedArtifactSecretHashes.ContainsKey($oldPath) -or
                -not $savedMap[$oldPath].SetEquals($script:AllowedArtifactSecretHashes[$oldPath])) {
                throw "Generated registration changed an existing exception."
            }
        }
        Write-Host "Generated-registration positive PASS: P=4; D=2; E=2; applied=2; proof-only unregistered=2; existing map preserved"
        Write-Host "Generated-registration negative PASS: same-value different-file and different-line inheritance"

        # Discard only this self-canary's detached delta; preserve prior families.
        $script:AllowedArtifactSecretHashes = $savedMap
        $negativeNames = @(
            "unexplained", "type", "type-with-int-line", "line", "line-string", "path", "result-path",
            "duplicate-finding", "duplicate-result-path", "malformed-list", "missing-field",
            "completion-snapshot", "completion-schema-int-size", "completion-size-string",
            "duplicate-completion", "missing-completion", "raw-duplicate-key", "raw-malformed-json"
        )
        foreach ($name in $negativeNames) {
            $mutated = ConvertFrom-Json -InputObject $json
            $entry = $mutated.results.PSObject.Properties[$first.Path].Value[0]
            switch ($name) {
                "unexplained" { $entry.hashed_secret = Get-Sha1Hex -Value "synthetic unproved value, not a credential" }
                "type" { $entry.type = "Base64 High Entropy String" }
                "type-with-int-line" { $entry.type = "Base64 High Entropy String"; $entry.line_number = [int]1 }
                "line" { $entry.line_number = 2 }
                "line-string" { $entry.line_number = "1" }
                "path" { $entry.filename = $second.Path }
                "result-path" {
                    $unknown = Join-Path $Directory "uncompleted.meta.json"
                    $mutated.results | Add-Member -NotePropertyName $unknown -NotePropertyValue @($entry)
                }
                "duplicate-finding" { $mutated.results.PSObject.Properties[$first.Path].Value = @($entry, $entry) }
                "duplicate-result-path" {
                    $alias = $first.Path.Replace("\", "/")
                    $mutated.results | Add-Member -NotePropertyName $alias -NotePropertyValue @($entry)
                }
                "malformed-list" { $mutated.results.PSObject.Properties[$first.Path].Value = $entry }
                "missing-field" { $entry.PSObject.Properties.Remove("type") }
                "completion-snapshot" { $mutated.serial_scan.completed[0].size += 1 }
                "completion-schema-int-size" {
                    $mutated.serial_scan.completed[0].sha256 = "invalid synthetic digest"
                    $mutated.serial_scan.completed[0].size = [int]$mutated.serial_scan.completed[0].size
                }
                "completion-size-string" { $mutated.serial_scan.completed[0].size = [string]$mutated.serial_scan.completed[0].size }
                "duplicate-completion" { $mutated.serial_scan.completed = @($mutated.serial_scan.completed) + @($mutated.serial_scan.completed[0]) }
                "missing-completion" { $mutated.serial_scan.completed = @($mutated.serial_scan.completed | Select-Object -Skip 1) }
            }
            $text = ConvertTo-Json -InputObject $mutated -Depth 30 -Compress
            if ($name -ceq "raw-duplicate-key") { $text = '{"results":{},' + $text.Substring(1) }
            if ($name -ceq "raw-malformed-json") { $text = $text.Substring(0, $text.Length - 1) }
            $badPath = Join-Path $Directory ($name + ".json")
            [System.IO.File]::WriteAllText($badPath, $text)
            $rejected = $false
            try {
                $badPlan = Get-GeneratedArtifactRegistrationPlan -Proofs $proofs -Scan $mutated -ScanJsonPath $badPath
                $null = Publish-GeneratedArtifactRegistrationPlan -Plan $badPlan
            }
            catch { $rejected = $true }
            if (-not $rejected -or -not [object]::ReferenceEquals($savedMap, $script:AllowedArtifactSecretHashes)) {
                throw "A generated result negative admitted a partial delta: $name"
            }
            Write-Host "Generated-registration negative PASS: $name; new generated delta=0"
        }

        $bad = New-GeneratedMypyCanary -Directory (Join-Path $Directory "last-forbidden-copy") -Template $Template
        $bad.Meta["opaque"] = $bad.Meta.hash
        [System.IO.File]::WriteAllText($bad.Path, (ConvertTo-Json -InputObject $bad.Meta -Depth 30 -Compress))
        $rejected = $false
        try {
            $allProofs = [System.Collections.Generic.List[object]]::new()
            foreach ($record in $proofs) { $allProofs.Add($record) }
            $allProofs.Add([pscustomobject]@{ Kind = "Mypy"; Proof = (Get-ValidatedMypyCacheHashProof -Path $bad.Path) })
            $badPlan = Get-GeneratedArtifactRegistrationPlan -Proofs $allProofs.ToArray() -Scan $scan -ScanJsonPath $path
            $null = Publish-GeneratedArtifactRegistrationPlan -Plan $badPlan
        }
        catch { $rejected = $true }
        if (-not $rejected -or -not [object]::ReferenceEquals($savedMap, $script:AllowedArtifactSecretHashes)) {
            throw "Final artifact rejection leaked a partial generated delta."
        }
        Write-Host "Generated-registration negative PASS: last-artifact forbidden-copy rejection; new generated delta=0"

        $plan = Get-GeneratedArtifactRegistrationPlan -Proofs $proofs -Scan $scan -ScanJsonPath $path
        [System.IO.File]::WriteAllText($second.SourcePath, "value = 24" + [char]10)
        $rejected = $false
        try { $null = Publish-GeneratedArtifactRegistrationPlan -Plan $plan }
        catch { $rejected = $true }
        if (-not $rejected -or -not [object]::ReferenceEquals($savedMap, $script:AllowedArtifactSecretHashes)) {
            throw "Pre-publication drift leaked a partial generated delta."
        }
        Write-Host "Generated-registration negative PASS: pre-publication input drift; new generated delta=0"
    }
    finally {
        $script:AllowedArtifactSecretHashes = $originalMap
        $script:GeneratedProofInputRecords = @{}
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

function Assert-PublicChecksumFileIdentity {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][byte[]] $Bytes
    )
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $relative = [System.IO.Path]::GetRelativePath($repoRoot, $fullPath).Replace("\", "/")
    if ($relative -cne "scripts/linux_setup.py" -or
        -not [string]::Equals($fullPath, $script:PublicChecksumPath,
            [StringComparison]::OrdinalIgnoreCase)) {
        throw "A public checksum source path is not the exact approved file."
    }
    $expectedSha256 = [string]::Concat(
        "6a8ef645", "c0e5fbaf", "df08297a", "6412fd30",
        "faf6a3a4", "bfdc1970", "ca0c62d9", "4abadc04"
    )
    if ((Get-GeneratedSha256HexFromBytes -Bytes $Bytes) -cne $expectedSha256) {
        throw "The approved public checksum source bytes have changed."
    }
}

function Get-ValidatedPublicChecksumAssignments {
    param([Parameter(Mandatory = $true)][string] $Text)

    $lines = $Text -split "`n"
    $patterns = [ordered]@{
        NODE = '^NODE = "([^"]+)"$'
        NODE_ARCHIVE = '^NODE_ARCHIVE = f"node-v\{NODE\}-linux-x64\.tar\.xz"$'
        NODE_SHA256 = '^NODE_SHA256 = "([0-9a-f]{64})"$'
        UV = '^UV = "([^"]+)"(?:\s+#.*)?$'
        UV_ARCHIVE = '^UV_ARCHIVE = "([^"]+)"$'
        UV_SHA256 = '^UV_SHA256 = "([0-9a-f]{64})"$'
    }
    $assignments = @{}
    foreach ($name in $patterns.Keys) {
        $assignmentLines = @(
            for ($index = 0; $index -lt $lines.Count; $index += 1) {
                $line = $lines[$index].TrimEnd([char] 13)
                if ($line -cmatch ('^' + [regex]::Escape($name) + '\s*=')) {
                    $index
                }
            }
        )
        if ($assignmentLines.Count -ne 1) {
            throw "A public checksum assignment is absent or ambiguous: $name"
        }
        $lineNumber = [int] $assignmentLines[0] + 1
        $line = $lines[$lineNumber - 1].TrimEnd([char] 13)
        $match = [regex]::Match($line, $patterns[$name])
        if (-not $match.Success) {
            throw "A public checksum assignment differs from its approved syntax: $name"
        }
        $assignments[$name] = [pscustomobject]@{
            LineNumber = $lineNumber
            Value = if ($match.Groups.Count -gt 1) { $match.Groups[1].Value } else { $null }
        }
    }
    $approvedNodeSha256 = [string]::Concat(
        "14b342e7", "1204f811", "bde6153b", "e8e04b62",
        "aef63c23", "6fef92b5", "5f9c8315", "4b409647"
    )
    $approvedUvSha256 = [string]::Concat(
        "745765a3", "b6e360ad", "76743599", "ae5c42e9",
        "278c7edf", "8bbff9fc", "76d05bf2", "623a04dd"
    )
    if ($assignments.NODE.Value -cne "24.19.0" -or
        ("node-v$($assignments.NODE.Value)-linux-x64.tar.xz") -cne
            "node-v24.19.0-linux-x64.tar.xz" -or
        $assignments.UV.Value -cne "0.12.13" -or
        $assignments.UV_ARCHIVE.Value -cne "uv-x86_64-unknown-linux-gnu.tar.gz" -or
        $assignments.NODE_SHA256.Value -cne $approvedNodeSha256 -or
        $assignments.UV_SHA256.Value -cne $approvedUvSha256 -or
        $assignments.NODE_SHA256.LineNumber -ne 21 -or
        $assignments.UV_SHA256.LineNumber -ne 23) {
        throw "A public checksum version, archive, value, or occurrence differs."
    }
    $hexOccurrences = 0
    for ($index = 0; $index -lt $lines.Count; $index += 1) {
        foreach ($value in [regex]::Matches($lines[$index],
            '(?<![0-9A-Fa-f])[0-9A-Fa-f]{64}(?![0-9A-Fa-f])')) {
            $lineNumber = $index + 1
            if (-not (
                ($lineNumber -eq $assignments.NODE_SHA256.LineNumber -and
                    $value.Value -ceq $approvedNodeSha256) -or
                ($lineNumber -eq $assignments.UV_SHA256.LineNumber -and
                    $value.Value -ceq $approvedUvSha256)
            )) {
                throw "An unapproved 64-hex occurrence exists in public checksum source."
            }
            $hexOccurrences += 1
        }
    }
    if ($hexOccurrences -ne 2) {
        throw "The public checksum occurrence population differs."
    }
    return [pscustomobject]@{
        Node = $assignments.NODE_SHA256
        Uv = $assignments.UV_SHA256
    }
}

function Add-ValidatedPublicChecksumExceptions {
    $snapshot = Get-GeneratedArtifactSnapshot -Path $script:PublicChecksumPath
    Assert-PublicChecksumFileIdentity -Path $snapshot.Path -Bytes $snapshot.Bytes
    $assignments = Get-ValidatedPublicChecksumAssignments -Text $snapshot.Text
    $script:AllowedPublicChecksumFindingKeys.Clear()
    foreach ($item in @($assignments.Node, $assignments.Uv)) {
        $key = [string]::Concat(
            $snapshot.Path.ToLowerInvariant(), "|", [string] $item.LineNumber,
            "|Hex High Entropy String|", (Get-Sha1Hex -Value $item.Value)
        )
        if (-not $script:AllowedPublicChecksumFindingKeys.Add($key)) {
            throw "A public checksum finding key is duplicated."
        }
    }
    if ($script:AllowedPublicChecksumFindingKeys.Count -ne 2) {
        throw "The approved public checksum exception population differs."
    }
    Write-Host "Public checksum exceptions validated: NODE line=$($assignments.Node.LineNumber); UV line=$($assignments.Uv.LineNumber); count=2."
    return $assignments
}

function Test-AllowedPublicChecksumFinding {
    param(
        [Parameter(Mandatory = $true)][string] $FindingPath,
        [Parameter(Mandatory = $true)][pscustomobject] $Finding
    )
    if ($Finding.type -cne "Hex High Entropy String" -or
        $Finding.hashed_secret -isnot [string] -or
        $Finding.hashed_secret -cnotmatch '^[0-9a-f]{40}$' -or
        ($Finding.line_number -isnot [int] -and $Finding.line_number -isnot [long])) {
        return $false
    }
    $fullPath = if ([System.IO.Path]::IsPathRooted($FindingPath)) {
        [System.IO.Path]::GetFullPath($FindingPath)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot $FindingPath))
    }
    $relative = [System.IO.Path]::GetRelativePath($repoRoot, $fullPath).Replace("\", "/")
    if ($relative -cne "scripts/linux_setup.py" -or
        -not [string]::Equals($fullPath, $script:PublicChecksumPath,
            [StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }
    $key = [string]::Concat(
        $fullPath.ToLowerInvariant(), "|", [string] $Finding.line_number,
        "|Hex High Entropy String|", $Finding.hashed_secret
    )
    return $script:AllowedPublicChecksumFindingKeys.Contains($key)
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
    if ([string]::Equals($key, $script:PublicChecksumPath.ToLowerInvariant(), [StringComparison]::Ordinal)) {
        return Test-AllowedPublicChecksumFinding -FindingPath $FindingPath -Finding $Finding
    }
    # Preserve the existing generic rejection order and semantics. CSV keys
    # never enter its Hex/Base64 map and cannot fall through to that family.
    if ([string]::Equals($key, $script:FrozenDiagnosticSnapshotPath.ToLowerInvariant(), [StringComparison]::Ordinal)) {
        try {
            $csvKey = Get-FrozenDiagnosticFindingKey -FindingPath $FindingPath -Finding $Finding
            return $script:FrozenDiagnosticFindingKeys.Contains($csvKey)
        } catch { return $false }
    }
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

function Invoke-PublicChecksumSelfCanaries {
    param(
        [Parameter(Mandatory = $true)][string] $Text,
        [Parameter(Mandatory = $true)][pscustomobject] $Assignments
    )
    $node = $Assignments.Node.Value
    $uv = $Assignments.Uv.Value
    $nodeFinding = [pscustomobject]@{
        type = "Hex High Entropy String"
        hashed_secret = Get-Sha1Hex -Value $node
        line_number = $Assignments.Node.LineNumber
    }
    $uvFinding = [pscustomobject]@{
        type = "Hex High Entropy String"
        hashed_secret = Get-Sha1Hex -Value $uv
        line_number = $Assignments.Uv.LineNumber
    }
    foreach ($finding in @($nodeFinding, $uvFinding)) {
        if (-not (Test-AllowedArtifactFinding -FindingPath "scripts/linux_setup.py" -Finding $finding)) {
            throw "An approved public checksum finding failed its positive canary."
        }
    }
    $mutations = [ordered]@{
        "node-value" = $Text.Replace($node, ("0" + $node.Substring(1)))
        "uv-value" = $Text.Replace($uv, ("0" + $uv.Substring(1)))
        "node-other-line" = $Text + "`n# $node`n"
        "uv-other-line" = $Text + "`n# $uv`n"
        "renamed-variable" = $Text.Replace("NODE_SHA256 =", "RENAMED_SHA256 =")
        "third-hex" = $Text + ("`nEXTRA_SHA256 = `"" + ("a" * 64) + "`"`n")
        "duplicate-node" = $Text + "`nNODE_SHA256 = `"$node`"`n"
        "duplicate-uv" = $Text + "`nUV_SHA256 = `"$uv`"`n"
        "node-archive" = $Text.Replace('node-v{NODE}-linux-x64.tar.xz', 'node-v{NODE}-linux-arm64.tar.xz')
        "uv-archive" = $Text.Replace('uv-x86_64-unknown-linux-gnu.tar.gz', 'uv-aarch64-unknown-linux-gnu.tar.gz')
        "node-version" = $Text.Replace('NODE = "24.19.0"', 'NODE = "24.19.1"')
        "uv-version" = $Text.Replace('UV = "0.12.13"', 'UV = "0.12.14"')
    }
    foreach ($case in $mutations.GetEnumerator()) {
        if ([string]::Equals($case.Value, $Text, [StringComparison]::Ordinal)) {
            throw "A public checksum canary did not change its input: $($case.Key)"
        }
        $rejected = $false
        try { $null = Get-ValidatedPublicChecksumAssignments -Text $case.Value }
        catch { $rejected = $true }
        if (-not $rejected) { throw "A public checksum mutation was accepted: $($case.Key)" }
    }
    $snapshot = Get-GeneratedArtifactSnapshot -Path $script:PublicChecksumPath
    $mutatedBytes = [byte[]] $snapshot.Bytes.Clone()
    $mutatedBytes[0] = $mutatedBytes[0] -bxor 1
    $rejected = $false
    try { Assert-PublicChecksumFileIdentity -Path $snapshot.Path -Bytes $mutatedBytes }
    catch { $rejected = $true }
    if (-not $rejected) { throw "A public checksum source SHA mutation was accepted." }
    foreach ($path in @("scripts/linux_setup_copy.py", "scripts/another_file.py")) {
        foreach ($finding in @($nodeFinding, $uvFinding)) {
            if (Test-AllowedArtifactFinding -FindingPath $path -Finding $finding) {
                throw "A public checksum finding was accepted at another file: $path"
            }
        }
    }
    foreach ($finding in @($nodeFinding, $uvFinding)) {
        $otherLine = [pscustomobject]@{
            type = $finding.type
            hashed_secret = $finding.hashed_secret
            line_number = $finding.line_number + 1
        }
        if (Test-AllowedArtifactFinding -FindingPath "scripts/linux_setup.py" -Finding $otherLine) {
            throw "A public checksum finding was accepted at another line."
        }
        foreach ($detector in @("Base64 High Entropy String", "Private Key", "AWS Access Key")) {
            $otherDetector = [pscustomobject]@{
                type = $detector
                hashed_secret = $finding.hashed_secret
                line_number = $finding.line_number
            }
            if (Test-AllowedArtifactFinding -FindingPath "scripts/linux_setup.py" -Finding $otherDetector) {
                throw "A public checksum finding was accepted under another detector."
            }
        }
    }
    Write-Host "Public checksum negative canaries passed: 12 source mutations, file SHA, other paths/lines, and detector families."
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

if ($GeneratedArtifactSelfTest -and $FrozenDiagnosticSelfTest) {
    throw "Select exactly one diagnostic self-test entry point."
}

if ($FrozenDiagnosticSelfTest) {
    $focusedDirectory = New-TaskTempDirectory
    try {
        Invoke-FrozenDiagnosticSelfCanaries -Directory (Join-Path $focusedDirectory "csv-canaries")
        $script:GeneratedProofInputRecords = @{}
        $proof = Get-FrozenDiagnosticSnapshotProof
        if ($null -eq $proof) { throw "This preservation-gated CSV focused run requires the frozen evidence." }
        $paths = @(
            "qa/PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_FINDINGS.csv",
            "qa/PHASE_02_CP3_C2_B2_C_R1_HISTORICAL_FINDINGS.csv",
            "qa/PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_FILE_COUNTS.csv",
            "qa/PHASE_02_CP3_C2_B2_C_R1_DIAGNOSTIC_SNAPSHOT.csv"
        )
        foreach ($path in $paths) { $null = Get-GeneratedArtifactSnapshot -Path (Join-Path $repoRoot $path) }
        $scanPath = Join-Path $focusedDirectory "csv-positive-scan.json"
        $scan = Invoke-DetectSecretsJson -Files $paths -OutputPath $scanPath
        Add-ValidatedFrozenDiagnosticSnapshotExceptions -Proof $proof -Scan $scan -ScanJsonPath $scanPath
        $applied = 0
        foreach ($property in $scan.results.PSObject.Properties) {
            foreach ($finding in $property.Value) {
                if (-not (Test-AllowedArtifactFinding -FindingPath $property.Name -Finding $finding)) {
                    Write-Host "CSV focused unexplained finding: path=$($property.Name); line=$($finding.line_number); type=$($finding.type)"
                    throw "The CSV focused scan retains an unexplained finding."
                }
                Write-Host "CSV applied finding: path=$($property.Name); line=$($finding.line_number); type=$($finding.type); classification=PROVEN_NOT_SECRET; basis=exact-frozen-source-digest-proof"
                $applied += 1
            }
        }
        if ($applied -ne 257) { throw "CSV focused actual application count changed." }
        Assert-GeneratedProofInputsUnchanged
        Write-Host "CSV focused completion: files=4; snapshot findings=257; other three CSV findings=0; other three CSV new exceptions=0."
        Write-Host "Frozen diagnostic focused verification passed. This is NOT a repository secret-scan PASS."
    } finally { Remove-TaskTempDirectory -Path $focusedDirectory }
    return
}

if ($GeneratedArtifactSelfTest) {
    $focusedDirectory = New-TaskTempDirectory
    $proofRoot = Join-Path ([System.IO.Path]::GetDirectoryName($repoRoot)) (
        "generated-proof-" + [System.Guid]::NewGuid().ToString("N")
    )
    try {
        New-GeneratedArtifactProofCorpus -ProofRoot $proofRoot
        Restore-TypeScriptCanonicalState
        Invoke-GeneratedArtifactSelfCanaries -Directory (Join-Path $focusedDirectory "generated-canaries") -ProofRoot $proofRoot
        $generatedProofs = @(Get-GeneratedArtifactExceptionProofs -ProofRoot $proofRoot)
        $generatedPaths = @($generatedProofs | ForEach-Object { $_.Proof.Path })
        $null = Get-ValidatedUtf8TextFiles -Files $generatedPaths
        $focusedScan = Invoke-DetectSecretsJson -Files $generatedPaths `
            -OutputPath (Join-Path $focusedDirectory "generated-positive-scan.json")
        Add-ValidatedGeneratedArtifactExceptions -Proofs $generatedProofs -Scan $focusedScan `
            -ScanJsonPath (Join-Path $focusedDirectory "generated-positive-scan.json")
        foreach ($property in $focusedScan.results.PSObject.Properties) {
            foreach ($finding in $property.Value) {
                if (-not (Test-AllowedArtifactFinding -FindingPath $property.Name -Finding $finding)) {
                    throw "The generated-artifact focused scan retains an unexplained finding."
                }
            }
        }
        Assert-GeneratedProofInputsUnchanged
        Write-Host "Generated-artifact focused verification passed. This is NOT a repository secret-scan PASS."
    }
    finally {
        try {
            Restore-TypeScriptCanonicalState
        }
        finally {
            try {
                if ($null -ne $script:GeneratedProofRoot) {
                    Remove-GeneratedProofRoot -Path $proofRoot
                }
            }
            finally { Remove-TaskTempDirectory -Path $focusedDirectory }
        }
    }
    return
}

$tempDirectory = New-TaskTempDirectory
$proofRoot = Join-Path ([System.IO.Path]::GetDirectoryName($repoRoot)) (
    "generated-proof-" + [System.Guid]::NewGuid().ToString("N")
)
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
    Add-FrozenMigrationBlobExceptions
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
    $publicChecksumAssignments = Add-ValidatedPublicChecksumExceptions
    $publicChecksumSnapshot = Get-GeneratedArtifactSnapshot -Path $script:PublicChecksumPath
    Invoke-PublicChecksumSelfCanaries -Text $publicChecksumSnapshot.Text `
        -Assignments $publicChecksumAssignments

    Invoke-FrozenDiagnosticSelfCanaries -Directory (Join-Path $tempDirectory "csv-canaries")
    New-GeneratedArtifactProofCorpus -ProofRoot $proofRoot
    $repositoryFiles = @(
        Get-SecretScanRepositoryFiles -Root $repoRoot -ExcludedExactDirectories @($tempDirectory)
    )
    Invoke-GeneratedArtifactSelfCanaries -Directory (Join-Path $tempDirectory "generated-canaries") -ProofRoot $proofRoot
    $generatedProofs = @(Get-GeneratedArtifactExceptionProofs -ProofRoot $proofRoot)
    $generatedPaths = @($generatedProofs | ForEach-Object { $_.Proof.Path })
    $null = @(Get-ValidatedUtf8TextFiles -Files $generatedPaths -WorkingDirectory $repoRoot)
    $generatedScanPath = Join-Path $tempDirectory "generated-proof-scan.json"
    $generatedScan = Invoke-DetectSecretsJson -Files $generatedPaths -OutputPath $generatedScanPath
    Add-ValidatedGeneratedArtifactExceptions -Proofs $generatedProofs -Scan $generatedScan `
        -ScanJsonPath $generatedScanPath
    $frozenDiagnosticProof = Get-FrozenDiagnosticSnapshotProof

    $providerSecretCanaries = @(
        [string]::Concat(
            "TOSS_CLIENT_",
            "SECRET=synthetic-credential-value-123"
        ),
        [string]::Concat(
            "client_",
            "secret=synthetic-provider-secret-456"
        ),
        [string]::Concat(
            "Authorization: Bearer ",
            "syntheticBearerToken1234567890"
        )
    )
    foreach ($canary in $providerSecretCanaries) {
        $canaryRejected = $false
        try {
            Assert-NoHighConfidenceSecretInBytes `
                -Bytes ([System.Text.Encoding]::UTF8.GetBytes($canary)) `
                -SourceLabel "synthetic provider credential canary"
        }
        catch {
            $canaryRejected = $true
        }
        if (-not $canaryRejected) {
            throw "The secret scan accepted a synthetic provider credential canary."
        }
    }

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

    $typeScriptProofs = @($generatedProofs | Where-Object { $_.Kind -ceq "TypeScript" })
    if ($typeScriptProofs.Count -ne 1) {
        throw "The generated proof corpus lacks exactly one TypeScript artifact."
    }
    $repositoryTypeScriptProof = Get-FreshCanonicalTypeScriptRegistrationProof `
        -GeneratedProof $typeScriptProofs[0]
    $repositoryGeneratedPlan = Get-GeneratedArtifactRegistrationPlan `
        -Proofs @($repositoryTypeScriptProof) `
        -Scan $scan -ScanJsonPath (Join-Path $tempDirectory "scan.json")
    if ($repositoryGeneratedPlan.FindingCounts.Mypy -ne 0 -or
        $repositoryGeneratedPlan.FindingCounts.Tag -ne 0 -or
        $repositoryGeneratedPlan.FindingCounts.TypeScript -ne 696 -or
        $repositoryGeneratedPlan.ProofCounts.TypeScript -ne 696 -or
        $repositoryGeneratedPlan.ArtifactCounts.TypeScript -ne 1) {
        throw "The repository generated-artifact finding population has changed."
    }
    $null = Publish-GeneratedArtifactRegistrationPlan -Plan $repositoryGeneratedPlan
    Write-Host "Repository generated-artifact findings: TypeScript=696; temporary mypy/Ruff proof corpus excluded."
    Add-ValidatedFrozenDiagnosticSnapshotExceptions -Proof $frozenDiagnosticProof -Scan $scan `
        -ScanJsonPath (Join-Path $tempDirectory "scan.json")
    $findings = @()
    $allowedFindingCount = 0
    $acceptedPublicChecksums = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($property in $scan.results.PSObject.Properties) {
        foreach ($finding in $property.Value) {
            if (Test-AllowedArtifactFinding -FindingPath $property.Name -Finding $finding) {
                if (Test-AllowedPublicChecksumFinding -FindingPath $property.Name -Finding $finding) {
                    $publicKey = [string]::Concat([string] $finding.line_number, "|", $finding.hashed_secret)
                    if (-not $acceptedPublicChecksums.Add($publicKey)) {
                        throw "A public checksum detector finding duplicated."
                    }
                }
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
    if ($acceptedPublicChecksums.Count -ne 2) {
        throw "The public checksum detector finding population differs: $($acceptedPublicChecksums.Count)"
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

    foreach ($ignoreProbe in @(
        ".env",
        ".env.local",
        ".env.development.local",
        "apps/web/.env.local",
        "services/api/.env"
    )) {
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

    Assert-GeneratedProofInputsUnchanged
    Write-Host "Secret scan passed."
}
finally {
    try {
        Restore-TypeScriptCanonicalState
    }
    finally {
        try {
            if ($null -ne $script:GeneratedProofRoot) {
                Remove-GeneratedProofRoot -Path $proofRoot
            }
        }
        finally { Remove-TaskTempDirectory -Path $tempDirectory }
    }
}
