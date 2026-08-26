param(
    [Parameter(Mandatory = $true)]
    [string]$ContentPath,
    [Parameter(Mandatory = $true)]
    [string]$DocumentName,
    [string]$DatasetId = '7674979933138976768',
    [int]$Port = 9223,
    [string]$TabId = '63FD0714DA5EEBE32E4C73889810EC14'
)

$ErrorActionPreference = 'Stop'
$content = Get-Content -Raw -LiteralPath $ContentPath
$contentJson = $content | ConvertTo-Json -Compress
$nameJson = $DocumentName | ConvertTo-Json -Compress
$datasetJson = $DatasetId | ConvertTo-Json -Compress

$expression = @'
(async () => {
  const response = await fetch('/studio/api/knowledge/document/create', {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({
      dataset_id: __DATASET_JSON__,
      format_type: 0,
      document_bases: [{
        name: __NAME_JSON__,
        source_info: {custom_content: __CONTENT_JSON__, document_source: 2}
      }],
      chunk_strategy: {chunk_type: 0},
      parsing_strategy: {parsing_type: 1, image_extraction: true, table_extraction: true, image_ocr: false}
    })
  });
  return {status: response.status, body: await response.json()};
})()
'@
$expression = $expression.Replace('__DATASET_JSON__', $datasetJson).Replace('__NAME_JSON__', $nameJson).Replace('__CONTENT_JSON__', $contentJson)

& "$PSScriptRoot/cdp_eval.ps1" -Port $Port -TabId $TabId -Expression $expression
