param(
    [switch]$SkipModel,
    [switch]$SkipDense,
    [switch]$RecreateVenv,
    [ValidateSet('auto','3.11','3.12','3.13')]
    [string]$PythonVersion = 'auto',
    [ValidateSet('auto','cpu','cu118','cu121','cu122','cu123','cu124','cu125','metal','vulkan','cuda-source','hipblas')]
    [string]$GpuBackend = 'auto'
)
$ErrorActionPreference = 'Stop'
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $AppRoot '..\..')
$VenvRoot = Join-Path $AppRoot '.venv'
$VenvPython = Join-Path $VenvRoot 'Scripts\python.exe'
$InstallTemp = Join-Path $AppRoot '.artifact_runtime\install_tmp'
New-Item -ItemType Directory -Force -Path $InstallTemp | Out-Null
$env:TEMP = $InstallTemp
$env:TMP = $InstallTemp

function Assert-NativeSuccess([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE" }
}

function New-TsingAskVenv {
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PythonVersion -ne 'auto') {
        if (-not $PyLauncher) {
            throw "Python launcher 'py' was not found; install Python $PythonVersion or create apps\tsingask_v2\.venv manually."
        }
        & $PyLauncher.Source "-$PythonVersion" -m venv $VenvRoot
        Assert-NativeSuccess "create Python $PythonVersion virtual environment"
        return
    }
    if ($PyLauncher) {
        foreach ($PreferredVersion in @('3.12', '3.11')) {
            & $PyLauncher.Source "-$PreferredVersion" -c "import sys; print(sys.version)" 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Creating virtual environment with preferred Python $PreferredVersion" -ForegroundColor Cyan
                & $PyLauncher.Source "-$PreferredVersion" -m venv $VenvRoot
                Assert-NativeSuccess "create Python $PreferredVersion virtual environment"
                return
            }
        }
    }
    Write-Warning 'Python 3.12/3.11 was not found through the py launcher; using the ambient python command.'
    python -m venv $VenvRoot
    Assert-NativeSuccess 'create virtual environment with ambient Python'
}

if ($RecreateVenv -and (Test-Path -LiteralPath $VenvRoot)) {
    $ResolvedAppRoot = [IO.Path]::GetFullPath($AppRoot).TrimEnd('\') + '\'
    $ResolvedVenvRoot = [IO.Path]::GetFullPath($VenvRoot).TrimEnd('\') + '\'
    if (-not $ResolvedVenvRoot.StartsWith($ResolvedAppRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove virtual environment outside the application directory: $ResolvedVenvRoot"
    }
    Write-Host "Removing recreatable virtual environment: $ResolvedVenvRoot" -ForegroundColor Yellow
    Remove-Item -LiteralPath $VenvRoot -Recurse -Force
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    New-TsingAskVenv
}
$VenvVersion = & $VenvPython -c "import platform; print(platform.python_version())"
Assert-NativeSuccess 'inspect virtual environment Python'
Write-Host "TsingAsk virtual environment Python: $VenvVersion" -ForegroundColor Cyan
if ([version]$VenvVersion -ge [version]'3.13') {
    Write-Warning 'Python 3.13 wheels are available for current backends, but this project is primarily validated on Python 3.11/3.12. The installer will run detailed import diagnostics and safely fall back to CPU in auto mode if GPU verification fails.'
}
if ($PythonVersion -ne 'auto' -and -not $VenvVersion.StartsWith("$PythonVersion.")) {
    Write-Warning "The existing .venv uses Python $VenvVersion, not requested Python $PythonVersion. Add -RecreateVenv to rebuild it."
}
& $VenvPython -m pip install --upgrade pip
Assert-NativeSuccess 'upgrade pip'
& $VenvPython -m pip install --prefer-binary -r (Join-Path $AppRoot 'requirements.txt')
Assert-NativeSuccess 'install Python dependencies'
& $VenvPython (Join-Path $RepoRoot 'scripts\install_tsingask_acceleration.py') --backend $GpuBackend
Assert-NativeSuccess 'install accelerator backend'
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
