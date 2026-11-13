$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PidFile = Join-Path $ProjectRoot "runtime\server.pid"

if (-not (Test-Path -LiteralPath $PidFile)) {
    Write-Output "AccessBridge is not running (no PID file)."
    exit 0
}

$ServerPid = [int](Get-Content -Raw -LiteralPath $PidFile)
$Process = Get-CimInstance Win32_Process -Filter "ProcessId = $ServerPid" -ErrorAction SilentlyContinue
if (-not $Process) {
    Remove-Item -LiteralPath $PidFile -Force
    Write-Output "AccessBridge process $ServerPid was already stopped."
    exit 0
}

$ExpectedRoot = $ProjectRoot.Replace("\", "\\")
if ($Process.CommandLine -notmatch "app\.server" -or $Process.CommandLine -notmatch [regex]::Escape($ProjectRoot)) {
    throw "Refusing to stop PID $ServerPid because it is not the AccessBridge server for $ProjectRoot"
}

Stop-Process -Id $ServerPid
Remove-Item -LiteralPath $PidFile -Force
Write-Output "AccessBridge stopped (PID $ServerPid)."
