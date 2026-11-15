param(
    [string]$InputPath = "evidence\demo-raw.webm",
    [string]$CaptionsPath = "evidence\demo-captions.srt",
    [string]$OutputPath = "evidence\demo-captioned.mp4"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$inputFull = Join-Path $repo $InputPath
$captionsFull = Join-Path $repo $CaptionsPath
$outputFull = Join-Path $repo $OutputPath
if (-not (Test-Path -LiteralPath $inputFull)) {
    throw "Missing recorded video: $inputFull"
}
if (-not (Test-Path -LiteralPath $captionsFull)) {
    throw "Missing captions: $captionsFull"
}
$ffmpeg = (Get-Command ffmpeg -ErrorAction Stop).Source

& $ffmpeg -y -i $inputFull `
    -c:v libx264 -preset medium -crf 21 -pix_fmt yuv420p -movflags +faststart `
    $outputFull
if ($LASTEXITCODE -ne 0) {
    throw "ffmpeg caption burn-in failed."
}
Write-Host "Created $outputFull"
