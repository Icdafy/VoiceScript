$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
  $python = "py"
  & $python -3.12 -m voicescript env
  exit $LASTEXITCODE
}

& $python -m voicescript env
exit $LASTEXITCODE
