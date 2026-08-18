# Fast HavenID web probe. Always exits in about 2 seconds. Does not start anything.
param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 3000
)
$ErrorActionPreference = "Stop"
& py -3 (Join-Path $PSScriptRoot "_start_local.py") probe web --host $BindHost --port $Port
exit $LASTEXITCODE
