[CmdletBinding(PositionalBinding = $false)]
param(
    [switch] $Live,
    [switch] $ConfirmReadOnly,
    [switch] $SelfTest,
    [ValidateLength(0, 32)]
    [string] $Symbol
)

. (Join-Path $PSScriptRoot "common.ps1")

$exactAcknowledgment = "READ_ONLY_ONE_SHOT"
$acknowledgmentEnvironmentName = "TOSS_LIVE_PREFLIGHT_ACK"
$symbolEnvironmentName = "TOSS_PREFLIGHT_SYMBOL"
$safeRunnerKeys = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::Ordinal
)
foreach ($key in @(
    "MODE",
    "PROVIDER_CONTRACT_DRIFT",
    "PROVIDER_OPENAPI",
    "PROVIDER_VERSION",
    "CONTRACT_SHA_MATCH",
    "CONTRACT_ORIGIN_MATCH",
    "CREDENTIALS_CONFIGURED",
    "TOSS_CLIENT_ID_CONFIGURED",
    "TOSS_CLIENT_SECRET_CONFIGURED",
    "OAUTH_REQUEST",
    "MARKET_REQUEST",
    "MARKET_ENDPOINT",
    "RATE_HEADERS",
    "RATE_LIMIT_HEADER",
    "RATE_REMAINING_HEADER",
    "RATE_RESET_HEADER",
    "RETRY_AFTER",
    "STAGE",
    "HTTP_STATUS_CATEGORY",
    "PROVIDER_CODE",
    "ERROR_CATEGORY",
    "EXTERNAL_NETWORK_REQUESTS",
    "CREDENTIALS_USED",
    "GATE_VALIDATION",
    "OUTPUT_SCHEMA",
    "REDACTION",
    "ONE_SHOT",
    "DRIFT_STOP",
    "STATUS"
)) {
    $null = $safeRunnerKeys.Add($key)
}

function Write-FixedSummary {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.Specialized.OrderedDictionary] $Summary
    )

    foreach ($entry in $Summary.GetEnumerator()) {
        [Console]::Out.WriteLine(("{0}={1}" -f $entry.Key, $entry.Value))
    }
}

function Test-IsSafeRunnerLine {
    param([Parameter(Mandatory = $true)][string] $Line)

    if ($Line -cnotmatch '^([A-Z][A-Z0-9_]*)=([A-Za-z0-9_./:-]+)$') {
        return $false
    }
    return $safeRunnerKeys.Contains($Matches[1])
}

function Get-GateError {
    param(
        [Parameter(Mandatory = $true)][bool] $LiveRequested,
        [Parameter(Mandatory = $true)][bool] $ReadOnlyConfirmed,
        [Parameter(Mandatory = $true)][bool] $SelfTestRequested,
        [AllowNull()][string] $Acknowledgment,
        [AllowEmptyString()][string] $CandidateSymbol
    )

    if ($LiveRequested -and $SelfTestRequested) {
        return "MODE_CONFLICT"
    }
    if ($SelfTestRequested) {
        if ($ReadOnlyConfirmed) {
            return "MODE_CONFLICT"
        }
        return $null
    }
    if (-not $LiveRequested) {
        if ($ReadOnlyConfirmed) {
            return "MODE_CONFLICT"
        }
        return "LIVE_NOT_REQUESTED"
    }
    if (-not $ReadOnlyConfirmed) {
        return "READ_ONLY_CONFIRMATION_REQUIRED"
    }
    if ($Acknowledgment -cne $exactAcknowledgment) {
        return "EXACT_ACK_REQUIRED"
    }
    if (
        [string]::IsNullOrEmpty($CandidateSymbol) -or
        $CandidateSymbol.Length -gt 32 -or
        $CandidateSymbol -cnotmatch '^[A-Za-z0-9.\-]+$'
    ) {
        return "INVALID_SYMBOL"
    }
    return $null
}

