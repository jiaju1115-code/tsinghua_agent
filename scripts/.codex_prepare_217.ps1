$root='D:\python_projects\tsinghua_ai\data_second'
$base=Join-Path $root 'public_rebuild_v1'
$out=Join-Path $root 'public_expansion_v2'
@('planning','crawl','raw','extracted','quality_gate','audit','candidates','human_check','reports') | ForEach-Object { New-Item -ItemType Directory -Force -Path (Join-Path $out $_) | Out-Null }
$rows=Get-Content -Encoding UTF8 (Join-Path $base 'audit\audit_results.jsonl') | ForEach-Object { $_ | ConvertFrom-Json }
$compact=foreach($r in $rows){
  $path=Join-Path $base $r.source_file
  $text=(Get-Content -Raw -Encoding UTF8 $path) -replace '\s+',' '
  [pscustomobject]@{id=$r.id;title=$r.title;url=$r.url;domain=$r.source_domain;source_file=$r.source_file;old_action=$r.action;old_category=$r.category;old_content_type=$r.content_type;old_time_status=$r.time_status;content_length=$text.Length;content_excerpt=$text.Substring(0,[Math]::Min(1800,$text.Length))}
}
$compact | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 (Join-Path $out 'planning\reaudit_217_compact.json')
[pscustomobject]@{count=$compact.Count;new_root=$out} | ConvertTo-Json -Compress
