param(
    [string]$OutputDirectory = "submission",
    [string]$Version = "20261115"
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

if (@(git status --porcelain --untracked-files=no).Count -ne 0) {
    throw "Commit tracked changes before packaging."
}

$output = if ([IO.Path]::IsPathRooted($OutputDirectory)) {
    $OutputDirectory
} else {
    Join-Path $repo $OutputDirectory
}
New-Item -ItemType Directory -Force -Path $output | Out-Null

$sourceName = "CourseJesus_AccessBridge_Source_$Version.zip"
$demoName = "CourseJesus_AccessBridge_Demo_$Version.zip"
$sourceZip = Join-Path $output $sourceName
$demoZip = Join-Path $output $demoName
if ((Test-Path -LiteralPath $sourceZip) -or (Test-Path -LiteralPath $demoZip)) {
    throw "A versioned package already exists in $output. Choose a new version."
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$demoStage = Join-Path $repo "runtime\package-demo-$Version-$stamp"
$demoRoot = Join-Path $demoStage 'CourseJesus_AccessBridge_Demo'
New-Item -ItemType Directory -Force -Path $demoRoot | Out-Null

git archive --format=zip --prefix='CourseJesus_AccessBridge_Source/' -o $sourceZip HEAD
if ($LASTEXITCODE -ne 0) {
    throw "git archive failed."
}

Copy-Item -Recurse -Force `
    -LiteralPath (Join-Path $repo 'apps\web\dist') `
    -Destination (Join-Path $demoRoot 'frontend-dist')
Copy-Item -Recurse -Force `
    -LiteralPath (Join-Path $repo 'evidence\screenshots') `
    -Destination (Join-Path $demoRoot 'evidence\screenshots')
New-Item -ItemType Directory -Force -Path (Join-Path $demoRoot 'evidence') | Out-Null
foreach ($name in @('demo-captioned.mp4', 'demo-captions.srt', 'LIVE_ACCESS_EVIDENCE.json', 'RESULTS.json')) {
    Copy-Item -Force `
        -LiteralPath (Join-Path $repo "evidence\$name") `
        -Destination (Join-Path $demoRoot "evidence\$name")
}

New-Item -ItemType Directory -Force -Path (Join-Path $demoRoot 'submission') | Out-Null
Get-ChildItem -LiteralPath (Join-Path $repo 'submission') -File |
    Where-Object Extension -eq '.md' |
    Copy-Item -Destination (Join-Path $demoRoot 'submission')
foreach ($name in @(
    'README.md',
    'LICENSE_NOTES.md',
    'THIRD_PARTY_NOTICES.md',
    'OWNER_DECISIONS.json',
    'netlify.competition.toml',
    'scripts\serve_web_dist.mjs'
)) {
    $destination = Join-Path $demoRoot $name
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -Force -LiteralPath (Join-Path $repo $name) -Destination $destination
}

Compress-Archive -LiteralPath $demoRoot -DestinationPath $demoZip -CompressionLevel Optimal
$sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceZip).Hash
$demoHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $demoZip).Hash
@(
    "CourseJesus AccessBridge packages generated $((Get-Date).ToUniversalTime().ToString('o'))"
    "$sourceHash  $sourceName"
    "$demoHash  $demoName"
) | Set-Content -LiteralPath (Join-Path $output 'SHA256SUMS.txt') -Encoding ascii

Get-ChildItem -LiteralPath $sourceZip, $demoZip |
    Select-Object Name, Length
Get-Content -LiteralPath (Join-Path $output 'SHA256SUMS.txt')
