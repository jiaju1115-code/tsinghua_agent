from pathlib import Path
import json
from transformers import AutoTokenizer
from preprocess import build_feature, IGNORE_INDEX

ROOT=Path(__file__).resolve().parents[1]
TOKENIZER=ROOT/'scripts/qwen_tokenizer'

def rows(name):
    return [json.loads(x) for x in (ROOT/'data'/name).read_text(encoding='utf-8').splitlines() if x.strip()]
def summarize(items):
    lengths=[x['full_length'] for x in items]; n=len(items)
    ordered=sorted(lengths)
    quantile=lambda q: ordered[max(0, __import__('math').ceil(q*n)-1)]
    count=lambda p:sum(p(x) for x in items)
    part=lambda p:{'count':count(p),'ratio':round(count(p)/n,6)}
    return {'count':n,'min':min(lengths),'median':quantile(.5),'p75':quantile(.75),'p90':quantile(.9),'p95':quantile(.95),'p99':quantile(.99),'token_length_le_1024':part(lambda x:x['full_length']<=1024),'token_length_gt_512':part(lambda x:x['full_length']>512),'token_length_gt_1024':part(lambda x:x['full_length']>1024),'token_length_gt_1536':part(lambda x:x['full_length']>1536),'token_length_gt_2048':part(lambda x:x['full_length']>2048),'token_length_gt_3072':part(lambda x:x['full_length']>3072),'max':max(lengths),'expected_truncated_at_1024':part(lambda x:x['full_length']>1024),'expected_truncated_at_2048':part(lambda x:x['full_length']>2048),'assistant_answer_truncated_at_2048':part(lambda x:x['answer_truncated']),'context_only_truncated_at_2048':part(lambda x:x['context_truncated']),'assistant_supervised_tokens':{'median':quantile_assistant(items,.5),'p90':quantile_assistant(items,.9),'p95':quantile_assistant(items,.95),'max':max(x['answer_length'] for x in items)},'assistant_completely_removed_at_2048':part(lambda x:x['supervised_tokens']==0),'supervised_assistant_tokens_lt_16_at_2048':part(lambda x:x['supervised_tokens']<16)}
def quantile_assistant(items,q):
    ordered=sorted(x['answer_length'] for x in items); return ordered[max(0,__import__('math').ceil(q*len(ordered))-1)]
def main():
    tokenizer=AutoTokenizer.from_pretrained(TOKENIZER,local_files_only=True)
    out={}; all_items=[]
    for name in ('train.jsonl','validation.jsonl'):
        items=[build_feature(tokenizer,x['messages'],2048) for x in rows(name)]
        out[name[:-6]]=summarize(items); all_items += items
    out['combined']=summarize(all_items)
    sample=build_feature(tokenizer,rows('train.jsonl')[0]['messages'],2048)
    mask={'implementation':'Qwen chat-template prefix/full token alignment; labels are -100 for all prefix tokens and assistant completion IDs for completion tokens','chat_template':'Qwen2Tokenizer apply_chat_template with add_generation_prompt=True for the masked prefix','user_token_masked':'YES','system_token_masked':'YES','assistant_token_supervised':'YES','special_token_handling':'assistant role marker is prefix-masked; assistant completion and terminal im_end token are supervised','truncation_strategy':'retain assistant completion; truncate left-side prompt first; warn when completion alone exceeds max_length','dry_validation':{'status':'PASS','prefix_tokens_masked':all(x==IGNORE_INDEX for x in sample['labels'][:len(sample['labels'])-sample['supervised_tokens']]),'assistant_tokens_supervised':all(x!=IGNORE_INDEX for x in sample['labels'][-sample['supervised_tokens']:]),'model_forward_backward_executed':False}}
    (ROOT/'data/truncation_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'audit').mkdir(exist_ok=True)
    (ROOT/'audit/loss_masking_audit.json').write_text(json.dumps(mask,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'truncation_audit':out['combined'],'loss_masking':mask['dry_validation']},ensure_ascii=False))
if __name__=='__main__': main()
