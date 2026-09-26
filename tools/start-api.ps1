# PestKG Java API launcher — starts the backend on http://localhost:18088.
# Usage: powershell -ExecutionPolicy Bypass -File tools\start-api.ps1
# (run from the repository root)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$port = 18088
$listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Write-Host "Port $port is already in use (PID $($listener.OwningProcess)); leaving the running API as-is." -ForegroundColor Yellow
    exit 0
}

$jar = Join-Path $root 'apps\java\pestkg-api\target\pestkg-api-1.0.0-SNAPSHOT.jar'
if (-not (Test-Path $jar)) {
    Write-Host "Backend jar not found: $jar`nBuild it first with: mvn -q clean package (in apps\java)." -ForegroundColor Red
    exit 1
}

$env:PESTKG_DATA_DIR = 'data\releases'
$env:PESTKG_STATE_DIR = 'data\state'
$env:PESTKG_RELEASE_ID = 'PestKG_A_Data_Release_v1.0'

Write-Host "Starting PestKG API on http://localhost:$port ..."
Start-Process java -ArgumentList '-jar', "`"$jar`"" -WorkingDirectory $root `
    -RedirectStandardOutput (Join-Path $env:TEMP 'pestkg-api.log') `
    -RedirectStandardError (Join-Path $env:TEMP 'pestkg-api.err.log') | Out-Null

Start-Sleep -Seconds 8
$ready = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($ready) {
    Write-Host "API is up (PID $($ready.OwningProcess)). Frontend: npm run dev in apps\web (http://localhost:5173)." -ForegroundColor Green
} else {
    Write-Host "API did not become ready; check $env:TEMP\pestkg-api.err.log." -ForegroundColor Red
    exit 1
}
