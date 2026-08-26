from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
import torch,yaml
from transformers import AutoModelForCausalLM,AutoTokenizer,set_seed
from peft import PeftModel
from general_scorer import score_output
ROOT=Path(__file__).resolve().parents[1]
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def load_base(path):
 kw={'local_files_only':True,'dtype':torch.bfloat16}
 m=AutoModelForCausalLM.from_pretrained(path,**kw).to('cuda');m.eval();return m
def run(label,model,tok,cases,cfg,resume):
 out=ROOT/'results'/label/'general_per_case.jsonl'
 out.parent.mkdir(parents=True,exist_ok=True)
 done={json.loads(x)['case_id'] for x in out.read_text(encoding='utf-8').splitlines() if x.strip()} if resume and out.exists() else set()
 fh=out.open('a' if done else 'w',encoding='utf-8')
 with torch.inference_mode():
  for c in cases:
   if c['case_id'] in done:
    continue
   messages=[{'role':'user','content':c['prompt']}]
   enc=tok.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_tensors='pt',
    return_dict=True,
    return_attention_mask=True
   ).to('cuda')
   input_len=enc['input_ids'].shape[1]
   t=time.perf_counter()
   gen=model.generate(
    input_ids=enc['input_ids'],
    attention_mask=enc['attention_mask'],
    max_new_tokens=cfg['max_new_tokens'],
    do_sample=False,
    pad_token_id=tok.pad_token_id,
    eos_token_id=tok.eos_token_id
   )
   lat=(time.perf_counter()-t)*1000
   raw=tok.decode(gen[0][input_len:],skip_special_tokens=True)
   parsed,score,reason=score_output(raw,c)
   fh.write(json.dumps({
    'case_id':c['case_id'],
    'family':c['family'],
    'prompt_hash':hashlib.sha256(c['prompt'].encode()).hexdigest(),
    'raw_output':raw,
    'parsed_output':parsed,
    'score':score,
    'scorer_type':c['scoring_rubric']['type'],
    'reason':reason,
    'latency_ms':lat,
    'output_token_count':int(gen.shape[1]-input_len)
   },ensure_ascii=False)+'\n')
   fh.flush()
 fh.close()

def main():
 p=argparse.ArgumentParser();p.add_argument('--base-model-path',required=True);p.add_argument('--adapter-path',required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
 if not torch.cuda.is_available():raise SystemExit('GPU_EVALUATION_PENDING: General evaluator requires one CUDA GPU.')
 cfg=yaml.safe_load((ROOT/'config/general_generation_config.yaml').read_text(encoding='utf-8'));set_seed(cfg['seed']);cases=rows(ROOT/'data/general/general_eval_v0_1.jsonl');tok=AutoTokenizer.from_pretrained(a.base_model_path,local_files_only=True);tok.pad_token=tok.pad_token or tok.eos_token;tok.padding_side='left'
 base=load_base(a.base_model_path);run('base',base,tok,cases,cfg,a.resume);del base;torch.cuda.empty_cache()
 pilot_base=load_base(a.base_model_path);pilot=PeftModel.from_pretrained(pilot_base,a.adapter_path,local_files_only=True,is_trainable=False);pilot.eval();run('pilot_v0',pilot,tok,cases,cfg,a.resume)
if __name__=='__main__':main()
