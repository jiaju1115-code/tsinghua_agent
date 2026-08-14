from __future__ import annotations
import csv,json
from collections import Counter
from pathlib import Path
from reviewer.loader import read_candidate_index,source_manifest
from utils.paths import DATA_DIR,REVIEWS_DIR,REPORT_DIR

def _rows(path):
    if not path.exists():return []
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def generate_reports(sample_size=20):
    candidates=read_candidate_index();results=_rows(REVIEWS_DIR/"review_results.csv")
    public=[r for r in results if r.get("review_type")=="external_llm"];portal=[r for r in results if r.get("review_type")=="local_portal"]
    origins=Counter(c["dataset_origin"] for c in candidates);actions=Counter(r["recommended_action"] for r in public);cats=Counter(r["category"] for r in results);fresh=Counter(r["freshness"] for r in results);time=Counter(r["time_sensitivity"] for r in results)
    lines=["# 分类统计报告","",f"- Candidate总数：{len(candidates)}",f"- Public：{origins['public']}",f"- Legacy Public：{origins['legacy_public']}",f"- Portal：{origins['portal']}",f"- Public AI测试数量：{len(public)}",f"- Portal本地审核数量：{len(portal)}","","## Public动作",""]
    lines += [f"- {k}：{actions[k]}" for k in ("approve","review","reject")]
    for title,counter,keys in (("类别",cats,("校园办事","校园生活","新生入校","规章制度","校园通知","其他")),("Freshness",fresh,("current","possibly_outdated","outdated","unknown")),("Time sensitivity",time,("low","medium","high"))):
        lines += ["",f"## {title}",""]+[f"- {k}：{counter[k]}" for k in keys]
    (REPORT_DIR/"classification_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    abnormal=[]
    for r in results:
        rel=int(r["relevance_score"]);value=int(r["knowledge_value"]);action=r["recommended_action"]
        reasons=[]
        if rel>=80 and action=="reject":reasons.append("高相关但reject")
        if rel<=30 and action=="approve":reasons.append("低相关但approve")
        if value<=40 and action=="approve":reasons.append("低知识价值但approve")
        if r["content_type"] in {"新闻","人物宣传","科研信息"} and action=="approve":reasons.append("新闻/人物/科研信息但approve")
        if r["authority"]=="high" and value<=20:reasons.append("高权威但低价值")
        if r["freshness"]=="outdated" and action=="approve":reasons.append("过期但approve")
        if r["time_sensitivity"]=="high" and action=="approve":reasons.append("高时效但approve")
        if r["personal_data_risk"]!="none" and action=="approve":reasons.append("敏感风险但approve")
        if r["possible_conflict"].lower()=="true" and action=="approve":reasons.append("疑似冲突但approve")
        if reasons:abnormal.append((r,reasons))
    q=["# 审核质量异常报告","",f"异常条目：{len(abnormal)}",""]
    for r,why in abnormal:q += [f"## {r['id']} {r.get('title','')}","",f"- 规则：{'；'.join(why)}",f"- 动作：{r['recommended_action']}",f"- 来源路径：{r['source_markdown_path']}",""]
    (REPORT_DIR/"quality_report.md").write_text("\n".join(q),encoding="utf-8")
    s=["# 审核抽检报告","","## Public AI样本",""]
    for r in public[:sample_size]:s += [f"### {r['id']} {r.get('title','')}","",f"- 来源：{next((c['source_url'] for c in candidates if c['id']==r['id']),'')}",f"- 类别：{r['category']} / {r['subcategory']}",f"- 相关性/价值：{r['relevance_score']} / {r['knowledge_value']}",f"- 类型：{r['content_type']}",f"- 新鲜度/时效：{r['freshness']} / {r['time_sensitivity']}",f"- 动作：{r['recommended_action']}",f"- 理由：{r['reason']}",""]
    s += ["## Portal本地审核样本",""]
    for r in portal[:10]:s += [f"### {r['id']} {r.get('title','')}","",f"- 类别：{r['category']} / {r['subcategory']}",f"- 动作：{r['recommended_action']}",f"- 理由：{r['reason']}",""]
    (REPORT_DIR/"sampling_report.md").write_text("\n".join(s),encoding="utf-8")
    before_path=DATA_DIR/"source_manifest_before.json";unchanged=None
    if before_path.exists():unchanged=json.loads(before_path.read_text(encoding="utf-8"))==source_manifest()
    (REPORT_DIR/"source_integrity_report.md").write_text(f"# Raw Evidence完整性\n\n- data_first哈希是否完全不变：{unchanged}\n- 文件数：{len(source_manifest())}\n",encoding="utf-8")
