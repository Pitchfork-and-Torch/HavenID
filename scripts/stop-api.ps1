# Stop the detached HavenID API started by start-api.ps1.
# Usage:
#   powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\HavenID\scripts\stop-api.ps1

param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PidFile = Join-Path $Root "apps\api\.local-run\uvicorn.pid"
$targets = New-Object System.Collections.Generic.HashSet[int]

if (Test-Path $PidFile) {
    $raw = (Get-Content $PidFile -Raw).Trim()
    if ($raw -match "^\d+$") { [void]$targets.Add([int]$raw) }
}

Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'py.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine -match "uvicorn" -and
        $_.CommandLine -match "app\.main:app" -and
        $_.CommandLine -match "--port\s+$Port"
    } |
    ForEach-Object { [void]$targets.Add([int]$_.ProcessId) }

$needle = ":$Port"
netstat -ano | Select-String -Pattern "LISTENING" | Where-Object {
    $_.Line -match [regex]::Escape($needle)
} | ForEach-Object {
    $parts = ($_.Line -split "\s+") | Where-Object { $_ }
    $procId = $parts[-1]
    if ($procId -match "^\d+$") { [void]$targets.Add([int]$procId) }
}

if ($targets.Count -eq 0) {
    Write-Host "ALREADY_DOWN :$Port"
    exit 0
}

foreach ($procId in $targets) {
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($p) {
        Write-Host "STOP pid=$procId $($p.ProcessName)"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

Start-Sleep -Milliseconds 400
Write-Host "DOWN :$Port"
exit 0
