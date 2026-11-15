param(
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]*$')]
    [string]$RuntimeName = 'competition-local'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$statePath = Join-Path $repo "runtime\$RuntimeName\run.json"

if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Host 'No recorded competition process is running.'
    exit 0
}

$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$processTable = @(Get-CimInstance Win32_Process)

function Test-HasAncestor($Process, [int]$AncestorPid) {
    $current = $Process
    for ($depth = 0; $current -and $depth -lt 16; $depth += 1) {
        if ($current.ParentProcessId -eq $AncestorPid) {
            return $true
        }
        $current = $processTable | Where-Object ProcessId -eq $current.ParentProcessId | Select-Object -First 1
    }
    return $false
}

foreach ($entry in $state.processes) {
    $process = $processTable | Where-Object ProcessId -eq $entry.pid | Select-Object -First 1
    if ($process -and $process.CommandLine -notlike "*$($entry.marker)*") {
        throw "PID $($entry.pid) does not contain the expected owner marker '$($entry.marker)'. Refusing to stop it."
    }
    $listener = Get-NetTCPConnection -LocalPort $entry.port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        $listenerProcess = $processTable | Where-Object ProcessId -eq $listener.OwningProcess | Select-Object -First 1
        $expectedListener = $listener.OwningProcess -eq $entry.pid -or
            ($entry.listener_pid -and $listener.OwningProcess -eq $entry.listener_pid) -or
            (Test-HasAncestor $listenerProcess $entry.pid)
        if (-not $expectedListener -or
            -not $listenerProcess -or
            $listenerProcess.CommandLine -notlike "*$($entry.marker)*") {
            throw "PID $($entry.pid) does not own the listener on port $($entry.port). Refusing to stop it."
        }
        if ($listener.OwningProcess -ne $entry.pid) {
            Stop-Process -Id $listener.OwningProcess
            Wait-Process -Id $listener.OwningProcess -Timeout 15 -ErrorAction SilentlyContinue
        }
    }
    if ($process) {
        Stop-Process -Id $entry.pid
        Wait-Process -Id $entry.pid -Timeout 15 -ErrorAction SilentlyContinue
    }
    Write-Host "Stopped $($entry.role) process $($entry.pid)."
}

Remove-Item -LiteralPath $statePath
Write-Host 'CourseJesus competition processes stopped.'
