$ErrorActionPreference = 'Stop'
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $AppRoot '..\..')
$VenvPython = Join-Path $AppRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw '请先运行 apps\tsingask_v2\setup.ps1'
}
if (-not (Test-Path -LiteralPath (Join-Path $AppRoot 'frontend\dist\index.html'))) {
    throw '前端尚未构建，请先运行 setup.ps1'
}
Set-Location $RepoRoot
& $VenvPython -m uvicorn apps.tsingask_v2.backend.main:app --host 127.0.0.1 --port 8765
