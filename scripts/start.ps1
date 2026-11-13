$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Runtime = Join-Path $ProjectRoot "runtime"
$PidFile = Join-Path $Runtime "server.pid"
$OutLog = Join-Path $Runtime "server.stdout.log"
$ErrLog = Join-Path $Runtime "server.stderr.log"
$Port = 15273

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Local Python environment not found at $Python. Follow README.md setup first."
}
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null

if (Test-Path -LiteralPath $PidFile) {
    $ExistingPid = [int](Get-Content -Raw -LiteralPath $PidFile)
    $Existing = Get-CimInstance Win32_Process -Filter "ProcessId = $ExistingPid" -ErrorAction SilentlyContinue
    if ($Existing -and $Existing.CommandLine -match "app\.server") {
        throw "AccessBridge is already running (PID $ExistingPid): http://127.0.0.1:$Port/"
    }
    Remove-Item -LiteralPath $PidFile -Force
}

Push-Location $ProjectRoot
try {
    & $Python -m app.build
    if ($LASTEXITCODE -ne 0) {
        throw "AccessBridge build failed with exit code $LASTEXITCODE"
    }
    $Process = Start-Process `
        -FilePath $Python `
        -ArgumentList @("-m", "app.server", "--host", "127.0.0.1", "--port", "$Port", "--no-build") `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $OutLog `
        -RedirectStandardError $ErrLog `
        -PassThru
    Set-Content -LiteralPath $PidFile -Value $Process.Id -Encoding ascii

    $Ready = $false
    for ($Attempt = 0; $Attempt -lt 40; $Attempt++) {
        Start-Sleep -Milliseconds 250
        try {
            $Health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/healthz" -TimeoutSec 1
            if ($Health.status -eq "ok") {
                $Ready = $true
                break
            }
        }
        catch {
            if ($Process.HasExited) {
                break
            }
        }
    }
    if (-not $Ready) {
        throw "AccessBridge did not become ready. Inspect $ErrLog"
    }
    Write-Output "AccessBridge ready: http://127.0.0.1:$Port/"
    Write-Output "PID: $($Process.Id)"
}
finally {
    Pop-Location
}
