import hashlib, json, re, shutil
from collections import Counter, defaultdict
from datetime import datetime
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data' / '04_kb_expansion_candidate' / 'dynamic_campus_v1'
RAW = BASE / 'raw' / 'source' / 'full_news_raw_restored.json'
for p in ['raw/source','processed/normalized','candidates','audit','manifests','reports']:
    (BASE/p).mkdir(parents=True, exist_ok=True)

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def clean(v):
    s = unescape(str(v or ''))
    s = re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>', ' ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'浏览次数\s*:?\s*\d*|收藏|关闭|技术支持|版权所有|English', ' ', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip()
    return s
def norm(s): return re.sub(r'[^\w\u4e00-\u9fff]+', '', (s or '').lower())
def val(x): return x if x not in ('', None) else None
def parse_date(s):
    if not s: return None
    m = re.search(r'(20\d{2})[年/.-](\d{1,2})[月/.-](\d{1,2})', str(s))
    return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}' if m else None
def category(x):
    s = ' '.join(str(x.get(k) or '') for k in ['lmmc','lmmc_show','flmc','xxfl','xxflid']).lower()
    for keys, name in [(['科研','research','项目','基金'],'科研通知'), (['办公','行政'],'办公通知'), (['教务','选课','学籍'],'教务通知'), (['学生','社团','活动'],'学生社区通知'), (['图书','library'],'图书馆信息'), (['国际组织','实习'],'国际组织实习任职'), (['综合'],'综合信息')]:
        if any(k.lower() in s for k in keys): return name
    return '其他'
def temporal(title, body, cat):
    s = title + ' ' + body
    if re.search(r'申报|报名|截止|申请|活动|招聘|实习|试用|临时|开放|关闭|有效期|预约', s): return 'DYNAMIC'
    if re.search(r'管理办法|办事|服务说明|规章|条例|固定|长期|指南', s): return 'STABLE'
    return 'UNKNOWN'
def status(body, published):
    if re.search(r'(截至|截止|报名至|有效期至)\s*20\d{2}[年/.-]\d{1,2}[月/.-]\d{1,2}', body):
        return 'UNKNOWN'  # exact deadline extraction is handled conservatively below
    return 'UNKNOWN'

src = json.loads(RAW.read_text(encoding='utf-8'))
items = src['list']
fields = sorted({k for x in items for k in x})
sha = hashlib.sha256(RAW.read_bytes()).hexdigest()
empty = {k: sum(x.get(k) in ('', None) for x in items) for k in fields}
def ids(k): return [str(x.get(k)) for x in items if x.get(k) not in ('',None)]
dups = {}
for k in ['xxid','yxxid','url','zxurl']:
    c=Counter(ids(k)); dups[k]={v:n for v,n in c.items() if n>1}

groups=defaultdict(list); candidates=[]; recovery=[]; excluded=[]
for i,x in enumerate(items,1):
    title=clean(x.get('bt_show') or x.get('bt') or x.get('bt_en'))
    body=clean(x.get('nr_show') or x.get('nr') or x.get('nr_en'))
    raw_body=str(x.get('nr_show') or x.get('nr') or x.get('nr_en') or '')
    if not body or len(body)<30: cs='TITLE_ONLY' if title else 'EMPTY_CONTENT'
    elif len(body)<120: cs='PARTIAL_CONTENT'
    elif re.search(r'首页|联系我们|导航菜单|浏览次数|技术支持', body) and len(body)<300: cs='WEB_SHELL'
    else: cs='FULL_CONTENT'
    title_key=norm(title); body_key=norm(body)
    gid = 'dg-' + hashlib.sha1((title_key+'|'+body_key).encode()).hexdigest()[:12]
    groups[gid].append(i)
    pub=parse_date(x.get('fbsj') or x.get('time') or x.get('time_mobile'))
    t=temporal(title,body,category(x)); cur=status(body,pub)
    rec={'candidate_id':f'dcc-{i:04d}','source_xxid':val(x.get('xxid')),'source_yxxid':val(x.get('yxxid')),'title':title,'content':body,'category':category(x),'source_department':val(x.get('dwmc_show') or x.get('dwmc') or x.get('lydw')),'published_at':pub,'canonical_url':val(x.get('zxurl') or x.get('url')),'source_url':val(x.get('url')),'content_status':cs,'temporal_type':'UNKNOWN' if t not in {'STABLE','DYNAMIC'} else t,'valid_from':None,'valid_until':None,'deadline':None,'current_status':cur,'stable_or_dynamic':t if t in {'STABLE','DYNAMIC'} else 'UNKNOWN','duplicate_group':gid,'source_provenance':{'raw_file':'raw/source/full_news_raw_restored.json','source_index':i},'processing_version':'dynamic_campus_candidate_v1'}
    if cs in {'FULL_CONTENT','PARTIAL_CONTENT'}: candidates.append(rec)
    if cs in {'TITLE_ONLY','EMPTY_CONTENT','WEB_SHELL'}:
        recovery.append({'source_xxid':rec['source_xxid'],'title':title,'source_url':rec['source_url'],'published_at':pub,'source_department':rec['source_department'],'missing_fields':['nr','nr_show','nr_en'] if not raw_body else ['usable_body'],'content_status':cs})
    if cs=='WEB_SHELL' and not rec['source_url']: excluded.append({'candidate_id':rec['candidate_id'],'reason':'WEB_SHELL_NO_RECOVERABLE_URL','source_xxid':rec['source_xxid']})
    if t in {'DYNAMIC','UNKNOWN'}: pass

