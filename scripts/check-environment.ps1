param(
    [string]$CacheDir = "$env:USERPROFILE\.cache\voicescript"
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

& $python -m voicescript env --cache-dir $CacheDir
