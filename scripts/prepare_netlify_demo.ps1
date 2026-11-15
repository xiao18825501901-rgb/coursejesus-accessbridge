param(
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $repo "apps\web\dist"

if (-not (Test-Path -LiteralPath (Join-Path $dist "accessbridge.html"))) {
    throw "Missing production build: $dist\accessbridge.html"
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDirectory = Join-Path $repo "runtime\netlify-competition-$stamp"
}
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputDirectory)
$runtimeRoot = [System.IO.Path]::GetFullPath((Join-Path $repo "runtime"))
if (-not $resolvedOutput.StartsWith($runtimeRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputDirectory must remain inside $runtimeRoot"
}
if (Test-Path -LiteralPath $resolvedOutput) {
    throw "Refusing to overwrite existing deploy directory: $resolvedOutput"
}

New-Item -ItemType Directory -Path $resolvedOutput | Out-Null
Copy-Item -Path (Join-Path $dist "*") -Destination $resolvedOutput -Recurse

# These redirects intentionally omit force markers. Existing hashed JS and CSS
# assets must be served directly; only application routes fall back to HTML.
@"
/  /accessbridge.html  200!
/*  /accessbridge.html  200
"@ | Set-Content -LiteralPath (Join-Path $resolvedOutput "_redirects") -Encoding ascii

@"
/*
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
"@ | Set-Content -LiteralPath (Join-Path $resolvedOutput "_headers") -Encoding ascii

Write-Output $resolvedOutput
