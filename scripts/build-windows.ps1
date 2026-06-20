$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$releaseDir = Join-Path $root "release"
$stageDir = Join-Path $releaseDir "package"
$zipPath = Join-Path $releaseDir "VoiceScript-v0.2.2-windows-x64.zip"

Set-Location $root

if (-not (Test-Path $venvPython)) {
  py -3.12 -m venv .venv
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e ".[dev]"
& $venvPython -m pytest tests -q
& $venvPython -m PyInstaller --clean --noconfirm VoiceScript.spec

if (Test-Path $releaseDir) {
  Remove-Item -LiteralPath $releaseDir -Recurse -Force
}
New-Item -ItemType Directory -Path $releaseDir | Out-Null
New-Item -ItemType Directory -Path $stageDir | Out-Null
Copy-Item -Path (Join-Path $root "dist\VoiceScript") -Destination $stageDir -Recurse -Force
Compress-Archive -Path (Join-Path $stageDir "VoiceScript") -DestinationPath $zipPath -Force
Remove-Item -LiteralPath $stageDir -Recurse -Force

Write-Host "Built $zipPath"
