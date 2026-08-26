import json, pathlib, statistics
root=pathlib.Path(__file__).resolve().parents[1]; vals=[]
for f in ('train.jsonl','validation.jsonl'):
 for line in (root/'data'/f).read_text(encoding='utf-8').splitlines():
  x=json.loads(line); vals.append(sum(len(m['content']) for m in x['messages']))
print({'rows':len(vals),'unit':'characters (diagnostic only; not tokenizer lengths)','median_chars':statistics.median(vals),'p90_chars':sorted(vals)[int(.9*len(vals))-1],'p95_chars':sorted(vals)[int(.95*len(vals))-1],'max_chars':max(vals)})
