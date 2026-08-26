import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; EXP=ROOT/'experiments/partial_semantics_audit_v1'
def test_audits_match_source_target_count():
 f=json.loads((EXP/'audit/source_freeze.json').read_text(encoding='utf8')); rows=[json.loads(x) for x in (EXP/'results/partial_case_audit.jsonl').read_text(encoding='utf8').splitlines() if x]
 assert len(rows)==f['target_count']==24
def test_only_allowed_classes_and_future_uses():
 rows=[json.loads(x) for x in (EXP/'results/partial_case_audit.jsonl').read_text(encoding='utf8').splitlines() if x]
 assert {x['audit_class'] for x in rows}<={'CONFIRMED_PRODUCTION_FALSE_PROMOTE','VALID_PARTIAL','LABEL_POLICY_MISMATCH','HUMAN_REVIEW_REQUIRED'}
 assert {x['recommended_future_use'] for x in rows}<={'HARD_NEGATIVE_CANDIDATE','VALID_PARTIAL_TRAINING_CANDIDATE','EVAL_POLICY_FIX_REQUIRED','HUMAN_REVIEW'}
