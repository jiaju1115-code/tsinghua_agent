import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; OUT=ROOT/'data/fine_tuning_v1'; EXP=ROOT/'experiments/fine_tuning_dataset_v1'
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def test_no_final_split_or_training_files():
 assert not any((OUT/x).exists() for x in ['train.jsonl','validation.jsonl','test.jsonl'])
def test_partial_policy_candidate_gate():
 xs=rows(OUT/'campus_grounded_candidates/partial_candidates.jsonl')
 assert len(xs)==20 and all(len(x['required_points'])>=2 and x['supported_required_points'] and x['unsupported_required_points'] and not x['conflicting_required_points'] for x in xs)
def test_held_out_scan_and_hard_negative_retention():
 d=json.loads((EXP/'audit/dedup_report.json').read_text(encoding='utf8')); h=rows(OUT/'campus_grounded_candidates/not_supported_candidates.jsonl')
 assert d['status']=='PASS' and sum(x['quality_status']=='GOLD' for x in h)==16
