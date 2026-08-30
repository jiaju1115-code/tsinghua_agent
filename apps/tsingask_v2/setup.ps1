param([switch]$SkipModel, [switch]$SkipDense)
$ErrorActionPreference = 'Stop'
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $AppRoot '..\..')
$VenvPython = Join-Path $AppRoot '.venv\Scripts\python.exe'
$InstallTemp = Join-Path $AppRoot '.artifact_runtime\install_tmp'
New-Item -ItemType Directory -Force -Path $InstallTemp | Out-Null
$env:TEMP = $InstallTemp
$env:TMP = $InstallTemp

function Assert-NativeSuccess([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE" }
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    python -m venv (Join-Path $AppRoot '.venv')
    Assert-NativeSuccess 'create virtual environment'
}
& $VenvPython -m pip install --upgrade pip
Assert-NativeSuccess 'upgrade pip'
& $VenvPython -m pip install --prefer-binary -r (Join-Path $AppRoot 'requirements.txt')
Assert-NativeSuccess 'install Python dependencies'
& $VenvPython -c "import fastapi, uvicorn, numpy, torch, transformers, llama_cpp, docx, openpyxl, pptx, reportlab, pypdf, pdfplumber; print('Python dependencies ready')"
Assert-NativeSuccess 'verify Python dependencies'

Push-Location (Join-Path $AppRoot 'frontend')
try {
    npm install
    Assert-NativeSuccess 'install frontend dependencies'
    npm run build
    Assert-NativeSuccess 'build frontend'
} finally {
    Pop-Location
}

Push-Location $RepoRoot
try {
    if (-not $SkipModel) {
        & $VenvPython scripts\download_tsingask_local_model.py
        Assert-NativeSuccess 'download and verify local model'
    }
    if ($SkipDense) {
        & $VenvPython scripts\build_trusted_campus_public_kb_v2.py --no-dense
    } else {
        & $VenvPython scripts\build_trusted_campus_public_kb_v2.py
    }
    Assert-NativeSuccess 'build trusted campus knowledge base'
} finally {
    Pop-Location
}
Write-Host 'TsingAsk V2 setup complete. Run apps\tsingask_v2\start.ps1' -ForegroundColor Green
