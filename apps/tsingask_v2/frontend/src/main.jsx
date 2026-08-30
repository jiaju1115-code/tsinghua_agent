import React, { memo, useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import './responsive-fixes.css'

const Icon = memo(function Icon({ name, size = 18 }) {
  const paths = {
    plus: <><path d="M12 5v14M5 12h14"/></>,
    chat: <><path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/></>,
    paperclip: <><path d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.4-9.4a4 4 0 0 1 5.7 5.7l-9.4 9.4a2 2 0 0 1-2.8-2.8l8.8-8.8"/></>,
    send: <><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/></>,
    shield: <><path d="M20 13c0 5-3.5 7.5-8 9-4.5-1.5-8-4-8-9V5l8-3 8 3Z"/><path d="m9 12 2 2 4-4"/></>,
    source: <><circle cx="12" cy="12" r="9"/><path d="M8 12h8M12 8v8"/></>,
    download: <><path d="M12 3v12m0 0 4-4m-4 4-4-4"/><path d="M5 21h14"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    check: <><path d="m5 12 4 4L19 6"/></>,
    list: <><path d="M9 6h11M9 12h11M9 18h11"/><path d="M4 6h.01M4 12h.01M4 18h.01"/></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
})

const starter = {
  evidence_status: 'SUPPORTED',
  path: 'FAST',
  response: {
    answer: '你好，我是清问。现在我能核验证据、规划校园事务，也能生成和修改 Word、Excel、PPT 与 PDF。',
    confirmed_facts: [], action_plan: null, citations: [], clarification_questions: [], search_guidance: [],
  },
}

function Badge({ status }) {
  const label = { SUPPORTED: '证据充分', PARTIAL: '部分支持', CONFLICT: '存在冲突', NOT_SUPPORTED: '证据不足' }[status] || status
  return <span className={`badge ${status?.toLowerCase()}`}><Icon name="shield" size={14}/>{label}</span>
}

const SourcePanel = memo(function SourcePanel({ result, coverage, tasks, sessionId, onTaskUpdate }) {
  const citations = result?.response?.citations || []
  const artifact = result?.artifact
  return <aside className="source-panel">
    <div className="panel-title"><span>证据与产物</span><span className="source-count">{citations.length} 个来源</span></div>
    <div className="trust-card">
      <div className="trust-head"><Icon name="shield"/><strong>可信回答状态</strong></div>
      <Badge status={result?.evidence_status || artifact?.evidence_status || 'SUPPORTED'}/>
      <p>结论只来自当前服务库中的公开、可追溯资料。证据不足时不会补猜。</p>
    </div>
    {artifact ? <div className="download-card">
      <div className="file-mark"><Icon name="file" size={24}/></div>
      <div className="file-copy"><strong>{artifact.filename}</strong><span>{artifact.format?.toUpperCase()} · {Math.ceil((artifact.size_bytes || 0) / 1024)} KB</span></div>
      <a className="download-btn" href={artifact.download_url}><Icon name="download" size={16}/>下载</a>
    </div> : null}
    <div className="sources">
      {citations.length ? citations.map((item, index) => <a className="source-item" href={item.url} target="_blank" rel="noreferrer" key={`${item.source_id}-${index}`}>
        <div className="source-index">{index + 1}</div><div><strong>{item.title}</strong><span>{item.url?.replace(/^https?:\/\//, '').split('/')[0]}</span></div>
      </a>) : <div className="empty-sources"><Icon name="source"/><p>完成一次校园事务检索后，官方来源会显示在这里。</p></div>}
    </div>
    <div className="task-card">
      <div className="task-head"><span><Icon name="list" size={15}/>事务工作区</span>{sessionId ? <a href={`/api/sessions/${sessionId}/calendar.ics`}>导出日历</a> : null}</div>
      {tasks.length ? tasks.slice(0, 8).map(task => <button className={`task-row ${task.status}`} key={task.task_id} onClick={() => onTaskUpdate(task)}><i>{task.status === 'done' ? <Icon name="check" size={13}/> : null}</i><span>{task.text}</span></button>) : <p className="task-empty">流程回答中的材料、步骤和截止时间会自动沉淀到这里。</p>}
    </div>
    {coverage ? <div className="coverage-card"><span>知识覆盖</span><strong>{Object.values(coverage).filter(x => x.status === 'COVERED').length}/8 场景</strong><div className="coverage-bar"><i style={{width: `${Object.values(coverage).filter(x => x.status === 'COVERED').length * 12.5}%`}}/></div></div> : null}
  </aside>
})

function ActionPlan({ value }) {
  if (!value) return null
  const fields = [['conditions', '适用条件'], ['materials', '材料清单'], ['steps', '办理步骤'], ['deadlines', '截止时间'], ['official_entries', '官方入口']]
  const active = fields.filter(([key]) => value[key]?.length)
  if (!active.length) return null
  return <section className="action-card"><div className="section-kicker">NEXT ACTIONS</div><h3>下一步行动清单</h3>
    <div className="action-grid">{active.map(([key, title]) => <div className="action-block" key={key}><h4>{title}</h4><ol>{value[key].map((item, i) => <li key={i}>{item}</li>)}</ol></div>)}</div>
  </section>
}

function Clarification({ response, onChoose }) {
  const questions = response?.clarification_questions || []
  const guidance = response?.search_guidance || []
  if (!questions.length && !guidance.length) return null
  return <section className="clarify-card">
    {questions.length ? <><div className="section-kicker">NEED TO KNOW</div><h3>补充这些信息，我能继续帮你查</h3><div className="question-list">{questions.map((item, index) => <button key={item} onClick={() => onChoose(item)}><span>{index + 1}</span>{item}</button>)}</div></> : null}
    {guidance.length ? <div className="guidance"><h4>也可以先这样找</h4>{guidance.map((item, index) => item.url ? <a key={`${item.label}-${index}`} href={item.url} target="_blank" rel="noreferrer"><strong>{item.label}</strong><span>{item.how}</span></a> : <div key={`${item.label}-${index}`}><strong>{item.label}</strong><span>{item.how}</span></div>)}</div> : null}
  </section>
}

function Answer({ result, loading, onClarify, onFeedback }) {
  if (loading) return <div className="answer loading"><span/><span/><span/><p>正在理解问题、检索证据并核验时效性…</p></div>
  const response = result?.response
  if (!response) return null
  return <div className="answer">
    <div className="answer-meta"><Badge status={result.evidence_status || 'SUPPORTED'}/><span><Icon name="clock" size={14}/>{result.path === 'FULL' ? '完整检索' : '快速路径'} · {Math.round(result.total_latency_ms || 0)} ms</span></div>
    <h2>可信结论</h2><p className="lead">{response.answer}</p>
    {response.confirmed_facts?.length ? <div className="fact-list">{response.confirmed_facts.map((fact, i) => <div className="fact" key={`${fact.source_id}-${i}`}><span>{i + 1}</span><p>{fact.text}</p></div>)}</div> : null}
    {response.historical_versions?.length ? <div className="history-note"><strong>发现历史版本</strong><p>系统已优先采用较新的有效官方来源，历史版本仅供追溯。</p></div> : null}
    <Clarification response={response} onChoose={onClarify}/>
    <ActionPlan value={response.action_plan}/>
    {result.case_id ? <div className="feedback-row"><span>这次回答有问题？</span><button onClick={() => onFeedback('irrelevant_source')}>来源不相关</button><button onClick={() => onFeedback('outdated')}>资料过时</button><button onClick={() => onFeedback('missing_step')}>缺少步骤</button></div> : null}
  </div>
}

function App() {
  const [message, setMessage] = useState('')
  const [result, setResult] = useState(starter)
  const [loading, setLoading] = useState(false)
  const [upload, setUpload] = useState(null)
  const [coverage, setCoverage] = useState(null)
  const [error, setError] = useState('')
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('tsingask:v2:session') || '')
  const [tasks, setTasks] = useState([])
  const fileRef = useRef(null)
  const textRef = useRef(null)

  useEffect(() => {
    const sessionPromise = sessionId ? Promise.resolve({ session_id: sessionId }) : fetch('/api/sessions', { method: 'POST' }).then(r => r.json())
    Promise.all([fetch('/api/coverage').then(r => r.ok ? r.json() : null), sessionPromise]).then(([matrix, session]) => {
      setCoverage(matrix); setSessionId(session.session_id); localStorage.setItem('tsingask:v2:session', session.session_id)
      return fetch(`/api/sessions/${session.session_id}/tasks`).then(r => r.ok ? r.json() : [])
    }).then(setTasks).catch(() => {})
  }, [])

  async function pickFile(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setError('')
    const body = new FormData(); body.append('file', file)
    try {
      const response = await fetch('/api/uploads', { method: 'POST', body })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '上传失败')
      setUpload(data)
    } catch (value) { setError(value.message) }
  }

  async function submit(event) {
    event?.preventDefault()
    const query = message.trim()
    if (!query || loading) return
    setLoading(true); setError('')
    try {
      const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: query, upload_ids: upload ? [upload.file_id] : [], session_id: sessionId || null }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || '智能体暂时不可用')
      setResult(data); setMessage(''); setTasks(current => data.workspace?.tasks || current)
    } catch (value) { setError(value.message) }
    finally { setLoading(false) }
  }

  async function newChat() {
    try {
      const response = await fetch('/api/sessions', { method: 'POST' }); const data = await response.json()
      setSessionId(data.session_id); localStorage.setItem('tsingask:v2:session', data.session_id)
    } catch { /* the next chat will create a session server-side */ }
    setResult(starter); setMessage(''); setUpload(null); setTasks([])
  }

  async function updateTask(task) {
    const next = task.status === 'done' ? 'todo' : 'done'
    const response = await fetch(`/api/sessions/${sessionId}/tasks/${task.task_id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: next }) })
    if (response.ok) setTasks(current => current.map(item => item.task_id === task.task_id ? { ...item, status: next } : item))
  }

  async function feedback(kind) {
    await fetch('/api/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ case_id: result.case_id, kind, detail: '' }) })
  }

  function startClarification(question) {
    const prefix = question.includes('当前院系和目标院系') ? '我目前在____，想转到____。' : question.includes('本科生、研究生') ? '我是____。' : question.includes('学年、学期') ? '我要办理的批次是____。' : question.includes('交换项目') ? '我要申请的是____交换项目。' : '补充信息：____。'
    setMessage(prefix)
    requestAnimationFrame(() => { textRef.current?.focus(); textRef.current?.setSelectionRange(prefix.indexOf('____'), prefix.indexOf('____') + 4) })
  }

  const shortcuts = ['本科生转系需要什么条件和材料？', '根据学校最新要求生成社会实践报告 Word', '读取并修改我上传的会议纪要']
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-seal">清</div><div><strong>清问</strong><span>TsingAsk</span></div></div>
      <button className="new-chat" onClick={newChat}><Icon name="plus"/>新建事务</button>
      <div className="nav-label">最近对话</div>
      <nav>{shortcuts.map((item, i) => <button key={item} className={i === 0 ? 'active' : ''} onClick={() => setMessage(item)}><Icon name="chat" size={16}/><span>{item}</span></button>)}</nav>
      <div className="sidebar-bottom"><div className="status-dot"/><div><strong>本地独立运行</strong><span>公开知识库 · 本地模型</span></div></div>
    </aside>
    <main className="workspace">
      <header><div><span className="eyebrow">TRUSTED CAMPUS AGENT</span><h1>把校园问题，变成可靠的下一步</h1></div><div className="header-status"><span/>独立版 V2</div></header>
      <div className="content-grid">
        <section className="conversation">
          <div className="user-query"><div className="avatar">你</div><p>{result?.query || '清问可以帮我做什么？'}</p></div>
          <Answer result={result} loading={loading} onClarify={startClarification} onFeedback={feedback}/>
          {error ? <div className="error-box">{error}</div> : null}
          <div className="composer-wrap">
            {upload ? <div className="upload-chip"><Icon name="file" size={15}/><span>{upload.filename}</span><button onClick={() => setUpload(null)}>×</button></div> : null}
            <form className="composer" onSubmit={submit}>
              <textarea ref={textRef} value={message} onChange={e => setMessage(e.target.value)} placeholder="问校园事务，或让我生成 / 修改文件…" rows="2" onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}/>
              <div className="composer-actions"><input ref={fileRef} type="file" accept=".docx,.xlsx,.pptx,.pdf" hidden onChange={pickFile}/><button type="button" className="attach" onClick={() => fileRef.current?.click()}><Icon name="paperclip"/><span>上传文件</span></button><button className="send" type="submit" disabled={!message.trim() || loading}><Icon name="send" size={17}/></button></div>
            </form>
            <p className="disclaimer">证据不足时会继续追问并给出官方查找方向；重要事项仍请点击来源复核。</p>
          </div>
        </section>
        <SourcePanel result={result} coverage={coverage} tasks={tasks} sessionId={sessionId} onTaskUpdate={updateTask}/>
      </div>
    </main>
  </div>
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>)
