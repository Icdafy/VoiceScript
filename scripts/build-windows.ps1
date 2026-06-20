$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

$python = ".\.venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -e ".[dev]"
& $python -m unittest discover -s tests -v
& $python -m PyInstaller --noconfirm VoiceScript.spec

Write-Host "Build output: $root\dist\VoiceScript"
