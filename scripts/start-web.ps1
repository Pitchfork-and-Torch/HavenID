# Detached HavenID web start. Returns in under 8 seconds. Does not wait for health.
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\start-web.ps1

param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 3000,
    [int]$TimeoutSec = 8
)

$ErrorActionPreference = "Stop"
& py -3 (Join-Path $PSScriptRoot "_start_local.py") start web --host $BindHost --port $Port --timeout $TimeoutSec
exit $LASTEXITCODE
