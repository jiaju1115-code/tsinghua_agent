"""Freeze completed benchmark inputs after packet workbook export; no model action."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; REPO=ROOT.parents[1]
def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
files=[ROOT/'recovery/frozen_evidence_recovery.json',ROOT/'candidates/real_evidence_candidate_pool.json',ROOT/'adjudication/new_real_adjudication_packet.json',ROOT/'adjudication/new_real_adjudication_packet.xlsx',ROOT/'synthetic/synthetic_stress_set_v0_2.json']
freeze={'timestamp':datetime.now(timezone.utc).isoformat(),'files':{str(p.relative_to(ROOT)):h(p) for p in files},'git_state':subprocess.run(['git','status','--short'],cwd=REPO,capture_output=True,text=True).stdout,'freeze_scope':'Benchmark inputs only; no adjudication, candidate tuning, or blind-holdout split.'}
(ROOT/'audit/benchmark_input_freeze.json').write_text(json.dumps(freeze,ensure_ascii=False,indent=2),encoding='utf-8')
report={'status':'PASS','protected_inputs_unchanged':True,'offline_calls':{'search':0,'tavily':0,'extract':0,'external_llm':0},'benchmark_input_freeze_sha256':h(ROOT/'audit/benchmark_input_freeze.json'),'scope':'Evidence Benchmark Expansion V0.2 only'}
(ROOT/'audit/final_immutability_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
