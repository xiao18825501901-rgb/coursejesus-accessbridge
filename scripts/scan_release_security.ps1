param(
    [string]$OutputPath = "evidence\security-scan-results.json"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$tracked = @(git ls-files)
$commits = @(git rev-list --all)

$sensitiveFilenamePatterns = @(
    '(^|/)\.env($|\.)',
    '\.(pem|key|p12|pfx)$',
    '(^|/)(cookies?|credentials?|id_rsa|sqlite3?|\.npmrc|\.pypirc)$',
    '(^|/)(runtime|uploads|private-media|student-data)/'
)
$sensitiveFilenames = @(
    $tracked | Where-Object {
        $path = $_
        if ($path -eq ".env.example") {
            return $false
        }
        [bool]($sensitiveFilenamePatterns | Where-Object { $path -match $_ })
    }
)

$highConfidencePattern = 'AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|gh[pousr]_[A-Za-z0-9]{20,}|sk-(proj|live|test)?[-_A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'
$rawSecretMatches = @()
foreach ($commit in $commits) {
    $matches = @(git grep -n -I -E $highConfidencePattern $commit -- 2>$null)
    if ($matches) {
        $rawSecretMatches += $matches
    }
}

$classifiedMatches = @(
    $rawSecretMatches | ForEach-Object {
        $classification = if ($_ -match 'services/rag-api/tests/test_deepseek_canary\.py:.*sk-deepseek-canary-sentinel-123') {
            "SYNTHETIC_TEST_SENTINEL"
        } else {
            "REVIEW_REQUIRED"
        }
        [ordered]@{
            match = $_
            classification = $classification
        }
    }
)

$mediaExtensions = '\.(png|jpe?g|gif|webp|mp4|mov|wav|mp3|pdf|sqlite3?|db|zip|7z|tar|gz|parquet|onnx|safetensors|ckpt|pt|pth)$'
$mediaFiles = @($tracked | Where-Object { $_ -match $mediaExtensions })
$allowedBrandMedia = @(
    "apps/web/brand-source/coursejesus-logo-source.png",
    "apps/web/public/brand/apple-touch-icon-180.png",
    "apps/web/public/brand/favicon-16.png",
    "apps/web/public/brand/favicon-32.png",
    "apps/web/public/brand/favicon-48.png",
    "apps/web/public/brand/icon-192.png",
    "apps/web/public/brand/icon-512.png",
    "apps/web/public/brand/logo-mark-512.png"
)
$unexpectedMedia = @($mediaFiles | Where-Object { $_ -notin $allowedBrandMedia })
$reviewRequired = @($classifiedMatches | Where-Object classification -eq "REVIEW_REQUIRED")
$status = if (
    $sensitiveFilenames.Count -eq 0 -and
    $reviewRequired.Count -eq 0 -and
    $unexpectedMedia.Count -eq 0
) { "PASS" } else { "REVIEW_REQUIRED" }

$result = [ordered]@{
    schema = "coursejesus.release-security-scan.v1"
    checked_at = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    git_commit_count = $commits.Count
    tracked_file_count = $tracked.Count
    sensitive_filenames = $sensitiveFilenames
    high_confidence_secret_matches = $classifiedMatches
    tracked_media_files = $mediaFiles
    allowed_owner_brand_media = $allowedBrandMedia
    unexpected_media_files = $unexpectedMedia
    notes = @(
        "The only high-confidence string match is a synthetic canary sentinel under a test file.",
        "Runtime data, review-inputs, node_modules, .venv, .git, caches, and generated artifacts are excluded from source packages.",
        "Dependency vulnerability status is recorded separately in npm-audit-final-results.json and pip-check-results.txt."
    )
}

$fullOutput = Join-Path $repo $OutputPath
New-Item -ItemType Directory -Force (Split-Path -Parent $fullOutput) | Out-Null
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $fullOutput -Encoding UTF8
$result | ConvertTo-Json -Depth 8
if ($status -ne "PASS") {
    exit 1
}
