$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:PIP_CACHE_DIR = Join-Path $PSScriptRoot ".pip-cache"
New-Item -ItemType Directory -Force -Path $env:PIP_CACHE_DIR | Out-Null

if (-not (Test-Path ".venv-demucs314")) {
  python -m venv .venv-demucs314
}

& ".\.venv-demucs314\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
& ".\.venv-demucs314\Scripts\python.exe" -m pip install demucs
& ".\.venv-demucs314\Scripts\python.exe" -c "import torch, torchaudio, demucs; print('torch', torch.__version__); print('torchaudio', torchaudio.__version__); print('demucs ok')"

Write-Host ""
Write-Host "Demucs AI is installed. Restart the app and choose high quality or Demucs AI mode."
