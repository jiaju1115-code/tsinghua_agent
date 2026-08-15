from __future__ import annotations
import csv,json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
claims=json.loads((ROOT/'results/claim_level_audit.json').read_text(encoding='utf-8'))
for c in claims:
 if c['requires_citation'] and not c['supported_by_evidence']:
  t=c['claim_text']
  if c['citation_present']: reason='wrong evidence interpretation'
  elif any(x in t for x in ['一定','所有','总是','完全','普遍','任何']): reason='over-generalization'
  elif re.search(r'\d|[A-Z]{2,}|20\d{2}',t): reason='hallucinated fact / background knowledge injection'
  else: reason='unsupported inference'
  c['unsupported_reason']=reason
 elif c['requires_citation'] and c['supported_by_evidence'] and not c['citation_present']:
  c['unsupported_reason']=None;c['citation_gap_reason']='citation omission only; evidence support detected'
(ROOT/'results/claim_level_audit.json').write_text(json.dumps(claims,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'results/claim_level_audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=sorted({k for x in claims for k in x});w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
 for x in claims:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in x.items()})
reasons=Counter(c['unsupported_reason'] for c in claims if c.get('unsupported_reason'))
(ROOT/'analysis/unsupported_claim_analysis.md').write_text('# Unsupported claims\n\nUnsupported factual/procedural claims identified by deterministic provisional proxy: '+str(sum(reasons.values()))+'.\n\nCause split:\n\n'+'\n'.join(f'- {k}: {v}' for k,v in reasons.most_common())+'\n\nCitation omission alone is not classified as unsupported when saved evidence support is detected. These semantic categories are proxy labels and should be reviewed before optimization.\n',encoding='utf-8')
