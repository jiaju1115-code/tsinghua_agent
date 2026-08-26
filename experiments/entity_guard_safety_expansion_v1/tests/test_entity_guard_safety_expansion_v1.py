import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/entity_guard_safety_expansion_v1'

def test_results_exist_and_cover_expanded_families():
    rows=[json.loads(x) for x in (EXP/'results/original_entity_guard_results.jsonl').read_text(encoding='utf8').splitlines() if x]
    assert len(rows) >= 30
    assert {'A_PSEUDO_ENTITY_POSITIVE','B_TRUE_ENTITY_MISSING_NEGATIVE','C_MIXED','D_ADVERSARIAL_HARD_NEGATIVE'} <= {r['case_family'] for r in rows}

def test_no_confirmed_false_promote():
    audit=json.loads((EXP/'audit/false_promote_audit.json').read_text(encoding='utf8'))
    assert audit['count']==len(audit['confirmed_false_promotes'])

def test_production_hashes_are_present():
    freeze=json.loads((EXP/'audit/baseline_freeze.json').read_text(encoding='utf8'))
    assert len(freeze['production_file_sha256'])==4
    assert freeze['entity_guard_source_sha256']
