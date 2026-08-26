import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; EXP=ROOT/'experiments/semantic_rescue_safety_expansion_v1'
def test_expanded_coverage():
 rows=[json.loads(x) for x in (EXP/'results/case_level_results.jsonl').read_text(encoding='utf8').splitlines() if x]
 assert len(rows)>=40
 assert {r['case_family'] for r in rows}>={'A_TRUE_PARAPHRASE_POSITIVE','B_ENTITY_MISMATCH','C_NUMERIC_NEGATIVE','D_TEMPORAL_NEGATIVE','E_NEGATION_LOGIC','F_REQUIRED_POINT_MISMATCH','G_MULTI_OBJECT_MIXED','H_OOD_TOPIC_NEAR'}
def test_freeze_contains_original_candidate_hash():
 f=json.loads((EXP/'audit/baseline_freeze.json').read_text(encoding='utf8'))
 assert f['baseline_reproduced'] and f['semantic_rescue_original_sha256']
def test_guard_never_triggers_on_blocked_case():
 rows=[json.loads(x) for x in (EXP/'results/case_level_results.jsonl').read_text(encoding='utf8').splitlines() if x]
 assert all(not r['candidates']['SEMANTIC_RESCUE_GUARDED']['rescue_triggered'] for r in rows if r['eligibility_block_reasons'])