function Test-OuterGateContract {
    $cases = @(
        [pscustomobject]@{
            Live = $false; Confirm = $false; SelfTest = $false
            Ack = $null; Symbol = ""; Expected = "LIVE_NOT_REQUESTED"
        },
        [pscustomobject]@{
            Live = $true; Confirm = $false; SelfTest = $false
            Ack = $exactAcknowledgment; Symbol = "SYNTHETIC"; Expected = "READ_ONLY_CONFIRMATION_REQUIRED"
        },
        [pscustomobject]@{
            Live = $true; Confirm = $true; SelfTest = $false
            Ack = $null; Symbol = "SYNTHETIC"; Expected = "EXACT_ACK_REQUIRED"
        },
        [pscustomobject]@{
            Live = $true; Confirm = $true; SelfTest = $false
            Ack = "WRONG_ACK"; Symbol = "SYNTHETIC"; Expected = "EXACT_ACK_REQUIRED"
        },
        [pscustomobject]@{
            Live = $true; Confirm = $true; SelfTest = $false
            Ack = $exactAcknowledgment; Symbol = "../unsafe"; Expected = "INVALID_SYMBOL"
        },
        [pscustomobject]@{
            Live = $true; Confirm = $true; SelfTest = $false
            Ack = $exactAcknowledgment; Symbol = "SYNTHETIC-1"; Expected = $null
        },
        [pscustomobject]@{
            Live = $true; Confirm = $true; SelfTest = $true
            Ack = $exactAcknowledgment; Symbol = "SYNTHETIC"; Expected = "MODE_CONFLICT"
        }
    )
    foreach ($case in $cases) {
        $actual = Get-GateError `
            -LiveRequested $case.Live `
            -ReadOnlyConfirmed $case.Confirm `
            -SelfTestRequested $case.SelfTest `
            -Acknowledgment $case.Ack `
            -CandidateSymbol $case.Symbol
        if ($actual -cne $case.Expected) {
            return $false
        }
    }
    return $true
}

function Test-SummaryFilterContract {
    if (-not (Test-IsSafeRunnerLine -Line "STATUS=PASS")) {
        return $false
    }
    $unsafeCanaries = @(
        [string]::Concat("Author", "ization=Bearer_synthetic"),
        [string]::Concat("CLIENT_", "SECRET=synthetic_value"),
        "MARKET_REQUEST=raw body",
        "RAW_HEADERS={synthetic:value}",
        "STATUS=PASS=EXTRA"
    )
    foreach ($canary in $unsafeCanaries) {
        if (Test-IsSafeRunnerLine -Line $canary) {
            return $false
        }
    }
    return $true
}

function Invoke-SafeRunner {
    param([Parameter(Mandatory = $true)][string[]] $ArgumentList)

    try {
        $python = Get-VenvPython
        $runner = [System.IO.Path]::GetFullPath(
            (Join-Path $PSScriptRoot "toss_live_preflight_runner.py")
        )
        Assert-SafeMutableRepositoryFile -Path $runner
        $captured = @(& $python "-I" "-B" "-X" "utf8" $runner @ArgumentList 2>&1)
        $runnerExitCode = $LASTEXITCODE
    }
    catch {
        Write-FixedSummary -Summary ([ordered]@{
            MODE = "SAFE_WRAPPER"
            STAGE = "LOCAL"
            ERROR_CATEGORY = "SAFE_WRAPPER_FAILURE"
            STATUS = "FAIL"
        })
        return 1
    }

    $safeLines = [System.Collections.Generic.List[string]]::new()
    foreach ($capturedLine in $captured) {
        $line = [string] $capturedLine
        if (-not (Test-IsSafeRunnerLine -Line $line)) {
            Write-FixedSummary -Summary ([ordered]@{
                MODE = "SAFE_WRAPPER"
                STAGE = "LOCAL"
                ERROR_CATEGORY = "UNSAFE_CHILD_OUTPUT_BLOCKED"
                STATUS = "FAIL"
            })
            return 1
        }
        $safeLines.Add($line)
    }
    if ($safeLines.Count -eq 0) {
        Write-FixedSummary -Summary ([ordered]@{
            MODE = "SAFE_WRAPPER"
            STAGE = "LOCAL"
            ERROR_CATEGORY = "EMPTY_CHILD_OUTPUT"
            STATUS = "FAIL"
        })
        return 1
    }
    foreach ($line in $safeLines) {
        [Console]::Out.WriteLine($line)
    }
    return $runnerExitCode
}

try {
    if ($SelfTest) {
        if (-not (Test-OuterGateContract) -or -not (Test-SummaryFilterContract)) {
            Write-FixedSummary -Summary ([ordered]@{
                MODE = "SELF_TEST"
                EXTERNAL_NETWORK_REQUESTS = "0"
                GATE_VALIDATION = "FAIL"
                STATUS = "FAIL"
            })
            exit 1
        }

        $clientIdEntry = Get-Item -LiteralPath Env:TOSS_CLIENT_ID -ErrorAction SilentlyContinue
        $clientSecretEntry = Get-Item `
            -LiteralPath Env:TOSS_CLIENT_SECRET `
            -ErrorAction SilentlyContinue
        try {
            $env:TOSS_CLIENT_ID = ""
            $env:TOSS_CLIENT_SECRET = ""
            $selfTestExitCode = Invoke-SafeRunner -ArgumentList @("--self-test")
        }
        finally {
            if ($null -ne $clientIdEntry) {
                $env:TOSS_CLIENT_ID = $clientIdEntry.Value
            }
            else {
                Remove-Item -LiteralPath Env:TOSS_CLIENT_ID -ErrorAction SilentlyContinue
            }
            if ($null -ne $clientSecretEntry) {
                $env:TOSS_CLIENT_SECRET = $clientSecretEntry.Value
            }
            else {
                Remove-Item -LiteralPath Env:TOSS_CLIENT_SECRET -ErrorAction SilentlyContinue
            }
        }
        exit $selfTestExitCode
    }

    if (-not $Live) {
        $defaultGateError = Get-GateError `
            -LiveRequested $false `
            -ReadOnlyConfirmed ([bool] $ConfirmReadOnly) `
            -SelfTestRequested $false `
            -Acknowledgment $null `
            -CandidateSymbol ""
        if ($defaultGateError -eq "LIVE_NOT_REQUESTED") {
            Write-FixedSummary -Summary ([ordered]@{
                MODE = "OFFLINE"
                EXTERNAL_NETWORK_REQUESTS = "0"
                CREDENTIALS_USED = "0"
                STATUS = "LIVE_NOT_REQUESTED"
            })
            exit 0
        }
        Write-FixedSummary -Summary ([ordered]@{
            MODE = "LIVE"
            STAGE = "GATE"
            ERROR_CATEGORY = $defaultGateError
            STATUS = "FAIL"
        })
        exit 2
    }

    if (-not $ConfirmReadOnly) {
        Write-FixedSummary -Summary ([ordered]@{
            MODE = "LIVE"
            STAGE = "GATE"
            ERROR_CATEGORY = "READ_ONLY_CONFIRMATION_REQUIRED"
            STATUS = "FAIL"
        })
        exit 2
    }

    $acknowledgment = [Environment]::GetEnvironmentVariable(
        $acknowledgmentEnvironmentName,
        [EnvironmentVariableTarget]::Process
    )
    if ($acknowledgment -cne $exactAcknowledgment) {
        Write-FixedSummary -Summary ([ordered]@{
            MODE = "LIVE"
            STAGE = "GATE"
            ERROR_CATEGORY = "EXACT_ACK_REQUIRED"
            STATUS = "FAIL"
        })
        exit 2
    }

    $resolvedSymbol = $Symbol
    if ([string]::IsNullOrEmpty($resolvedSymbol)) {
        $resolvedSymbol = [Environment]::GetEnvironmentVariable(
            $symbolEnvironmentName,
            [EnvironmentVariableTarget]::Process
        )
    }
    $gateError = Get-GateError `
        -LiveRequested $true `
        -ReadOnlyConfirmed $true `
        -SelfTestRequested $false `
        -Acknowledgment $acknowledgment `
        -CandidateSymbol $resolvedSymbol
    if ($null -ne $gateError) {
        Write-FixedSummary -Summary ([ordered]@{
            MODE = "LIVE"
            STAGE = "GATE"
            ERROR_CATEGORY = $gateError
            STATUS = "FAIL"
        })
        exit 2
    }

    $liveExitCode = Invoke-SafeRunner -ArgumentList @(
        "--live",
        "--confirm-read-only",
        "--symbol",
        $resolvedSymbol
    )
    exit $liveExitCode
}
catch {
    Write-FixedSummary -Summary ([ordered]@{
        MODE = "SAFE_WRAPPER"
        STAGE = "LOCAL"
        ERROR_CATEGORY = "SAFE_WRAPPER_FAILURE"
        STATUS = "FAIL"
    })
    exit 1
}
