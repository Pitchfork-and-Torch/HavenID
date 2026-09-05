# Fast HavenID API probe. Always exits in about 2 seconds. Does not start anything.
param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)
$ErrorActionPreference = "Stop"
& py -3 (Join-Path $PSScriptRoot "_start_local.py") probe api --host $BindHost --port $Port
exit $LASTEXITCODE
