param(
    [Parameter(Mandatory = $true)]
    [string]$Query,
    [string]$WorkflowId = '7675204261298307072',
    [string]$SpaceId = '7552398170991362048',
    [string]$ProjectId = '7674978993728126976',
    [int]$Port = 9223,
    [string]$TabId = 'FB1A22E56892F039D170BDF6C7E9CFE4'
)

$ErrorActionPreference = 'Stop'
$queryJson = $Query | ConvertTo-Json -Compress
$workflowJson = $WorkflowId | ConvertTo-Json -Compress
$spaceJson = $SpaceId | ConvertTo-Json -Compress
$projectJson = $ProjectId | ConvertTo-Json -Compress

$expression = @'
(async () => {
  const workflowId = __WORKFLOW_JSON__;
  const spaceId = __SPACE_JSON__;
  const projectId = __PROJECT_JSON__;
  const query = __QUERY_JSON__;
  const post = async (path, body) => (await fetch(path, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify(body)})).json();
  const launch = await post('/studio/api/workflow_api/test_run', {workflow_id: workflowId, input:{input:query}, space_id:spaceId, project_id:projectId, submit_commit_id:'', commit_id:''});
  if (launch.code !== 0) return {stage:'launch', launch};
  const executeId = launch.data.execute_id;
  await new Promise(resolve => setTimeout(resolve, 30000));
  const nodeIds = [['router','180471',22],['retrieval','152044',6],['judge','310001',3],['answer','320001',3],['end','900001',2]];
  const logs = {};
  for (const [key, nodeId, nodeType] of nodeIds) {
    const params = new URLSearchParams({workflow_id:workflowId, space_id:spaceId, execute_id:executeId, node_id:nodeId, is_batch:'false', batch_index:'0', node_type:String(nodeType)});
    logs[key] = await (await fetch('/studio/api/workflow_api/get_node_execute_history?' + params)).json();
  }
  return {query, executeId, logs};
})()
'@
$expression = $expression.Replace('__WORKFLOW_JSON__', $workflowJson).Replace('__SPACE_JSON__', $spaceJson).Replace('__PROJECT_JSON__', $projectJson).Replace('__QUERY_JSON__', $queryJson)

& "$PSScriptRoot/cdp_eval.ps1" -Port $Port -TabId $TabId -Expression $expression
