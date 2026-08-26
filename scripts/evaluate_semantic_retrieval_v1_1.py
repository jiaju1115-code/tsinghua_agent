"""Offline 60-query retrieval evaluation; no network, generation, or KB writes."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from src.semantic_retrieval_v1_1 import CandidateRetrieverV1_1

# Source-family labels were manually assigned from frozen source metadata.  A null
# family means KB_GAP and is excluded from retrieval recall, never counted as miss.
GROUPS=[
 ("visitor_entry",["我的爸妈怎么预约入校","我爸妈想进学校看看怎么弄","父母咋预约进学校","校外家属怎么预约进校","家长怎么进清华"],None),
 ("room_booking",["怎么预约C楼的教室","C楼怎么订","怎么约个教室","怎么借C楼的教室","C楼场地申请在哪"],None),
 ("dining",["给我推荐一个便宜又好吃的食堂","有没有便宜点的食堂","学校里吃饭去哪","食堂有什么推荐","餐厅便宜吗"],["KBV1-PUB-PUBV2C-0303","KBV1-PUB-PUBV2C-0304","KBV1-PUB-PUBV2C-0305","KBV1-PUB-PUBV2C-0306"]),
 ("library_hours",["图书馆几点关","图书馆啥时候闭馆","晚上能去图书馆到几点","图书馆开放时间","图书馆夜里关门吗"],None),
 ("scholarship",["奖学金咋搞","奖学金怎么申请","本科奖学金在哪申请","学生奖助什么时候弄","清华本科生奖学金什么时候申请"],["KBV1-PUB-PUBV2C-0074","KBV1-PUB-PUBV2C-0075","KBV1-PUB-PUBV2C-0079","KBV1-PUB-PUBV2C-0091"]),
 ("accommodation",["宿舍怎么申请","住宿安排在哪看","学生公寓怎么住","宿舍管理规定","研究生住宿怎么弄"],["KBV1-PUB-PUBV2C-0010","KBV1-PUB-PUBV2C-0047"]),
 ("campus_card",["校园卡怎么办","一卡通丢了怎么办","校园卡充值在哪","学生卡能干嘛","办卡流程"],None),
 ("network",["校园网怎么连","wifi连不上怎么办","学校网络服务在哪","宿舍网怎么用","网络账号怎么开"],None),
 ("medical",["校医院怎么去","学校看病去哪","医疗报销怎么弄","校内医院电话","学生就诊流程"],["KBV1-PUB-PUBV2C-0262"]),
 ("transport",["校车怎么坐","校园交通怎么走","班车时间","校内出行","学校交通服务"],None),
 ("student_affairs",["学生请假怎么办","处分规定在哪","助学贷款怎么申请","学籍异动流程","学生事务咨询"],["KBV1-PUB-PUBV2C-0075","KBV1-PUB-PUBV2C-0076","KBV1-PUB-PUBV2C-0079"]),
 ("research_resources",["实验室怎么申请","科研资源在哪找","仪器怎么预约","研究生实验室管理","校内设备使用"],["KBV1-PUB-PUBV2C-0259","KBV1-PUB-PUBV2C-0293"]),
]
OLD_MARKERS=("清华","校园","院系","宿舍","校历","图书馆","教务")
OLD_AMBIG=("奖学金","截止","报到","申请","选课")
def old_route(q): return not (any(x in q for x in OLD_AMBIG) and not any(x in q for x in OLD_MARKERS)) and any(x in q for x in OLD_MARKERS)
def rank(rows, targets):
 for n,(idx,_s) in enumerate(rows,1):
  if targets and idx in targets:return n
 return None
def metric(ranks,k):
 vals=[r for r in ranks if r]; return round(sum(r<=k for r in vals)/len(ranks),4) if ranks else None
def main():
 c=CandidateRetrieverV1_1(); cases=[]
 for category,queries,family in GROUPS:
  for query in queries:
   understand=c.trace(query)["query_understanding"]
   targets={i for i,x in enumerate(c.chunks) if family and x["canonical_source_id"] in family}
   v1=c._dense(query,20) if old_route(query) else []
   normalized=c._dense(understand["normalized_query"],20) if understand["route"]=="CAMPUS_RAG" else []
   hybrid=c.trace(query)["hybrid_top20"] if understand["route"]=="CAMPUS_RAG" else []
   hybrid_ranks=[next((i for i,x in enumerate(c.chunks) if x["chunk_id"]==r["chunk_id"]),-1) for r in hybrid]
   cases.append({"query":query,"category":category,"label":"RELEVANT_IN_KB" if family else "KB_GAP","relevant_source_ids":family or [],"frozen_v1_route":old_route(query),"candidate_route":understand["route"],"v1_rank":rank(v1,targets),"normalized_dense_rank":rank(normalized,targets),"hybrid_rank":rank([(i,0) for i in hybrid_ranks],targets)})
 relevant=[x for x in cases if x["label"]=="RELEVANT_IN_KB"]
 def series(key): return [x[key] for x in relevant]
 def row(key,bypass):
  rs=series(key); return {"Recall@5":metric(rs,5),"Recall@10":metric(rs,10),"Recall@20":metric(rs,20),"MRR":round(sum(1/r for r in rs if r)/len(rs),4),"Campus_RAG_bypass_rate":round(bypass/len(cases),4)}
 report={"evaluation_version":"SEMANTIC_RETRIEVAL_V1_1_OFFLINE_60","case_count":len(cases),"kb_gap_count":len(cases)-len(relevant),"metrics":{"Frozen Dense V1":row("v1_rank",sum(not x["frozen_v1_route"] for x in cases)),"Normalized Dense":row("normalized_dense_rank",sum(x["candidate_route"]!="CAMPUS_RAG" for x in cases)),"Hybrid Dense+BM25+RRF":row("hybrid_rank",sum(x["candidate_route"]!="CAMPUS_RAG" for x in cases)),"Hybrid+Reranker":"NOT_RUN_NO_LOCAL_RERANKER"},"cases":cases,"limitations":["Candidate remains diagnostic-only and is not integrated into frozen Evidence/Citation chain.","Reranker was not found locally and was not downloaded."]}
 (ROOT/"reports"/"semantic_retrieval_v1_1_evaluation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"status":"WRITTEN","cases":len(cases),"metrics":report["metrics"]},ensure_ascii=False));
if __name__=="__main__":main()