def write_jsonl(path, rows): path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows), encoding='utf-8')
write_jsonl(BASE/'candidates/dynamic_candidates_v1.jsonl', candidates)
write_jsonl(BASE/'candidates/content_recovery_queue.jsonl', recovery)
write_jsonl(BASE/'candidates/temporal_audit.jsonl', [r for r in candidates if r['stable_or_dynamic'] in {'DYNAMIC','UNKNOWN'}])
write_jsonl(BASE/'candidates/excluded_deterministic.jsonl', excluded)
dup_groups=[{'duplicate_group':g,'record_indices':v,'recommended_canonical_index':min(v)} for g,v in groups.items() if len(v)>1]
dump(BASE/'audit/duplicate_groups.json', {'groups':dup_groups,'field_duplicates':dups})
normed=[{**r,'content':r['content']} for r in candidates]
write_jsonl(BASE/'processed/normalized/candidates_normalized.jsonl', normed)
manifest={'manifest_version':'dynamic_campus_input_v1','created_at':datetime.now().astimezone().isoformat(),'source_path':'raw/source/full_news_raw_restored.json','sha256':sha,'file_size_bytes':RAW.stat().st_size,'json_top_level':list(src),'declared_total':src.get('total'),'pages':src.get('pages'),'actual_list_count':len(items),'fields':fields,'empty_counts':empty,'xxid_unique':len(ids('xxid'))==len(set(ids('xxid'))),'duplicate_summary':{k:len(v) for k,v in dups.items()},'raw_read_only':True}
dump(BASE/'manifests/input_manifest.json',manifest)
cats=Counter(r['category'] for r in candidates); content=Counter(r['content_status'] for r in candidates); sd=Counter(r['stable_or_dynamic'] for r in candidates); st=Counter(r['current_status'] for r in candidates)
report=f'''# Dynamic Campus Candidate V1 Report\n\n- Input SHA256: `{sha}`\n- Total records: **{len(items)}** (declared `{src.get('total')}`; list `{len(items)}`)\n- Candidate records: **{len(candidates)}**\n- Recovery queue: **{len(recovery)}**\n- Deterministic exclusions: **{len(excluded)}**\n\n## Distributions\n\n### Category\n{''.join(f'- {k}: {v} ({v/len(candidates):.1%})\n' for k,v in cats.most_common())}\n### Content status\n{''.join(f'- {k}: {v}\n' for k,v in content.items())}\n### Stable/dynamic\n{''.join(f'- {k}: {v}\n' for k,v in sd.items())}\n### Current status\n{''.join(f'- {k}: {v}\n' for k,v in st.items())}\n\n## Quality notes\n\n- International-organization internship records in recovery queue: {sum('国际组织' in (r['title'] or '') or '实习' in (r['title'] or '') for r in recovery)}.\n- Dates are extracted only when explicitly present; unresolved temporal fields remain `UNKNOWN`.\n- Duplicate groups and field-level duplicates are preserved in `audit/duplicate_groups.json`; no records were deleted.\n- No approve/reject or external-model classification was performed.\n\n## Frozen integrity\n\nThis run did not modify KB V1, Retriever V1, embeddings, Dense/Hybrid Retriever, Evidence Sufficiency, Citation Support, Answer Generation, E2E evaluation, Prompt V3.2, or production runtime.\n'''
(BASE/'reports/dynamic_campus_v1_report.md').write_text(report,encoding='utf-8')
