from __future__ import annotations

import hashlib,json,re,sys,time
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel,AutoTokenizer

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT.parent;RAG1=DATA/"rag_v1";AE1=DATA/"answer_eval_v1"
CFG=json.loads((ROOT/"config"/"citation_config.json").read_text(encoding="utf-8"));EC=CFG["embedding"];TH=CFG["thresholds"]
FACT_TYPES={"FACTUAL","PROCEDURAL","TEMPORAL","NUMERIC","LOCATION","ENTITY","UNCERTAIN"}
REFUSAL_RE=re.compile(r"根据当前资料无法确认|当前资料无法确认|资料不足|无法确认|无法从.{0,8}资料|证据不足")
TEMP_RE=re.compile(r"(?:\d{4}年|\d{1,2}月\d{0,2}日?|\d{1,2}[：:]\d{2}|第\d+周|春季学期|秋季学期|学期|截止|开放时间|每年|期限|小时|分钟)")
NUM_RE=re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:%|％|年|月|日|周|小时|分钟|人|名|个|元|折|平方米|平米|号|楼|室)?")
PROC_WORDS=["申请","提交","办理","查询","查看","联系","预约","报销","入住","注册","签订","填写","下载","携带","出示","缴纳","审批","盖章","邮寄","咨询","调整","换发","选择","获取","进入"]
SEQ_WORDS=["先","再","然后","之后","前","后","步骤","流程"]
GENERIC_ENTITIES={"学校","学生","资料","规定","办法","流程","服务","平台","系统","中心","项目"}
ALIASES={"清华校医院":["清华大学医院","校医院"],"清华大学医院":["清华校医院","校医院"],"信息门户":["清华大学信息门户"],"学生清华":["“学生清华”","学生清华公众号"]}

