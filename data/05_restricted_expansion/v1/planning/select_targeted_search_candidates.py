from __future__ import annotations

import json
import re
from pathlib import Path


ROOT=Path(r'D:\python_projects\tsinghua_ai')
BASE=ROOT/'data_second'/'restricted_expansion_v1'
SEARCH=BASE/'crawl'/'p0_p1_search_results_corrected.jsonl'
SEEDS=BASE/'planning'/'_seed_rows.json'
OUT=BASE/'planning'/'targeted_fetch_queue.jsonl'

include_patterns={
 '就医报销':[r'生育医疗报销程序',r'基本医疗保险就医、报销须知'],
 '奖学金助学金':[r'特等奖学金评选办法',r'奖学金评选办法',r'助学金.*办法',r'助学金.*管理',r'奖助学金.*办法'],
 '就业手续':[r'就业手续办理通知',r'就业手续办理',r'就业手续.*说明',r'就业政策',r'就业协议',r'档案转递'],
 '体育场地':[r'^2\.1\.7 工会体育场地',r'^2\.2\.2 工会体育场地预约',r'^体育场地预定'],
 '校园网指南':[r'开启校园有线网准入认证',r'校园无线网转入正式运行'],
 '学生事务':[r'学生.*管理规定',r'学生.*管理办法',r'学生事务.*指南',r'学生证.*办理',r'学生.*服务指南'],
 '校园访问':[r'校园参观',r'校园访问.*规定',r'入校.*办理',r'校门.*通行'],
 '住宿办理':[r'住宿管理规定',r'住宿办理指南',r'住宿登记.*规定'],
 '食堂餐饮':[r'餐卡.*办理',r'食堂.*服务指南',r'餐饮.*管理规定'],
 '校园交通班车':[r'班车.*时刻',r'校园交通.*规定',r'校车.*服务'],
}
term_category={'就医报销':'医疗健康','奖学金助学金':'奖助与资助','就业手续':'就业与职业发展','体育场地':'体育与场馆','校园网指南':'网络与信息化','学生事务':'学生事务','校园访问':'校园访问','住宿办理':'住宿服务','食堂餐饮':'餐饮服务','校园交通班车':'交通服务'}
reject=re.compile(r'(招聘|招标|大赛|讲座|论坛|活动|获奖|先进工作者|施工|疫情防控|暑期项目|寒假项目|实习项目|简报|讣告|20(?:0[0-9]|1[0-9]|2[0-3])年|\(20(?:0[0-9]|1[0-9]|2[0-3]))')

rows=[json.loads(x) for x in SEARCH.read_text(encoding='utf-8').splitlines() if x.strip()]
queue=[]; seen=set()
for r in rows:
 term=r.get('search_term'); title=r.get('title',''); url=r.get('url','')
 if not url or r.get('pre_safety_status')!='eligible_general_link' or reject.search(title): continue
 if term=='就业手续' and re.search(r'20(20|21|22|23|24|25)届|寒假|暑假|近期就业手续',title): continue
 if not any(re.search(p,title) for p in include_patterns.get(term,[])): continue
 if url in seen: continue
 seen.add(url)
 queue.append({'queue_source':'portal_search','search_term':term,'discovery_category':term_category[term],'title_hint':title[:260],'url':url,'priority':'P0' if term_category[term] in {'医疗健康','奖助与资助','就业与职业发展','学生事务','住宿服务','餐饮服务','交通服务'} else 'P1','selection_reason':'stable rule/guide/procedure or current core service'})

for s in json.loads(SEEDS.read_text(encoding='utf-8')):
 if s.get('recommended_for_authenticated_fetch') not in {'yes','conditional'}: continue
 url=s['url']
 if url in seen: continue
 seen.add(url)
 queue.append({'queue_source':'prior_login_required_seed','search_term':'就业手续','discovery_category':'就业与职业发展','title_hint':s['title'],'url':url,'priority':'P0','selection_reason':s['value_judgement'],'seed_id':s['seed_id']})

OUT.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in queue),encoding='utf-8')
from collections import Counter
print(json.dumps({'queue':len(queue),'by_category':dict(Counter(x['discovery_category'] for x in queue)),'by_source':dict(Counter(x['queue_source'] for x in queue)),'items':[(x.get('seed_id',''),x['discovery_category'],x['title_hint'][:80]) for x in queue]},ensure_ascii=False))
