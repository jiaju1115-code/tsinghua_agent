from pathlib import Path
import json, hashlib
from transformers import AutoTokenizer
from audit_truncation_and_masking import rows, summarize
from preprocess import build_feature

ROOT=Path(__file__).resolve().parents[1]
def old_char_statistics():
    vals=[]
    for name in ('train.jsonl','validation.jsonl'):
        for x in rows(name): vals.append(sum(len(m['content']) for m in x['messages']))
    vals.sort(); n=len(vals); q=lambda p:vals[__import__('math').ceil(p*n)-1]
    return {'implementation':'scripts/inspect_dataset.py','unit':'characters, not tokens','tokenizer':None,'tokenizer_revision':None,'apply_chat_template':False,'includes_user':True,'includes_assistant':True,'includes_system':False,'includes_special_tokens':False,'truncation_before_statistics':True,'population':'converted train.jsonl + validation.jsonl (841)','reproduced_statistics':{'median':q(.5),'p90':q(.9),'p95':q(.95),'max':max(vals)}}
def main():
    tok=AutoTokenizer.from_pretrained(ROOT/'scripts/qwen_tokenizer',local_files_only=True)
    grouped={}; all_items=[]
    for name in ('train.jsonl','validation.jsonl'):
        items=[build_feature(tok,x['messages'],2048) for x in rows(name)]
        grouped[name[:-6]]=summarize(items); all_items.extend(items)
    authoritative=summarize(all_items)
    files=['tokenizer.json','tokenizer_config.json']
    tokenizer_info={'tokenizer':'Qwen/Qwen2.5-1.5B-Instruct','tokenizer_revision':'989aa7980e4cf806f80c7fef2b1adb7bc71aa306','local_assets':{x:hashlib.sha256((ROOT/'scripts/qwen_tokenizer'/x).read_bytes()).hexdigest() for x in files},'apply_chat_template':True,'chat_template':'Qwen2Tokenizer.apply_chat_template; default system message + user + assistant + im_start/im_end special tokens','includes_user':True,'includes_assistant':True,'includes_system':True,'includes_special_tokens':True,'truncation_before_statistics':True,'population':'all 841 converted train/validation rows'}
    out={'root_cause':'Historical values were character counts produced by scripts/inspect_dataset.py and were incorrectly described as token lengths. The latest truncation audit uses actual Qwen tokenizer IDs over the complete chat-template sequence; the two metrics are not comparable.','old_statistics_explanation':old_char_statistics(),'new_statistics_explanation':tokenizer_info,'authoritative_statistics':{'all_841':authoritative,'train_757':grouped['train'],'validation_84':grouped['validation']},'max_seq_length_2048_recommended':True,'existing_upload_package_files_need_correction':['README.md historical character statistics wording','config/experiment_manifest.json audit provenance','data/truncation_audit.json expanded authoritative distribution','integrity/SHA256SUMS.txt','ZIP and ZIP hash']}
    (ROOT/'audit').mkdir(exist_ok=True); (ROOT/'audit/token_length_discrepancy_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'root_cause':out['root_cause'],'authoritative':authoritative},ensure_ascii=False))
if __name__=='__main__': main()
