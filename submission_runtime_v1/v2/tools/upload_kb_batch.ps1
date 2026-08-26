param(
    [Parameter(Mandatory = $true)]
    [string[]]$ContentPaths,
    [string]$DatasetId = '7674979933138976768',
    [int]$Port = 9223,
    [string]$TabId = '63FD0714DA5EEBE32E4C73889810EC14',
    [int]$WaitSeconds = 20
)

$ErrorActionPreference = 'Stop'
$docs = @($ContentPaths | ForEach-Object {
    $path = (Resolve-Path -LiteralPath $_).Path
    [ordered]@{ name = [IO.Path]::GetFileName($path); content = Get-Content -Raw -LiteralPath $path }
})
if ($docs.Count -eq 0) { throw 'No content paths supplied.' }
$docsJson = $docs | ConvertTo-Json -Depth 5 -Compress
$datasetJson = $DatasetId | ConvertTo-Json -Compress

$expression = @"
(()=>{
  const docs=$docsJson;
  const dataset=$datasetJson;
  const bases=docs.map(d=>({name:d.name,source_info:{custom_content:d.content,document_source:2}}));
  fetch('/studio/api/knowledge/document/create',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({dataset_id:dataset,format_type:0,document_bases:bases,chunk_strategy:{chunk_type:0},parsing_strategy:{parsing_type:1,image_extraction:true,table_extraction:true,image_ocr:false}})}).then(async r=>window.__codexBatchUpload={status:r.status,body:(await r.text()).slice(0,3000),count:bases.length}).catch(e=>window.__codexBatchUpload={error:String(e),count:bases.length});
  return {sent:true,count:bases.length,names:docs.map(d=>d.name)};
})()
"@

& "$PSScriptRoot\cdp_eval.ps1" -Port $Port -TabId $TabId -Expression $expression
Start-Sleep -Seconds $WaitSeconds
$resultExpression = 'window.__codexBatchUpload||null'
& "$PSScriptRoot\cdp_eval.ps1" -Port $Port -TabId $TabId -Expression $resultExpression
