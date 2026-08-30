param([string]$At = '03:30')
$ErrorActionPreference = 'Stop'
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $AppRoot '..\..')
$Python = Join-Path $AppRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}
$Action = New-ScheduledTaskAction -Execute $Python -Argument 'scripts\refresh_trusted_campus_public_kb_v2.py --max-pages 300 --max-files 80' -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $At
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName 'TsingAskV2PublicKnowledgeRefresh' -Action $Action -Trigger $Trigger -Settings $Settings -Description 'Refresh public official TsingAsk V2 knowledge; never accesses the authenticated portal.' -Force
Write-Host '已注册每周公开知识库更新任务 TsingAskV2PublicKnowledgeRefresh' -ForegroundColor Green
