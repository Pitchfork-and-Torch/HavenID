# Prove the HavenID spawn path leaves the current Windows Job Object. Must return in under 10s.
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\selftest-breakaway.ps1

$ErrorActionPreference = "Stop"
& py -3 (Join-Path $PSScriptRoot "_job_breakaway.py") selftest
exit $LASTEXITCODE
