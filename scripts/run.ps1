$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
& ".venv\Scripts\python.exe" -m app.server --host 127.0.0.1 --port 15273