def jl(p):return[json.loads(x) for x in p.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
def dumpjl(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("w",encoding="utf-8",newline="\n") as f:
  for x in rows:f.write(json.dumps(x,ensure_ascii=False)+"\n")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def norm(s):return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff%％]","",s).lower()
def bigrams(s):
 s=norm(s);return {s[i:i+2] for i in range(max(0,len(s)-1))}
def lexical(claim,text):
 c=bigrams(claim);e=bigrams(text);return len(c&e)/len(c) if c else 0.0

def spans(answer):
 # Stable non-overlapping spans. Split first by newlines/sentence punctuation,
 # then by semantically independent comma clauses with an explicit predicate.
 bounds=[];start=0
 for m in re.finditer(r"\n+|(?<=[。！？；])",answer):
  end=m.start() if m.group().startswith("\n") else m.end();
  if end>start:bounds.append((start,end))
  start=m.end()
 if start<len(answer):bounds.append((start,len(answer)))
 out=[]
 pred="|".join(PROC_WORDS+["时间","地点","电话","邮箱","开放","截止","由","可","应","需","须"])
 for a,b in bounds:
  text=answer[a:b];local=0
  for m in re.finditer(rf"，(?=(?:并|且|同时)?(?:{pred}))",text):
   if m.start()>local:out.append((a+local,a+m.start()+1))
   local=m.start()+1
  if local<len(text):out.append((a+local,b))
 return out

def clean_span(answer,a,b):
 raw=answer[a:b];left=len(raw)-len(raw.lstrip());right=len(raw.rstrip());a+=left;b=a+right-left if False else a+len(raw.strip())
 text=answer[a:b].strip();lead=re.match(r"^(?:[-*•]\s*|\d+[.、]\s*)",text)
 if lead:a+=lead.end();text=text[lead.end():].strip();a+=len(answer[a:b])-len(answer[a:b].lstrip())
 return a,a+len(text),text

def claim_type(text):
 if REFUSAL_RE.search(text):return "REFUSAL" if norm(text) in {norm("根据当前资料无法确认。"),norm("当前资料无法确认。")} else "UNCERTAIN"
 if re.search(r"可能|建议|应咨询|需咨询|信息不详|详见|可至官网|应查看",text):return "UNCERTAIN"
 if len(norm(text))<3 or (text.endswith("：") and not any(x in text for x in PROC_WORDS)):return "NON_FACTUAL"
 if TEMP_RE.search(text):return "TEMPORAL"
 if NUM_RE.search(text):return "NUMERIC"
 if re.search(r"地址|地点|校区|路|楼|室|馆|园|宿舍",text):return "LOCATION"
 if any(x in text for x in PROC_WORDS):return "PROCEDURAL"
 if re.search(r"《[^》]+》|[A-Za-z\u4e00-\u9fff]{2,16}(?:大学|学院|学系|中心|委员会|图书馆|医院|体育馆|食堂|平台|系统|门户|公众号|小程序)",text):return "ENTITY"
 return "FACTUAL"

def segment(row):
 answer=row["generated_answer"];claims=[]
 for a,b in spans(answer):
  a,b,t=clean_span(answer,a,b)
  if not t:continue
  claims.append({"question_id":row["question_id"],"claim_id":f"{row['question_id']}-C{len(claims)+1:03d}","claim_text":t,"claim_type":claim_type(t),"source_answer_span":{"start":a,"end":b,"text":answer[a:b]},"segmentation_method":"DETERMINISTIC_RULE_V1"})
 return claims

def entities(text):
 vals=set(re.findall(r"《([^》]{2,40})》",text))
 vals|=set(re.findall(r"[A-Za-z\u4e00-\u9fff]{2,16}(?:大学|学院|学系|中心|委员会|图书馆|医院|体育馆|食堂|平台|系统|门户|公众号|小程序)",text))
 vals|=set(re.findall(r"[A-Z]{2,}(?:\s+[A-Z]{2,})*",text))
 return sorted(x for x in vals if x not in GENERIC_ENTITIES and len(x)<=24)
def entity_present(ent,text):return ent in text or any(a in text for a in ALIASES.get(ent,[]))
def rule_eval(claim,evidence,semantic):
 ct=claim["claim_text"];et=evidence["text"];title=evidence.get("title","");full=title+"\n"+et
 nums=NUM_RE.findall(ct);temps=TEMP_RE.findall(ct);ents=entities(ct);verbs=[x for x in PROC_WORDS if x in ct];seq=[x for x in SEQ_WORDS if x in ct]
 num_ok=all(x in full for x in nums) if nums else True;temp_ok=all(x in full for x in temps) if temps else True;ent_ok=all(entity_present(x,full) for x in ents) if ents else True
 verb_alias={"查询":["查询","查看"],"查看":["查询","查看"],"办理":["办理","申请"],"申请":["申请","办理"],"获取":["获取","获得"],"进入":["进入","入馆"]}
 proc_ok=all(any(v in full for v in verb_alias.get(x,[x])) for x in verbs) if verbs else True;seq_ok=all(x in full for x in seq) if seq else True
 lex=lexical(ct,full);exact=norm(ct) in norm(full) and len(norm(ct))>=4
 hard=num_ok and temp_ok and ent_ok and proc_ok and seq_ok
 comp=0.72*semantic+0.28*lex
 return {"semantic_score":semantic,"lexical_claim_coverage":lex,"exact_normalized_match":exact,"numeric_values":nums,"numeric_match":num_ok,"temporal_tokens":temps,"temporal_match":temp_ok,"entities":ents,"entity_match":ent_ok,"procedural_verbs":verbs,"procedural_match":proc_ok,"sequence_tokens":seq,"sequence_match":seq_ok,"hard_rules_pass":hard,"composite_support_score":comp,"rule_flags":[n for n,v in (("NUMERIC_MISMATCH",num_ok),("TEMPORAL_MISMATCH",temp_ok),("ENTITY_MISMATCH",ent_ok),("PROCEDURAL_MISMATCH",proc_ok),("SEQUENCE_MISMATCH",seq_ok)) if not v]}

def conflict_check(claim,candidates):
 nums=NUM_RE.findall(claim["claim_text"]);ents=entities(claim["claim_text"])
 # A generic university name plus unrelated numbers elsewhere in long chunks is
 # not evidence of a contradiction.  Conflict detection is deliberately narrow:
 # it requires a claim-specific, non-generic entity in every conflicting source.
 generic={"清华大学","清华","学校","校园"}
 ents=[e for e in ents if e not in generic and len(e)>=4]
 if not nums or not ents:return False,[]
 vals=[]
 for c in candidates:
  if c["semantic_score"]<TH["main_partial"]:continue
  text=c["evidence"]["title"]+"\n"+c["evidence"]["text"]
  if all(entity_present(e,text) for e in ents):
   other=[x for x in NUM_RE.findall(text) if x not in nums]
   if other:vals.append({"chunk_id":c["chunk_id"],"other_numeric_values":other[:10]})
 return (len(vals)>=2),vals

def classify(claim,cands,qid):
 if claim["claim_type"]=="NON_FACTUAL":return "NON_FACTUAL",[],{"reason":"non-factual framing"}
 if claim["claim_type"]=="REFUSAL":
  appropriate=qid in set(CFG["rules"]["known_source_quality_failure_question_ids"]) or max(x["semantic_score"] for x in cands)<TH["main_partial"]
  return "REFUSAL",[],{"reason":"bare evidence-insufficiency refusal","refusal_appropriate_proxy":appropriate}
 conflict,details=conflict_check(claim,cands)
 if conflict:return "CONFLICTING_EVIDENCE",[],{"reason":"high-similarity evidence contains divergent critical numeric values","conflict_details":details}
 top=cands[0];r=top["rules"]
 if top["semantic_score"]>=TH["main_supported"] and r["hard_rules_pass"] and (r["lexical_claim_coverage"]>=0.12 or r["exact_normalized_match"]):return "SUPPORTED",[top],{"reason":"semantic threshold and all deterministic rules pass"}
 if top["semantic_score"]>=TH["main_partial"] and r["numeric_match"] and r["temporal_match"] and r["entity_match"] and r["procedural_match"] and r["lexical_claim_coverage"]>=0.05:return "PARTIALLY_SUPPORTED",[top],{"reason":"partial semantic/lexical support with critical hard rules passing"}
 # Multi-chunk partial: combine the two strongest chunks, never upgrade to full support.
 if len(cands)>=2 and max(cands[0]["semantic_score"],cands[1]["semantic_score"])>=TH["main_partial"]:
  combo={"title":"","text":cands[0]["evidence"]["title"]+"\n"+cands[0]["evidence"]["text"]+"\n"+cands[1]["evidence"]["title"]+"\n"+cands[1]["evidence"]["text"]}
  rr=rule_eval(claim,combo,max(cands[0]["semantic_score"],cands[1]["semantic_score"]))
  if rr["hard_rules_pass"] and rr["lexical_claim_coverage"]>=0.08:return "PARTIALLY_SUPPORTED",cands[:2],{"reason":"requires two chunks for combined partial support","multi_chunk":True}
 return "UNSUPPORTED",[],{"reason":"semantic/lexical threshold or deterministic fact rules failed","top_rule_flags":r["rule_flags"]}

def render(row,claim_rows,assignments):
 amap=defaultdict(list)
 for a in assignments:amap[a["claim_id"]].append(a)
 refs=[];refnum={};insertions=[]
 for c in claim_rows:
  aa=amap.get(c["claim_id"],[])
  if not aa:continue
  nums=[]
  for x in aa:
   cid=x["chunk_id"]
   if cid not in refnum:refnum[cid]=len(refnum)+1;refs.append({"reference_number":refnum[cid],"chunk_id":cid,"document_id":x["document_id"],"title":x["title"],"url":x["source_url"]})
   nums.append(refnum[cid])
  marker="".join(f"[{n}]" for n in sorted(set(nums)));insertions.append((c["source_answer_span"]["end"],marker))
 cited=row["generated_answer"]
 for pos,m in sorted(insertions,reverse=True):cited=cited[:pos]+m+cited[pos:]
 if refs:cited += "\n\n参考资料：\n"+"\n".join(f"[{x['reference_number']}] {x['title']} — {x['url'] or x['document_id']}" for x in refs)
 return cited,refs,insertions

def main():
 a=jl(AE1/"results"/"generation_a.jsonl");v0=jl(DATA/"answer_eval_v0"/"results"/"answer_generation_results.jsonl");ev_a={x["question_id"]:x for x in jl(AE1/"results"/"evaluation_a.jsonl")}
 if len(a)!=38 or any(x["generated_answer"]!=y["generated_answer"] for x,y in zip(a,v0)):raise SystemExit("INPUT_INVARIANCE_FAILURE")
 claims=[]
 for row in a:claims.extend(segment(row))
 dumpjl(ROOT/"results"/"claims.jsonl",claims)
 model_path=RAG1/"indexes"/"dense"/"model";tok=AutoTokenizer.from_pretrained(model_path,local_files_only=True);model=AutoModel.from_pretrained(model_path,local_files_only=True).eval()
 texts=[EC["query_instruction"]+x["claim_text"] for x in claims];vec=[];started=time.perf_counter()
 with torch.inference_mode():
  for s in range(0,len(texts),EC["batch_size"]):
   t=tok(texts[s:s+EC["batch_size"]],padding=True,truncation=True,max_length=EC["max_length"],return_tensors="pt");v=model(**t).last_hidden_state[:,0];v=torch.nn.functional.normalize(v,p=2,dim=1);vec.append(v.cpu().numpy().astype(np.float32))
 embeddings=np.concatenate(vec);emb_path=ROOT/"results"/"claim_embeddings.npy";np.save(emb_path,embeddings,allow_pickle=False)
 dumpjl(ROOT/"results"/"claim_embedding_rows.jsonl",[{"embedding_row":i,"question_id":x["question_id"],"claim_id":x["claim_id"],"dimension":embeddings.shape[1]} for i,x in enumerate(claims)])
 doc=np.load(RAG1/"indexes"/"dense"/"document_embeddings.npy",mmap_mode="r");mapping={x["chunk_id"]:x for x in jl(RAG1/"indexes"/"dense"/"row_mapping.jsonl")};byqid={x["question_id"]:x for x in a}
 mappings=[];assignments=[];claim_out=[];sensitivity={str(t):Counter() for t in TH["sensitivity"]};high_sem_hard_fail=[]
 for i,c in enumerate(claims):
  row=byqid[c["question_id"]];cands=[]
  for rank,(cid,base_score,evidence) in enumerate(zip(row["retrieved_chunk_ids"],row["retrieval_scores"],row["retrieved_context"]),1):
   score=float(doc[mapping[cid]["embedding_row"]]@embeddings[i]);rules=rule_eval(c,evidence,score);cands.append({"chunk_id":cid,"document_id":evidence["source_id"],"source_url":evidence.get("url"),"title":evidence["title"],"original_dense_rank":rank,"original_query_score":base_score,"semantic_score":score,"rules":rules,"evidence":evidence})
  cands.sort(key=lambda x:(-x["semantic_score"],x["original_dense_rank"]));label,chosen,why=classify(c,cands,c["question_id"])
  if c["claim_type"] in FACT_TYPES:
   for t in TH["sensitivity"]:
    top=cands[0];sens="SUPPORTED" if top["semantic_score"]>=t and top["rules"]["hard_rules_pass"] and (top["rules"]["lexical_claim_coverage"]>=0.12 or top["rules"]["exact_normalized_match"]) else "UNSUPPORTED";sensitivity[str(t)][sens]+=1
  if cands[0]["semantic_score"]>=TH["main_supported"] and not cands[0]["rules"]["hard_rules_pass"]:high_sem_hard_fail.append({"question_id":c["question_id"],"claim_id":c["claim_id"],"claim_text":c["claim_text"],"semantic_score":cands[0]["semantic_score"],"rule_flags":cands[0]["rules"]["rule_flags"],"chunk_id":cands[0]["chunk_id"]})
  mapping_row={"question_id":c["question_id"],"claim_id":c["claim_id"],"claim_type":c["claim_type"],"claim_embedding":{"row":i,"dimension":int(embeddings.shape[1]),"file":"results/claim_embeddings.npy"},"candidate_chunk_ids":[x["chunk_id"] for x in cands],"candidate_scores":[x["semantic_score"] for x in cands],"top_candidate_chunk":cands[0]["chunk_id"],"top_candidate_score":cands[0]["semantic_score"],"candidates":[{"chunk_id":x["chunk_id"],"document_id":x["document_id"],"source_url":x["source_url"],"semantic_score":x["semantic_score"],"original_dense_rank":x["original_dense_rank"],**x["rules"]} for x in cands],"final_support_label":label,"decision":why};mappings.append(mapping_row)
  claim_out.append({**c,"semantic_score":cands[0]["semantic_score"],**cands[0]["rules"],"final_support_label":label,"decision":why})
  for j,x in enumerate(chosen):assignments.append({"question_id":c["question_id"],"claim_id":c["claim_id"],"chunk_id":x["chunk_id"],"document_id":x["document_id"],"source_url":x["source_url"],"title":x["title"],"support_score":x["rules"]["composite_support_score"],"semantic_score":x["semantic_score"],"support_label":label,"citation_role":"primary" if j==0 else "supporting","deterministic_rules_pass":x["rules"]["hard_rules_pass"]})
 dumpjl(ROOT/"results"/"claim_evidence_mapping.jsonl",mappings);dumpjl(ROOT/"results"/"citation_assignments.jsonl",assignments);dumpjl(ROOT/"results"/"claims_classified.jsonl",claim_out)
 cby=defaultdict(list);aby=defaultdict(list)
 for c in claim_out:cby[c["question_id"]].append(c)
 for x in assignments:aby[x["question_id"]].append(x)
 per=[]
 for row in a:
  cs=cby[row["question_id"]];aa=aby[row["question_id"]];cited,refs,ins=render(row,cs,aa);counts=Counter(x["final_support_label"] for x in cs);factual=[x for x in cs if x["claim_type"] in FACT_TYPES];covered=[x for x in factual if x["final_support_label"] in {"SUPPORTED","PARTIALLY_SUPPORTED"}];unsupported=[x for x in factual if x["final_support_label"]=="UNSUPPORTED"]
  mapped_answer=bool(factual) and all(x["final_support_label"] in {"SUPPORTED","PARTIALLY_SUPPORTED"} for x in factual)
  appropriate_refusal=not factual and any(x["final_support_label"]=="REFUSAL" for x in cs) and all(x["final_support_label"] in {"REFUSAL","NON_FACTUAL"} for x in cs)
  new_ok=mapped_answer or appropriate_refusal
  body=cited.split("\n\n参考资料：",1)[0];body_clean=re.sub(r"\[\d+\]","",body);preserved=body_clean==row["generated_answer"]
  per.append({"question_id":row["question_id"],"question":row["question"],"eval_status":row["eval_status"],"category":row["category"],"original_answer":row["generated_answer"],"cited_answer":cited,"citation_references":refs,"citation_insertions":ins,"original_citation_status":"COMPLIANT" if ev_a[row["question_id"]]["auto_evaluation"]["citation_compliance"] else "NONCOMPLIANT","new_citation_status":"COMPLIANT" if new_ok else "NONCOMPLIANT","claim_count":len(cs),"factual_claim_count":len(factual),"supported_claim_count":counts["SUPPORTED"],"partial_claim_count":counts["PARTIALLY_SUPPORTED"],"unsupported_claim_count":counts["UNSUPPORTED"],"conflicting_claim_count":counts["CONFLICTING_EVIDENCE"],"refusal_claim_count":counts["REFUSAL"],"citation_count":len(aa),"citation_coverage":len(covered)/len(factual) if factual else 1.0,"citation_precision_proxy":sum(bool(x["deterministic_rules_pass"]) for x in aa)/len(aa) if aa else None,"preservation_status":"PRESERVED" if preserved else "FAILED","source_quality_failure":row["question_id"] in set(CFG["rules"]["known_source_quality_failure_question_ids"]),"unsupported_claim_ids":[x["claim_id"] for x in unsupported]})
 dumpjl(ROOT/"results"/"per_question_results.jsonl",per)
 fact=[x for x in claim_out if x["claim_type"] in FACT_TYPES];cnt=Counter(x["final_support_label"] for x in claim_out);covered=sum(x["final_support_label"] in {"SUPPORTED","PARTIALLY_SUPPORTED"} for x in fact);assigned=len(assignments);valid=sum(bool(x["deterministic_rules_pass"]) for x in assignments)
 metrics={"status":"PASS","scope":"PROVISIONAL_AUTO_EVAL","questions_completed":len(per),"claim_total":len(claim_out),"factual_claim_total":len(fact),"support_distribution":dict(cnt),"claim_level_citation_coverage":covered/len(fact) if fact else None,"citation_assignments":assigned,"citation_precision_proxy":valid/assigned if assigned else None,"unsupported_claim_rate":cnt["UNSUPPORTED"]/len(fact) if fact else None,"partial_support_rate":cnt["PARTIALLY_SUPPORTED"]/len(fact) if fact else None,"conflict_rate":cnt["CONFLICTING_EVIDENCE"]/len(fact) if fact else None,"answer_level_citation_compliance":{"a_baseline":sum(x["original_citation_status"]=="COMPLIANT" for x in per)/len(per),"citation_pipeline_v1":sum(x["new_citation_status"]=="COMPLIANT" for x in per)/len(per)},"answer_preservation_rate":sum(x["preservation_status"]=="PRESERVED" for x in per)/len(per),"wrong_citation_assignments_proxy":assigned-valid,"high_semantic_hard_rule_failures":len(high_sem_hard_fail),"embedding":{"file":"results/claim_embeddings.npy","sha256":sha(emb_path),"rows":len(claims),"dimension":int(embeddings.shape[1]),"encoding_seconds":time.perf_counter()-started,"model_name":EC["model_name"],"revision":EC["revision"]},"human_validated_citation_correctness":None}
 (ROOT/"results"/"citation_metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
 sensitivity_out={}
 for t,v in sensitivity.items():
  total=sum(v.values());sensitivity_out[t]={**dict(v),"eligible_factual_claims":total,"coverage_proxy":v["SUPPORTED"]/total if total else None}
 threshold={"selection_rule":TH["selection_rule"],"main_supported":TH["main_supported"],"main_partial":TH["main_partial"],"sensitivity":sensitivity_out,"high_semantic_but_hard_rules_fail":high_sem_hard_fail}
 (ROOT/"results"/"threshold_analysis.json").write_text(json.dumps(threshold,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(metrics,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
