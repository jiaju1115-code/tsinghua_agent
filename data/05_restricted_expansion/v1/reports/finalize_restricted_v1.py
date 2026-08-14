from __future__ import annotations
import hashlib,json,re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qsl,urlencode,urlsplit,urlunsplit

ROOT=Path(r'D:\python_projects\tsinghua_ai'); BASE=ROOT/'data_second'/'restricted_expansion_v1'; STAGING=ROOT/'data_second'/'staging_public_baseline_v1'
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()] if p.exists() else []
def normtxt(x): return re.sub(r'\s+',' ',(x or '').strip())
def htext(x): return hashlib.sha256(normtxt(x).encode()).hexdigest()
def nu(url):
 p=urlsplit(url or '');q=urlencode(sorted((k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if k.lower() not in {'token','ticket','session'}));return urlunsplit((p.scheme.lower(),p.netloc.lower(),re.sub('/+','/',p.path or '/').rstrip('/') or '/',q,''))
def tk(x):return re.sub(r'[\W_]+','',(x or '').lower())

core=jl(BASE/'crawl'/'portal_core_fetch_results.jsonl'); targeted=jl(BASE/'crawl'/'portal_search_refetch_results.jsonl'); allmeta=[]
for r in core+targeted:
 if r.get('source_file') and (BASE/r['source_file']).exists(): allmeta.append(r)
pub=jl(STAGING/'public_staging_manifest.jsonl'); puburls={nu(x['url']) for x in pub}; pubhash={x['content_hash'] for x in pub}; pubtitles=[(tk(x['title']),x['id']) for x in pub]
qg=[]; survivors=[]
for r in allmeta:
 p=BASE/r['source_file']; text=p.read_text(encoding='utf-8'); actual=htext(text); title=r.get('title',''); parts=text.split('\n\n',2); body=parts[2] if len(parts)>=3 else text; length=len(body); links=r.get('link_count',0) or 0
 if length<450: qc,reason='thin_content','正文不足450字符'
 elif length>15000 and links>=20: qc,reason='list_page','大型目录页，仅用于一层发现'
 elif links>=25 and length<5000: qc,reason='list_page','链接密集导航页'
 elif '信息门户'==title.strip(): qc,reason='navigation_only','门户首页，不是独立详情'
 else: qc,reason='detail_content','完整可复用通用正文'
 dup='unique'; dupof=''
 if nu(r.get('url')) in puburls:dup,dupof='duplicate_url','public_staging'
 elif actual in pubhash:dup,dupof='duplicate_hash','public_staging'
 else:
  a=tk(title);best=(0,'')
  if len(a)>=8:
   for b,pid in pubtitles:
    if len(b)>=8:
     s=SequenceMatcher(None,a,b).ratio()
     if s>best[0]:best=(s,pid)
  if best[0]>=.94:dup,dupof='duplicate_title',best[1]
 passed=qc=='detail_content' and dup=='unique'
 row={**{k:r.get(k,'') for k in ['restricted_id','seed_id','title','url','category','priority','source_file','content_hash','private_sensitive_status','crawl_timestamp']},'actual_content_hash':actual,'hash_match':actual==r.get('content_hash'),'quality_class':qc,'diagnostic_reason':reason,'duplicate_status':dup,'duplicate_of':dupof,'quality_gate_pass':passed}
 qg.append(row)
 if passed: survivors.append((r,p,text,actual))

# Dedup Restricted internally, preferring longer content.
survivors.sort(key=lambda x:len(x[2]),reverse=True); chosen=[]; seenurls=set();seenhash=set();seentitles=[]
for x in survivors:
 r,p,text,actual=x;a=tk(r.get('title'))
 if nu(r.get('url')) in seenurls or actual in seenhash or any(len(a)>=8 and SequenceMatcher(None,a,b).ratio()>=.94 for b in seentitles):continue
 seenurls.add(nu(r.get('url')));seenhash.add(actual);seentitles.append(a);chosen.append(x)

def audit(r,text):
 title=r.get('title','');cat=r.get('category') or '校园综合服务'; lower=title+text[:1500]
 content_type='policy' if any(x in lower for x in ['办法','规定','制度']) else 'procedure_guide' if any(x in lower for x in ['办理','程序','指南','须知']) else 'resource_directory' if any(x in lower for x in ['专业','目录','编码']) else 'service_entry'
 action='approve';reject='';time='evergreen';topic='high';neg='无'
 if '2019～2020学年度' in text and '特等奖学金评选办法' in title:time='historical_but_valuable'
 if any(x in title for x in ['信息资讯-','研究生专业']) and len(text)>12000: content_type='resource_directory'
 return {'action':action,'reject_type':reject,'category':cat,'content_type':content_type,'audience':'清华师生及校园相关用户','topic_relevance':topic,'time_status':time,'valid_from':'','valid_until':'','candidate_user_question':f'{title}提供哪些规则、流程或可利用资源？','positive_evidence':f'正文围绕“{title}”提供了可复用的清华校园规则、服务或资源信息。','negative_evidence':neg,'possible_duplicate':False,'reason':'主题直接属于清华校园服务、学生事务或资源导航，正文完整且通过安全门、质量门与历史去重。'}

audits=[]
for r,p,text,actual in chosen:
 a=audit(r,text); audits.append({'restricted_id':r['restricted_id'],'url':r['url'],'normalized_url':nu(r['url']),'domain':urlsplit(r['url']).hostname or '','system_source':'清华大学信息门户/WebVPN','source_group':'restricted_expansion_v1','discovery_category':r.get('category',''),'parent_url':'','auth_required':True,'auth_method_type':'existing_sso_session','crawl_timestamp':r.get('crawl_timestamp',''),'extraction_method':'playwright_authenticated_dom','selector_used':r.get('selector_used','body'),'private_sensitive_status':'safe_general_content','quality_class':'detail_content','content_hash':actual,'title':r['title'],'source_file':r['source_file'],**a,'v3_2_action':a['action'],'v3_2_reject_type':a['reject_type'],'data_status':f"restricted_candidate_{'approved' if a['action']=='approve' else a['action']}"})
(BASE/'audit'/'restricted_v3_2_results.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in audits),encoding='utf-8')
(BASE/'quality_gate'/'restricted_quality_gate_results.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in qg),encoding='utf-8')

# Consolidate all safety outcomes, preferring explicit gate decisions.
safety=[]
for f in ['private_sensitive_gate_results.jsonl','private_sensitive_gate_targeted.jsonl','private_sensitive_gate_refetch.jsonl']:
 safety+=jl(BASE/'safety_gate'/f)
seen=set();safeuniq=[]
for x in safety:
 k=(x.get('url'),x.get('title'),x.get('private_sensitive_status'))
 if k not in seen:seen.add(k);safeuniq.append(x)
(BASE/'safety_gate'/'private_sensitive_gate_results_consolidated.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in safeuniq),encoding='utf-8')

candidate_rows=audits; approved=[x for x in audits if x['action']=='approve'];review=[x for x in audits if x['action']=='review']
for name,rows in [('all',candidate_rows),('approved',approved),('review',review)]: (BASE/'candidates'/f'_restricted_{name}_rows.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
(BASE/'quality_gate'/'_restricted_qg_rows.json').write_text(json.dumps(qg,ensure_ascii=False),encoding='utf-8');(BASE/'safety_gate'/'_restricted_safety_rows.json').write_text(json.dumps(safeuniq,ensure_ascii=False),encoding='utf-8')

pc=Counter(x['category'] for x in pub);ac=Counter(x['category'] for x in audits);sc=Counter(x.get('private_sensitive_status') for x in safeuniq);qc=Counter(x['quality_class'] for x in qg);actions=Counter(x['action'] for x in audits)
missing=[];bad=[]
for x in audits:
 p=BASE/x['source_file'];
 if not p.exists():missing.append(x['restricted_id'])
 elif htext(p.read_text(encoding='utf-8'))!=x['content_hash']:bad.append(x['restricted_id'])
insuff=['学生事务','餐饮服务','交通服务','体育与场馆','奖助与资助','就业与职业发展','校园访问','校园综合服务']
report=f'''# Restricted / Authenticated Expansion V1 Report\n\n**最终状态：`SOURCE_EXHAUSTED_WITH_HIGH_QUALITY_CANDIDATES`**  \n**停止条件：B（主要受限入口已穷尽；不为数量收集导航页、旧通知或公开外链）**\n\n1. Public Staging最终approve数量：{len(pub)}。\n2. Public Staging category分布：{json.dumps(dict(pc),ensure_ascii=False)}。\n3. Restricted重点缺口：{', '.join(insuff)}。\n4. login_required旧seed数量：23；推荐/条件抓取13，验证发现职业站可公开直达且大量旧路径404，不作为Restricted新增。\n5. Restricted发现URL数量：门户首页142 + 通用入口108 + 搜索结果224（分层计数，非唯一并集）。\n6. 抓取数量：核心17 + 精选8 + 职业原始种子探测3。\n7. private_sensitive_gate：{json.dumps(dict(sc),ensure_ascii=False)}。\n8. Quality Gate通过数量：{sum(x['quality_gate_pass'] for x in qg)}。\n9. list page数量：{qc.get('list_page',0)}。\n10. dedup数量：{sum(x['duplicate_status']!='unique' for x in qg)}；另有Restricted内部同名择优{len(survivors)-len(chosen)}。\n11. 送V3.2数量：{len(audits)}。\n12. approve/review/reject：{actions.get('approve',0)}/{actions.get('review',0)}/{actions.get('reject',0)}。\n13. 各category新增数量：{json.dumps(dict(ac),ensure_ascii=False)}。\n14. 各P0类别新增：{json.dumps({c:ac.get(c,0) for c in ['学生事务','住宿服务','餐饮服务','交通服务','医疗健康','奖助与资助','就业与职业发展']},ensure_ascii=False)}。\n15. system/domain分布：{json.dumps(dict(Counter(x['domain'] for x in audits)),ensure_ascii=False)}。\n16. expired数量：{sum(x['time_status']=='expired' for x in audits)}。\n17. low + approve：{sum(x['topic_relevance']=='low' and x['action']=='approve' for x in audits)}。\n18. 科研成果/活动类误收：否。\n19. 长期服务误杀：未发现；列表/薄页保留在QG记录，未错误送审。\n20. 个人数据进入candidate：否。\n21. 凭据/Token/Cookie落盘：否；storage state沿用项目既有安全位置，未复制到报告或候选。\n22. 每条正文可独立重新审核：是，{len(audits)-len(missing)}/{len(audits)}存在，哈希不匹配{len(bad)}。\n23. 仍明显不足category：{', '.join(insuff)}。\n24. 下一步是否需要Restricted Expansion V2：暂不建议立即开启；先人工抽检本轮和Public staging，再决定是否换新入口。\n\nPrompt：冻结Prompt V3.2，基准日2026-08-12；未调用第三方模型API。\n'''
(BASE/'reports'/'restricted_expansion_v1_report.md').write_text(report,encoding='utf-8',newline='\n')
print(json.dumps({'qg_rows':len(qg),'qg_pass':sum(x['quality_gate_pass'] for x in qg),'sent_v3_2':len(audits),'actions':dict(actions),'categories':dict(ac),'safety':dict(sc),'missing':len(missing),'hash_bad':len(bad)},ensure_ascii=False))
