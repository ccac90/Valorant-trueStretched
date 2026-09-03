$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    py -m venv (Join-Path $PSScriptRoot "venv")
}

& $python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --uac-admin `
    --name ValorantTrueStretch `
    (Join-Path $PSScriptRoot "stretch.py")

Write-Host "Build complete: $PSScriptRoot\dist\ValorantTrueStretch.exe"
