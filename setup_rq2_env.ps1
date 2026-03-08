param(
    [string]$VenvPath = ".venv311"
)

$ErrorActionPreference = "Stop"

Write-Host "=== RQ2 Environment Setup ==="

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3.11 -m venv $VenvPath
} else {
    python -m venv $VenvPath
}

& "$VenvPath\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
& "$VenvPath\Scripts\python.exe" -m pip install -r "AgoneTest/requirements.txt"

npm install -g @google/gemini-cli

Write-Host "Done. Use:"
Write-Host "  $VenvPath\Scripts\Activate.ps1"
Write-Host "  gemini.cmd --version"
