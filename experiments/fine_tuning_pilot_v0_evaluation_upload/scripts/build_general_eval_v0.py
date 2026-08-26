from __future__ import annotations
import hashlib,json,random
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SEED=20260817
def case(i,f,prompt,gold,rubric,params=None):return {'case_id':f'PGBG0-{i:03d}','family':f,'prompt':prompt,'gold':gold,'scoring_rubric':rubric,'source_provenance':'POST_TRAINING_PROGRAMMATIC_OR_HAND_AUTHORED_DETERMINISTIC_V0','generated_parameters':params or {},'blind_before_inference':True}
def main():
 rng=random.Random(SEED);out=[];i=1
 # 20 machine-checkable instruction tasks
 for n in range(20):
  words=['amber','birch','cobalt','dune','ember'][n%5:]+['falcon','glade','harbor']; pick=words[:3]
  prompt=f"Return exactly a JSON object with keys 'items' and 'count'. items must be this ordered list: {json.dumps(pick)}. count must be {len(pick)}. No other text."
  out.append(case(i,'GENERAL_INSTRUCTION',prompt,{'items':pick,'count':len(pick)},{'type':'json_exact','required_keys':['items','count'],'forbidden_extra_text':True}));i+=1
 # 20 arithmetic reasoning, parameters deliberately high-range and seed recorded
 for _ in range(20):
  a,b,c=[rng.randrange(1009,9001) for z in range(3)]; ans=a*b-c
  out.append(case(i,'MATHEMATICAL_REASONING',f'Compute ({a} × {b}) − {c}. Return only the integer.',str(ans),{'type':'integer_exact'},{'a':a,'b':b,'c':c,'structure':'a*b-c','generator_seed':SEED}));i+=1
 # 12 2x2 linear systems
 for _ in range(12):
  x,y=rng.randrange(-20,21),rng.randrange(-20,21);a,b,d,e=[rng.randrange(2,19) for z in range(4)];c=a*x+b*y;f=d*x+e*y
  out.append(case(i,'LINEAR_ALGEBRA',f'Solve the system {a}x + {b}y = {c}; {d}x + {e}y = {f}. Return JSON exactly as {{"x":integer,"y":integer}}.',{'x':x,'y':y},{'type':'json_exact'},{'matrix':[a,b,d,e],'solution':[x,y],'generator_seed':SEED}));i+=1
 # 10 calculus derivatives
 for _ in range(10):
  a,b,c=[rng.randrange(11,97) for z in range(3)]
  out.append(case(i,'CALCULUS',f'For f(x) = {a}x^3 + {b}x^2 + {c}x, give f\'(x) in the exact form Ax^2+Bx+C with no spaces.',f'{3*a}x^2+{2*b}x+{c}',{'type':'normalized_string_exact'},{'coefficients':[a,b,c],'operation':'derivative','generator_seed':SEED}));i+=1
 # 10 probability
 for _ in range(10):
  good,total=rng.randrange(4,31),rng.randrange(40,101); import math; g=math.gcd(good,total); num,den=good//g,total//g
  out.append(case(i,'PROBABILITY_STATISTICS',f'A bag has {good} red and {total-good} blue balls. One ball is selected uniformly. Return the probability of red as a reduced fraction a/b only.',f'{num}/{den}',{'type':'reduced_fraction_exact'},{'good':good,'total':total,'generator_seed':SEED}));i+=1
 # 15 finite ordering
 for _ in range(15):
  letters=list('ABCDE');rng.shuffle(letters);gold=''.join(letters); clues='; '.join(f'{letters[j]} is before {letters[j+1]}' for j in range(4))
  out.append(case(i,'GENERAL_REASONING',f'Five items A, B, C, D, E must be ordered. Constraints: {clues}. Return the unique order as five letters only.',gold,{'type':'string_exact'},{'order':gold,'generator_seed':SEED}));i+=1
 # 8 pure code tasks; expected implementation exercised by embedded tests
 for n in range(8):
  sample=['"a-b-c"','"aaabb"','"one,two,three"','"level"'][n%4]
  prompt=f"Write only a Python function `solve(s: str) -> str` that returns the reverse of s. It must be pure and use no imports, filesystem, network, or shell. Example input: {sample}."
  out.append(case(i,'BASIC_CODE',prompt,{'function':'solve','tests':[{'input':'abc','output':'cba'},{'input':'清华AI','output':'IA华清'}]}, {'type':'python_unit_tests','forbidden_imports':['os','subprocess','socket','pathlib']}));i+=1
 # 5 stable science facts as constrained choice
 science=[('Which gas has chemical formula O2? Return only the name.','oxygen'),('At sea level, what is the Celsius freezing point of pure water? Return only the integer.','0'),('Which organ pumps blood through the human body? Return only one lowercase English word.','heart'),('What force keeps planets in orbit? Return only one lowercase English word.','gravity'),('What is the SI base unit of electric current? Return only one lowercase English word.','ampere')]
 for p,g in science:out.append(case(i,'BASIC_SCIENCE',p,g,{'type':'normalized_string_exact','source':'stable_basic_science'}));i+=1
 assert len(out)==100
 d=ROOT/'data/general';d.mkdir(parents=True,exist_ok=True); raw='\n'.join(json.dumps(x,ensure_ascii=False,sort_keys=True) for x in out)+'\n';(d/'general_eval_v0.jsonl').write_text(raw,encoding='utf-8')
 scoring={'version':'POST_TRAINING_BLIND_GENERAL_EVAL_V0_SCORING_1','machine_checkable_only':True,'external_llm_used':False,'families':sorted(set(x['family'] for x in out))};(d/'general_eval_v0_scoring.json').write_text(json.dumps(scoring,indent=2),encoding='utf-8')
 manifest={'status':'POST_TRAINING_BLIND_GENERAL_EVAL_V0_FROZEN','creation_timestamp_utc':datetime.now(timezone.utc).isoformat(),'post_training_constructed':True,'blind_before_inference':True,'not_used_for_training_or_validation':True,'not_selected_based_on_model_outputs':True,'generator_version':'1.0','generator_seed':SEED,'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'normalized_sha256':hashlib.sha256(raw.replace('\r\n','\n').encode()).hexdigest(),'case_count':len(out),'family_distribution':Counter(x['family'] for x in out),'scoring_version':scoring['version']};(d/'general_eval_v0_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,default=dict),encoding='utf-8')
if __name__=='__main__':main()
