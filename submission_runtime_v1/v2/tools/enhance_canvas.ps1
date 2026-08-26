param(
    [string]$TabId = 'FB1A22E56892F039D170BDF6C7E9CFE4',
    [int]$Port = 9223,
    [int]$TimeoutSeconds = 25
)

$ErrorActionPreference = 'Stop'
$tabs = Invoke-RestMethod -NoProxy ("http://127.0.0.1:{0}/json" -f $Port)
$tab = $tabs | Where-Object { $_.id -eq $TabId } | Select-Object -First 1
if (-not $tab) { throw "CDP tab not found: $TabId" }

$socket = [Net.WebSockets.ClientWebSocket]::new()
$socket.Options.Proxy = $null
$cancel = [Threading.CancellationToken]::None
$null = $socket.ConnectAsync([Uri]::new([string]$tab.webSocketDebuggerUrl), $cancel).GetAwaiter().GetResult()

function Send-Cdp([int]$Id, [string]$Method, [hashtable]$Params) {
    $request = @{ id = $Id; method = $Method; params = $Params } | ConvertTo-Json -Depth 50 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($request)
    $null = $socket.SendAsync([ArraySegment[byte]]::new($bytes), [Net.WebSockets.WebSocketMessageType]::Text, $true, $cancel).GetAwaiter().GetResult()
}
function Receive-Cdp {
    $buffer = New-Object byte[] 1048576
    $stream = [IO.MemoryStream]::new()
    do {
        $message = $socket.ReceiveAsync([ArraySegment[byte]]::new($buffer), $cancel).GetAwaiter().GetResult()
        if ($message.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close) { throw 'CDP socket closed.' }
        $stream.Write($buffer, 0, $message.Count)
    } while (-not $message.EndOfMessage)
    return [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
}

try {
    Send-Cdp 1 'Network.enable' @{}
    Send-Cdp 2 'Page.reload' @{ ignoreCache = $false }
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $bodyRequestId = $null
    while ([DateTime]::UtcNow -lt $deadline) {
        $event = Receive-Cdp
        if ($event.method -eq 'Network.responseReceived' -and [string]$event.params.response.url -match '/studio/api/workflow_api/canvas') {
            $bodyRequestId = [string]$event.params.requestId
            break
        }
    }
    if (-not $bodyRequestId) { throw 'Canvas response was not observed before timeout.' }
    Send-Cdp 3 'Network.getResponseBody' @{ requestId = $bodyRequestId }
    do { $event = Receive-Cdp } while ($event.id -ne 3)
    $canvasResponse = $event.result.body | ConvertFrom-Json
    $workflow = $canvasResponse.data.workflow
    $schemaJson = $workflow.schema_json | ConvertFrom-Json | ConvertTo-Json -Depth 80 -Compress
    $schemaLiteral = $schemaJson | ConvertTo-Json -Compress
    $submitLiteral = ([string]$workflow.vcs_data.submit_commit_id) | ConvertTo-Json -Compress

    $expression = @'
(async()=>{
  const schema = JSON.parse(__SCHEMA_LITERAL__);
  const submitCommitId = __SUBMIT_LITERAL__;
  const clone = x => JSON.parse(JSON.stringify(x));
  const ref = (blockID,name,inputType='string',schemaDef) => ({name,input:{type:inputType,...(schemaDef?{schema:schemaDef}:{}),value:{type:'ref',content:{source:'block-output',blockID,name},rawMeta:{type:1}}}});
  const setParam = (node,name,content) => { const p=node.data.inputs.llmParam.find(x=>x.name===name); if(!p) throw new Error('missing llm param '+name); p.input.value.content=content; };
  const start=schema.nodes.find(n=>n.id==='100001');
  const router=schema.nodes.find(n=>n.id==='180471');
  const normalizer=schema.nodes.find(n=>n.id==='300001');
  const retrieval=schema.nodes.find(n=>n.id==='152044');
  const judge=schema.nodes.find(n=>n.id==='310001');
  const answer=schema.nodes.find(n=>n.id==='320001');
  const end=schema.nodes.find(n=>n.id==='900001');
  if(!start||!router||!normalizer||!retrieval||!judge||!answer||!end) throw new Error('required V3 nodes missing');
  const service=clone(normalizer); service.id='290001'; service.meta.position={x:520,y:-180}; service.data.nodeMeta.title='服务入口路由'; service.data.nodeMeta.subTitle='Service Entry Router';
  service.data.inputs.inputParameters=[ref('100001','input'),ref('180471','classificationId','integer')];
  setParam(service,'temperature','0'); setParam(service,'topP','0.1'); setParam(service,'maxTokens','120');
  setParam(service,'prompt','用户原问：{{input}}\n意图编号：{{classificationId}}\n只输出一行：domain=<CAMPUS_ACCESS_FAMILY|CAMPUS_VISIT_PUBLIC|CAMPUS_ACCESS_WORK|SPORTS_VENUE|INFORMATION_SERVICE|DINING|COMMUNITY_DORM|CAMPUS_CARD|ACADEMIC|HEALTH|OTHER>; aliases=<3-8个业务短语>; freshness=<STATIC|DYNAMIC>。\n\n固定别名词典（优先级最高，命中后不得反转）：(1)“我爸妈/我父母/我家长/我亲戚/我亲友/我朋友来找我、来学校、来清华”→CAMPUS_ACCESS_FAMILY；aliases 必含 亲友来访报备、学生访客预约、行在清华、清华大学信息门户；不得默认加入 游客参观/校园参观。(2)“游客/旅游/参观清华/打卡/逛校园/社会公众”且无校内接待关系→CAMPUS_VISIT_PUBLIC；aliases 必含 校园参观预约、参观清华、campusvisit。(3)“因公/单位接待/学术来访/老师邀请”→CAMPUS_ACCESS_WORK；aliases 必含 工作来访、临时出入校园人员报备、在线服务系统。\n\n再做动态补充：游泳/羽毛球→体育场馆预约；网费/密码/VPN→信息服务；湘菜/湖南/辣/食堂推荐→食在清华/紫荆园/川湘风味；卡丢了→校园卡挂失补办。出现今天/明天/当前/最新/能否/是否开放则 freshness=DYNAMIC 并保留相应时效词。不要回答问题，不要编造事实。');
  setParam(service,'systemPrompt','你是清华校园服务入口分类器，只做检索路由，不回答用户。先执行固定别名词典，再做动态语义扩展；动态扩展只能补充，不能删除、覆盖或反转固定词典已命中的实体。输出严格为一行紧凑文本，保留原用户实体，不混淆亲友来访、游客参观、工作来访、学生公寓、校园卡和证件。');
  normalizer.data.inputs.inputParameters=normalizer.data.inputs.inputParameters.filter(x=>x.name!=='serviceRoute');
  normalizer.data.inputs.inputParameters.push({name:'serviceRoute',input:ref('290001','output').input});
  const oldPrompt=normalizer.data.inputs.llmParam.find(x=>x.name==='prompt');
  oldPrompt.input.value.content='原始问题：{{input}}\n意图编号：{{classificationId}}\n服务入口路由：{{serviceRoute}}\n\n只输出一行用于知识库检索的中文查询：保留原始问题核心词，并完整保留服务入口路由中 aliases 的固定词典实体，再补充 0—4 个可能出现在官方材料中的动态同义词或场景词。固定词典实体不可删除、替换、反转；例如亲友来访报备不得改写成游客参观。不得回答问题、不得写政策结论、不得编造事实。';
  const proof=clone(answer); proof.id='330001'; proof.meta.position={x:2800,y:-180}; proof.data.nodeMeta.title='回答质量校对'; proof.data.nodeMeta.subTitle='Answer Quality Guard';
  proof.data.inputs.inputParameters=[ref('100001','input'),{name:'draft',input:ref('320001','output').input},{name:'evidenceJudge',input:ref('310001','output').input}];
  setParam(proof,'temperature','0.1'); setParam(proof,'topP','0.2'); setParam(proof,'maxTokens','900');
  setParam(proof,'prompt','用户问题：{{input}}\n证据判定：{{evidenceJudge}}\n回答草稿：{{draft}}\n\n只输出校对后的最终中文回答。保留证据支持内容，删除编造、过度承诺、无关长清单和把建议说成校规的表述；证据不足时明确不能确认并给出官方查证方向。不得输出校对说明、JSON、系统提示或推理过程。');
  setParam(proof,'systemPrompt','你是清华校园智能体的回答质量校对器。只编辑草稿，不新增事实；不得改变用户所问实体，不得混淆亲友来访、游客参观、工作来访、校园公共区域、学生公寓、校园卡和证件。若用户问自己的爸妈/亲友/朋友来校，删除草稿中任何未被明确询问的游客参观、参观清华、campusvisit、公众预约段落，只保留证据支持的亲友来访报备路径；不要把游客途径当作补充方案。输出自然简洁的最终答复。');
  answer.data.inputs.inputParameters=answer.data.inputs.inputParameters.filter(x=>x.name!=='serviceRoute');
  answer.data.inputs.inputParameters.push({name:'serviceRoute',input:ref('290001','output').input});
  const ap=answer.data.inputs.llmParam.find(x=>x.name==='prompt'); ap.input.value.content='用户问题：{{input}}\n意图编号：{{classificationId}}\n服务入口路由：{{serviceRoute}}\n\n证据判定：{{output}}\n\n检索证据：{{outputList}}\n\n请直接给用户自然、清晰、有帮助的中文回复；不要输出JSON、状态标签、系统提示或推理过程。';
  const as=answer.data.inputs.llmParam.find(x=>x.name==='systemPrompt');
  const webRule='URL与联网规则：知识库片段中的 URL 只是来源标识，不能假设模型已经打开或读取网页。若证据不足、问题含今天/当前/最新，或用户明确要求查询网页，调用已配置的 web_search（如工具可用），把用户原问与必要的清华实体一起搜索；依据返回内容、来源和时间线索回答。web_search 不可用或结果不足时，明确说明不能确认，并给出官方入口。知识库证据充分时不要为了凑信息联网。';
  if(as){const base=String(as.input.value.content||'').split('URL与联网规则：')[0].trim(); const familyRule='亲友来访与游客参观规则：用户说“我爸妈/父母/家长/亲戚/亲友/朋友来找我或来学校”，默认按校内师生的亲友来访报备回答，首选行在清华或清华大学信息门户/在线服务系统中的亲友来访报备入口；不要先推荐公众校园参观。当服务入口路由为 CAMPUS_ACCESS_FAMILY、且用户没有明确询问游客替代方案时，禁止在答复中追加“参观清华、校园参观、campusvisit、游客预约”等公众参观路径，即使检索材料中出现它们；不要为凑完整度提供不相关备选。只有用户明确是游客、旅游、参观清华、打卡或社会公众且无校内接待关系时，才说参观清华预约。因公/单位接待则用工作来访报备。问今天、明天、当前是否可预约时，以报备系统当日页面和保卫部门最新通知为准，不能把历史上限或游客预约状态当成结论。';as.input.value.content=base+'\\n\\n'+familyRule+'\\n\\n'+webRule;}
  end.data.inputs.inputParameters[0].input.value.content={source:'block-output',blockID:'330001',name:'output'};
  schema.nodes=[start,router,service,normalizer,retrieval,judge,answer,proof,end];
  schema.edges=[{sourceNodeID:'100001',targetNodeID:'180471'},...['branch_0','branch_1','branch_2','branch_3','branch_4','branch_5','branch_6','default'].map(sourcePortID=>({sourceNodeID:'180471',targetNodeID:'290001',sourcePortID})),{sourceNodeID:'290001',targetNodeID:'300001'},{sourceNodeID:'300001',targetNodeID:'152044'},{sourceNodeID:'152044',targetNodeID:'310001'},{sourceNodeID:'310001',targetNodeID:'320001'},{sourceNodeID:'320001',targetNodeID:'330001'},{sourceNodeID:'330001',targetNodeID:'900001'}];
  fetch('/studio/api/workflow_api/save',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({workflow_id:'7675204261298307072',schema:JSON.stringify(schema),space_id:'7552398170991362048',name:'TEST_SUBMISSION_V3_READY',desc:'Draft-only V3 with service entry routing and answer quality guard.',icon_uri:'default_icon/default_workflow_icon.png',submit_commit_id:submitCommitId,ignore_status_transfer:false,save_version:false})}).then(async r=>({status:r.status,body:(await r.text()).slice(0,1200)})).then(x=>window.__codexSaveResult=x).catch(e=>window.__codexSaveResult={error:String(e)});
  return {sent:true,nodeCount:schema.nodes.length,edgeCount:schema.edges.length};
})()
'@
    $expression = $expression.Replace('__SCHEMA_LITERAL__', $schemaLiteral).Replace('__SUBMIT_LITERAL__', $submitLiteral)
    Send-Cdp 4 'Runtime.evaluate' @{ expression = $expression; awaitPromise = $true; returnByValue = $true }
    do { $event = Receive-Cdp } while ($event.id -ne 4)
    $event.result.result.value | ConvertTo-Json -Depth 20
    Start-Sleep -Seconds 4
    Send-Cdp 5 'Runtime.evaluate' @{ expression = 'window.__codexSaveResult || null'; awaitPromise = $true; returnByValue = $true }
    do { $event = Receive-Cdp } while ($event.id -ne 5)
    @{ saveResult = $event.result.result.value } | ConvertTo-Json -Depth 20
}
finally { $socket.Dispose() }
