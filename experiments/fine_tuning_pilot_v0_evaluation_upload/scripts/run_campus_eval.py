from __future__ import annotations
import argparse,json,os,re,time
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer, set_seed
from peft import PeftModel
ROOT=Path(__file__).resolve().parents[1]
def jl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def prompt(system, case, replay):
 evidence='\n\n'.join(f"[{x['chunk_id']}] {x['title']}\n{x['text']}" for x in replay['ordered_top5_chunks'])
 return [{'role':'system','content':system},{'role':'user','content':f"Question:\n{case['query']}\n\nFrozen evidence:\n{evidence}\n\nAnswer the question using only the frozen evidence."}]
def assess(output, replay, case):
 ids={x['chunk_id'] for x in replay['ordered_top5_chunks']}; cites=set(re.findall(r'\[([^\]]+)\]',output)); valid=cites & ids
 refusal_expected=('拒答' in case.get('category','') or case.get('slice')=='insufficient_information_refusal')
 refusal=bool(re.search(r'证据不足|无法确定|无法从.*证据|没有足够',output))
 return {'answer_correctness':None,'groundedness_proxy':int(bool(valid)),'required_point_coverage':None,'correct_refusal_proxy':int(refusal==refusal_expected),'partial_answer_correctness':None,'unsupported_claim_proxy':int(bool(cites-valid)),'citation_presence':int(bool(cites)),'citation_compatibility':int(bool(cites) and not bool(cites-valid)),'provisional':True,'reason':'Rule-based proxy only; frozen dataset contains no answer gold labels and no external evaluator was called.'}
def generate(model, tok, messages, cfg):
 encoded=tok.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,return_tensors='pt').to(model.device)
 t=time.perf_counter(); out=model.generate(encoded,max_new_tokens=cfg['max_new_tokens'],do_sample=False,use_cache=True,pad_token_id=tok.eos_token_id);elapsed=(time.perf_counter()-t)*1000
 return tok.decode(out[0][encoded.shape[1]:],skip_special_tokens=True), elapsed, int(out.shape[1]-encoded.shape[1])
def load(path, base, is_adapter):
 model=AutoModelForCausalLM.from_pretrained(base,torch_dtype=torch.bfloat16,local_files_only=True,device_map='auto')
 if is_adapter: model=PeftModel.from_pretrained(model,path,local_files_only=True,is_trainable=False)
 model.eval(); return model
def main():
 p=argparse.ArgumentParser();p.add_argument('--base-model-path',required=True);p.add_argument('--adapter-path',required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
 expected=json.loads((ROOT/'baseline_reference/e2e_heldout_dataset_freeze.json').read_text(encoding='utf-8'))['dataset_sha256']
 import hashlib
 actual=hashlib.sha256((ROOT/'data/campus/e2e_50_cases.jsonl').read_bytes()).hexdigest()
 normalized=hashlib.sha256((ROOT/'data/campus/e2e_50_cases.jsonl').read_text(encoding='utf-8-sig').replace('\r\n','\n').replace('\r','\n').encode()).hexdigest()
 if actual != expected and normalized != expected: raise SystemExit(f'FROZEN_INTEGRITY_FAIL: expected {expected}, raw {actual}, normalized {normalized}; refusing Campus evaluation.')
 if not torch.cuda.is_available(): raise SystemExit('GPU_EVALUATION_PENDING: CUDA GPU required; CPU inference is prohibited.')
 import yaml
 cfg=yaml.safe_load((ROOT/'config/generation_config.yaml').read_text(encoding='utf-8'));set_seed(cfg['seed'])
 cases={x['case_id']:x for x in jl(ROOT/'data/campus/e2e_50_cases.jsonl')}; replays={x['case_id']:x for x in jl(ROOT/'data/campus/retrieval_replay.jsonl')}
 tok=AutoTokenizer.from_pretrained(a.base_model_path,local_files_only=True);tok.padding_side='left';tok.pad_token=tok.pad_token or tok.eos_token
 for label, model_path, adapter in [('base',a.base_model_path,False),('pilot_v0',a.adapter_path,True)]:
  target=ROOT/'results'/label/'campus_per_case.jsonl';target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists() and a.resume: continue
  model=load(model_path,a.base_model_path,adapter)
  with target.open('w',encoding='utf-8') as f:
   for case_id,case in cases.items():
    replay=replays[case_id]; msg=prompt(cfg['system_prompt'],case,replay); raw,latency,tokens=generate(model,tok,msg,cfg); score=assess(raw,replay,case)
    f.write(json.dumps({'case_id':case_id,'task_family':'CAMPUS_QA','category':case.get('category'),'prompt_input_hash':__import__('hashlib').sha256(json.dumps(msg,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'raw_output':raw,'parsed_result':score,'score':score,'evaluator_decision':'PROVISIONAL_RULE_BASED','reason':score['reason'],'evidence_references':replay['chunk_ids'],'latency_ms':latency,'token_count':tokens},ensure_ascii=False)+'\n')
  del model;torch.cuda.empty_cache()
if __name__=='__main__':main()
