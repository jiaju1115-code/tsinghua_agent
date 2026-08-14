import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from run_ab_evaluation import normalize,summary
def jl(p):return[json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
for g in ("a","b"):
    gen={x["question_id"]:x for x in jl(ROOT/"results"/f"generation_{g}.jsonl")}; p=ROOT/"results"/f"evaluation_{g}.jsonl"; old=jl(p); new=[]
    for r in old:
        raw=json.loads(r["evaluator_raw_output"]);r["auto_evaluation"]=normalize(gen[r["question_id"]],raw);new.append(r)
    with p.open("w",encoding="utf-8",newline="\n") as f:
        for r in new:f.write(json.dumps(r,ensure_ascii=False)+"\n")
    (ROOT/"results"/f"metrics_{g}.json").write_text(json.dumps(summary(new),ensure_ascii=False,indent=2),encoding="utf-8")
    print(g,json.dumps(summary(new),ensure_ascii=False))
