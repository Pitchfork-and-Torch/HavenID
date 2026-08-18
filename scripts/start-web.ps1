# Job-escape HavenID web start. This command must return in under 8 seconds.
# It does not wait for health. Never run next/npm as a Grok job.
# Usage:
#   powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\HavenID\scripts\start-web.ps1
# If this row is still running after 8s: Ctrl+B. Do not retry start.

param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 3000,
    [int]$TimeoutSec = 8
)

$ErrorActionPreference = "Stop"
& py -3 (Join-Path $PSScriptRoot "_start_local.py") start web --host $BindHost --port $Port --timeout $TimeoutSec
exit $LASTEXITCODE
