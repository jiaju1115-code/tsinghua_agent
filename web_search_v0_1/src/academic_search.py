from __future__ import annotations
import hashlib,json,os,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
from .academic_query_planner import plan_academic
from .direct_answer_guard import possible_direct_answer

ROOT=Path(__file__).resolve().parents[1]
def source_tier(url:str)->str:
    d=urlparse(url).netloc.lower()
    if any(x in d for x in (".edu","arxiv.org","mathworld.wolfram.com","docs.python.org","numpy.org","pytorch.org")): return "TIER_A"
    if any(x in d for x in ("wikipedia.org","libretexts.org")): return "TIER_B"
    return "TIER_C"
class Cache:
    def __init__(self): self.dir=ROOT/"cache"; self.dir.mkdir(exist_ok=True)
    def get(self,p):
        f=self.dir/(hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()+".json")
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    def put(self,p,v):
        f=self.dir/(hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()+".json")
        f.write_text(json.dumps({"retrieved_at":datetime.now(timezone.utc).isoformat(),**v},ensure_ascii=False),encoding="utf-8"); return v
class AcademicRetriever:
    def __init__(self):
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT.parent/"web_search_v0"/".env")
        except ImportError: pass
        self.key=os.getenv("TAVILY_API_KEY","").strip(); self.cache=Cache(); self.new_search=0; self.new_extract=0; self.cache_hits=0
    def client(self):
        if not self.key: raise RuntimeError("TAVILY_API_KEY_NOT_CONFIGURED")
        from tavily import TavilyClient
        return TavilyClient(api_key=self.key)
    def _search(self,query):
        k={"kind":"search","query":query,"max_results":5}; cached=self.cache.get(k)
        if cached: self.cache_hits+=1; return cached["results"],0.0
        t=time.perf_counter(); raw=self.client().search(query=query,max_results=5,search_depth="basic").get("results",[]); elapsed=time.perf_counter()-t; self.new_search+=1
        out=[{"url":x.get("url",""),"title":x.get("title",""),"snippet":x.get("content", ""),"score":x.get("score"),"source_tier":source_tier(x.get("url","")),"raw_source_metadata":x} for x in raw]
        self.cache.put(k,{"results":out}); return out,elapsed
    def _extract(self,urls):
        if not urls:return {},0.0
        t=time.perf_counter(); raw=self.client().extract(urls=urls).get("results",[]); elapsed=time.perf_counter()-t; self.new_extract+=1
        return {x.get("url",""):x.get("raw_content","") for x in raw},elapsed
    def _atom_terms(self, topic, atom_id, description):
        aliases={
          "泊松分布":[["期望","expectation","mean"],["方差","variance"],["二阶","second moment","moment"]],
          "积分方法":[["integral","积分","integration"],["parts","分部积分"],["substitution","换元"]],
          "矩阵与特征理论":[["eigenvalue","特征值"],["eigenvector","特征向量"],["diagonaliz","对角化"]],
          "经典力学":[["newton","牛顿","second law"],["force","受力","free body"],["acceleration","加速度"]],
          "极限与级数":[["convergence","收敛"],["ratio","root","comparison","判别"],["limit","极限"]],
          "约束极值":[["lagrange","拉格朗日"],["first order","一阶"],["constraint","约束"]],
          "计量回归":[["ols","ordinary least squares"],["unbiased","无偏"],["gauss","markov","assumption","假设"]],
          "算法分析":[["complexity","复杂度","asymptotic"],["recurrence","递推"],["master theorem","主定理"]],
          "微观经济学":[["elasticity","弹性"],["marginal","边际"],["derivative","导数"]]
        }
        idx=int(atom_id[1:])-1
        return aliases.get(topic,[])[idx] if topic in aliases and idx<len(aliases[topic]) else re_terms(description)
    def retrieve_academic_context(self,problem):
        began=time.perf_counter(); plan=plan_academic(problem); searches=[]; search_time=extract_time=0.0
        # Stage 1: two knowledge-only queries, never a copied submitted problem.
        for query in plan.knowledge_queries[:2]:
            items,elapsed=self._search(query); search_time+=elapsed
            for x in items: x["retrieval_query"]=query
            searches.extend(items)
        dedup=[]; seen=set()
        for x in sorted(searches,key=lambda s:({"TIER_A":3,"TIER_B":2,"TIER_C":1}[s["source_tier"]],s.get("score") or 0),reverse=True):
            if x["url"] not in seen:seen.add(x["url"]);dedup.append(x)
        selected=dedup[:3]; pages,elapsed=self._extract([x["url"] for x in selected]); extract_time+=elapsed
        evidence=[]; covered=[]
        for source in selected:
            content=pages.get(source["url"],""); source["content_length"]=len(content); source["extraction_status"]="PASS" if len(content)>=120 else "REJECT"
            source["possible_direct_answer_flag"]=possible_direct_answer(problem,source["title"],content,source["url"])
            if source["extraction_status"]=="PASS" and not source["possible_direct_answer_flag"]:
                for atom in plan.knowledge_atoms:
                    terms=self._atom_terms(plan.topic,atom["knowledge_atom_id"],atom["description"])
                    if any(t.lower() in content.lower() or t.lower() in source["snippet"].lower() for t in terms):
                        if atom["knowledge_atom_id"] not in covered: covered.append(atom["knowledge_atom_id"])
                        evidence.append({"evidence_id":f"ev-{hash((source['url'],atom['knowledge_atom_id']))&0xffffffff:08x}","knowledge_atom_ids":[atom["knowledge_atom_id"]],"source_url":source["url"],"source_title":source["title"],"authority_tier":source["source_tier"],"evidence_type":atom["type"],"span_text":content[:500],"retrieval_query":source["retrieval_query"]})
        missing=[a["knowledge_atom_id"] for a in plan.knowledge_atoms if a["knowledge_atom_id"] not in covered]
        # Stage 2 is deliberately bounded: one atom-specific query and top-2 extract.
        stage2=False
        if missing:
            stage2=True; atom=next(a for a in plan.knowledge_atoms if a["knowledge_atom_id"]==missing[0]); gap_query=" ".join(self._atom_terms(plan.topic,atom["knowledge_atom_id"],atom["description"])+["formula definition theorem"])
            gaps,elapsed=self._search(gap_query); search_time+=elapsed
            gap_selected=[s for s in gaps if s["url"] not in seen][:2]; gap_pages,elapsed=self._extract([s["url"] for s in gap_selected]); extract_time+=elapsed
            for source in gap_selected:
                content=gap_pages.get(source["url"],""); source.update({"retrieval_query":gap_query,"content_length":len(content),"extraction_status":"PASS" if len(content)>=120 else "REJECT","possible_direct_answer_flag":possible_direct_answer(problem,source["title"],content,source["url"])})
                selected.append(source)
                if source["extraction_status"]=="PASS" and not source["possible_direct_answer_flag"]:
                    for a in plan.knowledge_atoms:
                        if a["knowledge_atom_id"] in covered: continue
                        if any(t.lower() in (content+source["snippet"]).lower() for t in self._atom_terms(plan.topic,a["knowledge_atom_id"],a["description"])):
                            covered.append(a["knowledge_atom_id"]); evidence.append({"evidence_id":f"ev-{hash((source['url'],a['knowledge_atom_id']))&0xffffffff:08x}","knowledge_atom_ids":[a["knowledge_atom_id"]],"source_url":source["url"],"source_title":source["title"],"authority_tier":source["source_tier"],"evidence_type":a["type"],"span_text":content[:500],"retrieval_query":gap_query})
            missing=[a["knowledge_atom_id"] for a in plan.knowledge_atoms if a["knowledge_atom_id"] not in covered]
        return {"mode":"ACADEMIC_RETRIEVAL","plan":plan.to_dict(),"retrieved_sources":selected,"retrieved_evidence":evidence,"covered_atoms":covered,"missing_atoms":missing,"knowledge_sufficiency":not missing,"direct_answer_risk":any(s["possible_direct_answer_flag"] for s in selected),"stage2_triggered":stage2,"search_latency_seconds":round(search_time,3),"extract_latency_seconds":round(extract_time,3),"total_latency_seconds":round(time.perf_counter()-began,3)}
def re_terms(text): return text.replace("与"," ").replace("或"," ").replace("/"," ").split()
