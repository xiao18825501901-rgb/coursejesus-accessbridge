param(
    [switch]$SkipBuild,
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]*$')]
    [string]$RuntimeName = 'competition-local'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $repo "runtime\$RuntimeName"
$dataDirectory = Join-Path $runtimeRoot 'data'
$logDirectory = Join-Path $runtimeRoot 'logs'
$statePath = Join-Path $runtimeRoot 'run.json'
$databasePath = Join-Path $dataDirectory 'rag.sqlite3'
$uploadDirectory = Join-Path $dataDirectory 'uploads'
$uiDataDirectory = Join-Path $dataDirectory 'ui-extension'
$webPort = 15273
$apiPort = 15274
$webUrl = "http://127.0.0.1:$webPort"
$apiUrl = "http://127.0.0.1:$apiPort"
$python = Join-Path $repo '.venv\Scripts\python.exe'
$webBuild = Join-Path $repo 'apps\web\dist\ui.html'
$node = (Get-Command node -ErrorAction Stop).Source

function Assert-PortAvailable([int]$Port) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        throw "Port $Port is already in use by PID $($listener.OwningProcess)."
    }
}

function Wait-HttpOk([string]$Url, [int]$TimeoutSeconds = 90) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for $Url."
}

if (Test-Path -LiteralPath $statePath) {
    throw "A competition run is already recorded at $statePath. Stop it before starting another."
}
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing isolated Python environment: $python"
}
$nodeVersion = [Version]((& $node --version).TrimStart('v'))
if ($nodeVersion -lt [Version]'24.14.0') {
    throw "CourseJesus requires Node.js 24.14.0 or newer; found $nodeVersion."
}
Assert-PortAvailable $webPort
Assert-PortAvailable $apiPort

New-Item -ItemType Directory -Force -Path $runtimeRoot, $logDirectory | Out-Null
if (-not (Test-Path -LiteralPath $databasePath)) {
    & $python (Join-Path $repo 'scripts\prepare_competition_browser.py') $dataDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Competition fixture preparation failed."
    }
}
New-Item -ItemType Directory -Force -Path $uiDataDirectory | Out-Null
if (-not (Test-Path -LiteralPath $uploadDirectory)) {
    New-Item -ItemType Directory -Path $uploadDirectory | Out-Null
}

if (-not $SkipBuild -and -not (Test-Path -LiteralPath $webBuild)) {
    Push-Location $repo
    try {
        & npm --workspace '@coursemate/web' run build
        if ($LASTEXITCODE -ne 0) {
            throw "The production web build failed."
        }
    } finally {
        Pop-Location
    }
}
if (-not (Test-Path -LiteralPath $webBuild)) {
    throw "Missing production web build: $webBuild"
}

$env:APP_ENV = 'test'
$env:CMUI_ENV = 'test'
$env:V3_ENABLED = 'true'
$env:UI_EXTENSION_ENABLED = 'true'
$env:CMUI_DATA_DIR = $uiDataDirectory
$env:CMUI_VERIFICATION_SECRET = 'competition-local-verification-secret'
$env:GUEST_SESSION_SECRET = 'competition-local-guest-session-secret'
$env:GUEST_SESSION_TTL_SECONDS = '900'
$env:CMUI_PROVIDER_MODE = 'test'
$env:RAG_PROVIDER_MODE = 'deterministic'
$env:CMUI_ALLOWED_ORIGINS = $webUrl
$env:WEB_ORIGIN = $webUrl
$env:AUTH_TEST_USER_ID = 'competition-local-owner'
$env:ADMIN_USER_IDS = ''
$env:RAG_DATABASE_PATH = $databasePath
$env:RAG_UPLOAD_DIR = $uploadDirectory
$env:VISUAL_ENGINE_ENABLED = 'true'
$env:VISUAL_PROVIDER = 'mock'
$env:VISUAL_AUTO_ENABLED = 'false'
$env:VISUAL_VIDEO_ENABLED = 'false'
$env:AUTO_KNOWLEDGE_MAP_ENABLED = 'false'

$processes = @()
try {
    $api = Start-Process -FilePath $python `
        -WorkingDirectory (Join-Path $repo 'services\rag-api') `
        -ArgumentList '-m','uvicorn','app.main:create_app','--factory','--host','127.0.0.1','--port',"$apiPort" `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDirectory 'api.out.log') `
        -RedirectStandardError (Join-Path $logDirectory 'api.err.log') `
        -PassThru
    $processes += $api
    Wait-HttpOk "$apiUrl/health"

    $env:COURSEMATE_API_PROXY = $apiUrl
    $web = Start-Process -FilePath $node `
        -WorkingDirectory $repo `
        -ArgumentList (Join-Path $repo 'scripts\serve_web_dist.mjs'),(Join-Path $repo 'apps\web\dist'),"$webPort" `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDirectory 'web.out.log') `
        -RedirectStandardError (Join-Path $logDirectory 'web.err.log') `
        -PassThru
    $processes += $web
    Wait-HttpOk "$webUrl/ui-extension/"

    $env:COMPETITION_WEB_URL = $webUrl
    & $python (Join-Path $repo 'scripts\check_local_guest.py')
    if ($LASTEXITCODE -ne 0) {
        throw "The real HTTP guest-isolation smoke check failed."
    }
    Remove-Item Env:COMPETITION_WEB_URL
    $apiListener = (Get-NetTCPConnection -LocalPort $apiPort -State Listen -ErrorAction Stop).OwningProcess
    $webListener = (Get-NetTCPConnection -LocalPort $webPort -State Listen -ErrorAction Stop).OwningProcess

    @{
        schema = 2
        repository = $repo
        started_at = (Get-Date).ToUniversalTime().ToString('o')
        web_url = "$webUrl/ui-extension/"
        api_url = $apiUrl
        processes = @(
            @{ role = 'api'; pid = $api.Id; listener_pid = $apiListener; marker = 'app.main:create_app'; port = $apiPort },
            @{ role = 'web'; pid = $web.Id; listener_pid = $webListener; marker = 'serve_web_dist.mjs'; port = $webPort }
        )
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statePath -Encoding UTF8

    Write-Host "CourseJesus competition build: $webUrl/ui-extension/"
    Write-Host "Logs: $logDirectory"
    Write-Host 'Stop with scripts\stop_competition.ps1.'
} catch {
    foreach ($process in $processes) {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id
        }
    }
    throw
} finally {
    Remove-Item Env:COURSEMATE_API_PROXY -ErrorAction SilentlyContinue
}
