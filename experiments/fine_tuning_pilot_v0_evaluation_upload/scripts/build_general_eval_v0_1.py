from __future__ import annotations
import hashlib,json,random
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SEED=2026081701
def add(rows,f,p,g,r,params=None):rows.append({'case_id':f'PGBG01-{len(rows)+1:03d}','family':f,'prompt':p,'gold':g,'scoring_rubric':r,'generated_parameters':params or {},'source_provenance':'POST_TRAINING_BLIND_GENERAL_EVAL_V0_1','blind_before_inference':True})
def main():
 r=random.Random(SEED); rows=[]
 instruction=[
 ('Return only {"n":3,"items":["a","b","c"]}.',{'n':3,'items':['a','b','c']}),('Return only the JSON array [4,3,2,1].',[4,3,2,1]),('Return only {"first":"Ada","last":"Lovelace"}.',{'first':'Ada','last':'Lovelace'}),('Return only {"sorted":[1,2,5,9]}.',{'sorted':[1,2,5,9]}),('Return only {"upper":"MINT"}.',{'upper':'MINT'}),('Return only {"unique":["x","y","z"]}.',{'unique':['x','y','z']}),('Return only {"renamed":{"new":7}}.',{'renamed':{'new':7}}),('Return only {"count":4,"word":"pear"}.',{'count':4,'word':'pear'}),('Return only {"pairs":[["a",1],["b",2]]}.',{'pairs':[['a',1],['b',2]]}),('Return only {"truth":true,"falsehood":false}.',{'truth':True,'falsehood':False}),('Return only {"csv":"a,b,c"}.',{'csv':'a,b,c'}),('Return only {"lines":2,"text":"up\\ndown"}.',{'lines':2,'text':'up\ndown'}),('Return only {"min":-2,"max":8}.',{'min':-2,'max':8}),('Return only {"mapping":{"red":"R","blue":"B"}}.',{'mapping':{'red':'R','blue':'B'}}),('Return only {"letters":["A","C","E"]}.',{'letters':['A','C','E']}),('Return only {"even":[2,4,6]}.',{'even':[2,4,6]}),('Return only {"reversed":"desserts"}.',{'reversed':'desserts'}),('Return only {"tokens":["north","east"]}.',{'tokens':['north','east']}),('Return only {"total":15,"valid":true}.',{'total':15,'valid':True}),('Return only {"format":"YYYY-MM-DD","example":"2030-07-04"}.',{'format':'YYYY-MM-DD','example':'2030-07-04'})]
 for p,g in instruction:add(rows,'GENERAL_INSTRUCTION',p,g,{'type':'json_exact','forbidden_extra_text':True})
 for _ in range(20):
  a,b,c=[r.randrange(1009,9001) for z in range(3)];add(rows,'MATHEMATICAL_REASONING',f'Compute ({a} × {b}) − {c}. Return only the integer.',str(a*b-c),{'type':'integer_exact'},{'a':a,'b':b,'c':c,'structure':'a*b-c','generator_seed':SEED})
 for _ in range(12):
  while True:
   a,b,d,e=[r.randrange(2,31) for z in range(4)]
   if a*e-b*d:break
  x,y=r.randrange(-20,21),r.randrange(-20,21);c,f=a*x+b*y,d*x+e*y;add(rows,'LINEAR_ALGEBRA',f'Solve {a}x + {b}y = {c}; {d}x + {e}y = {f}. Return only JSON {{"x":integer,"y":integer}}.',{'x':x,'y':y},{'type':'json_exact','forbidden_extra_text':True},{'matrix':[a,b,d,e],'determinant':a*e-b*d,'solution':[x,y],'generator_seed':SEED})
 for _ in range(10):
  a,b,c=[r.randrange(11,97) for z in range(3)];add(rows,'CALCULUS',f'Differentiate f(x)={a}x^3+{b}x^2+{c}x. Return Ax^2+Bx+C without spaces.',f'{3*a}x^2+{2*b}x+{c}',{'type':'normalized_string_exact'},{'coefficients':[a,b,c],'generator_seed':SEED})
 import math
 for _ in range(10):
  good,total=r.randrange(4,31),r.randrange(40,101);g=math.gcd(good,total);add(rows,'PROBABILITY_STATISTICS',f'A bag has {good} red and {total-good} blue balls. Return P(red) as a reduced a/b fraction only.',f'{good//g}/{total//g}',{'type':'reduced_fraction_exact'},{'good':good,'total':total,'generator_seed':SEED})
 perms=list(__import__('itertools').permutations('ABCDE'));r.shuffle(perms)
 for perm in perms[:15]:
  order=''.join(perm); clues='; '.join(f'{order[j]} is immediately before {order[j+1]}' for j in range(4));add(rows,'GENERAL_REASONING',f'Order A,B,C,D,E. Constraints: {clues}. Return the unique five-letter order only.',order,{'type':'string_exact'},{'order':order,'generator_seed':SEED})
 code=[('reverse', 'Write only Python code defining solve(s) that returns s reversed.', [{'input':['abc'],'output':'cba'}]),('vowels','Write only Python code defining solve(s) that counts a,e,i,o,u case-insensitively.',[{'input':['Aeon'],'output':3}]),('dedupe','Write only Python code defining solve(xs) that removes duplicates while preserving first occurrence.',[{'input':[[3,1,3,2,1]],'output':[3,1,2]}]),('frequency','Write only Python code defining solve(s) that returns a character frequency dictionary.',[{'input':['aba'],'output':{'a':2,'b':1}}]),('palindrome','Write only Python code defining solve(s) that returns whether s equals its reverse.',[{'input':['level'],'output':True}]),('rotate','Write only Python code defining solve(xs) that rotates a list left by one position.',[{'input':[[1,2,3]],'output':[2,3,1]}]),('whitespace','Write only Python code defining solve(s) that collapses whitespace runs to one space and strips ends.',[{'input':['  a\t b\n'],'output':'a b'}]),('digits','Write only Python code defining solve(s) that sums decimal digit characters in s.',[{'input':['a7b2'],'output':9}])]
 for name,p,tests in code:add(rows,'BASIC_CODE',p,{'function':'solve','tests':tests},{'type':'python_unit_tests','forbidden_imports':['all']},{'task':name})
 for p,g in [('Which gas is O2? Return one lowercase word.','oxygen'),('At sea level, water freezes at how many Celsius degrees? Return integer only.','0'),('Which organ pumps blood? Return one lowercase word.','heart'),('What force keeps planets in orbit? Return one lowercase word.','gravity'),('What is the SI unit of electric current? Return one lowercase word.','ampere')]:add(rows,'BASIC_SCIENCE',p,g,{'type':'normalized_string_exact'})
 assert len(rows)==100
 prompts=[x['prompt'] for x in rows]; norm=[' '.join(x.casefold().split()) for x in prompts]; assert len(set(prompts))==100 and len(set(norm))==100
 d=ROOT/'data/general'; raw='\n'.join(json.dumps(x,ensure_ascii=False,sort_keys=True) for x in rows)+'\n';(d/'general_eval_v0_1.jsonl').write_text(raw,encoding='utf-8'); scoring={'version':'POST_TRAINING_BLIND_GENERAL_EVAL_V0_1_SCORING_1','machine_checkable_only':True,'external_llm_used':False};(d/'general_eval_v0_1_scoring.json').write_text(json.dumps(scoring,indent=2),encoding='utf-8')
 m={'status':'POST_TRAINING_BLIND_GENERAL_EVAL_V0_1_FROZEN','case_count':100,'family_distribution':Counter(x['family'] for x in rows),'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'normalized_sha256':hashlib.sha256(raw.encode()).hexdigest(),'unique_prompt_count':100,'exact_duplicate_prompts':0,'normalized_duplicate_prompts':0,'generator_seed':SEED,'scoring_version':scoring['version'],'creation_time_utc':datetime.now(timezone.utc).isoformat(),'blind_before_inference':True,'inference_executed':False};(d/'general_eval_v0_1_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2,default=dict),encoding='utf-8')
if __name__=='__main__':main()
