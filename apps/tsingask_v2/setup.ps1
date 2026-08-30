param([switch]$SkipModel, [switch]$SkipDense)
$ErrorActionPreference = 'Stop'
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $AppRoot '..\..')
$VenvPython = Join-Path $AppRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $VenvPython)) {
    python -m venv (Join-Path $AppRoot '.venv')
}
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $AppRoot 'requirements.txt')

Push-Location (Join-Path $AppRoot 'frontend')
try {
    npm install
    npm run build
} finally {
    Pop-Location
}

Push-Location $RepoRoot
try {
    if (-not $SkipModel) { & $VenvPython scripts\download_tsingask_local_model.py }
    if ($SkipDense) { & $VenvPython scripts\build_trusted_campus_public_kb_v2.py --no-dense }
    else { & $VenvPython scripts\build_trusted_campus_public_kb_v2.py }
} finally {
    Pop-Location
}
Write-Host 'TsingAsk V2 setup complete. Run apps\tsingask_v2\start.ps1' -ForegroundColor Green
