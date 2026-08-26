from __future__ import annotations
import ast,json,re,subprocess,sys
def _norm(s): return ' '.join(s.strip().split())
def _code_score(code, tests):
 try:
  tree=ast.parse(code)
  if any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(tree)): return 0,'forbidden import'
  if not any(isinstance(n,ast.FunctionDef) and n.name=='solve' for n in tree.body): return 0,'missing solve function'
 except SyntaxError:return 0,'syntax error'
 harness="""import json,sys\np=json.loads(sys.stdin.read()); safe={'abs':abs,'all':all,'any':any,'bool':bool,'dict':dict,'enumerate':enumerate,'float':float,'int':int,'len':len,'list':list,'max':max,'min':min,'range':range,'reversed':reversed,'set':set,'sorted':sorted,'str':str,'sum':sum,'tuple':tuple,'zip':zip}\nns={'__builtins__':safe}; exec(compile(p['code'],'<model>','exec'),ns,ns); fn=ns['solve']; print(json.dumps([fn(*t['input'])==t['output'] for t in p['tests']]))"""
 try:
  r=subprocess.run([sys.executable,'-I','-c',harness],input=json.dumps({'code':code,'tests':tests}),text=True,capture_output=True,timeout=2,check=False)
  ok=r.returncode==0 and all(json.loads(r.stdout));return (int(ok),'unit tests passed' if ok else 'unit tests failed')
 except subprocess.TimeoutExpired:return 0,'code timeout'
def score_output(raw, case):
 rubric=case['scoring_rubric']; typ=rubric['type']; gold=case['gold']; text=raw.strip()
 if typ=='json_exact':
  try: parsed=json.loads(text); ok=parsed==gold and (not rubric.get('forbidden_extra_text') or text.startswith('{') and text.endswith('}'));return parsed,int(ok),'json exact' if ok else 'json mismatch'
  except Exception:return None,0,'invalid JSON or extra prose'
 if typ=='integer_exact':
  ok=bool(re.fullmatch(r'-?\d+',text)) and text==str(gold);return text,int(ok),'integer exact' if ok else 'integer mismatch'
 if typ=='reduced_fraction_exact':
  ok=bool(re.fullmatch(r'-?\d+/[1-9]\d*',text)) and text==gold;return text,int(ok),'reduced fraction exact' if ok else 'fraction mismatch'
 if typ in ('normalized_string_exact','string_exact'):
  value=_norm(text) if typ=='normalized_string_exact' else text; target=_norm(str(gold)) if typ=='normalized_string_exact' else str(gold);return value,int(value==target),'string exact' if value==target else 'string mismatch'
 if typ=='python_unit_tests':
  score,reason=_code_score(raw,gold['tests']);return None,score,reason
 return None,0,'unknown scorer type'
