import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / 'experiments/evidence_paraphrase_mapping_v1'


def test_candidate_comparison_has_zero_false_promote_and_selects_entity_guard():
    result = json.loads((EXP / 'results/candidate_comparison.json').read_text(encoding='utf-8'))
    assert result['decision'] == 'SAFE_CANDIDATE_IDENTIFIED'
    assert result['best_by_target_recovery'] == 'ENTITY_GUARD'
    assert all(row['false_promote_count'] == 0 for row in result['candidates'])


def test_overfitting_audit_has_no_case_specific_logic():
    audit = json.loads((EXP / 'audit/overfitting_audit.json').read_text(encoding='utf-8'))
    assert all(value is False for value in audit['checks'].values())


def test_baseline_freeze_records_frozen_production_hashes():
    freeze = json.loads((EXP / 'audit/baseline_freeze.json').read_text(encoding='utf-8'))
    assert freeze['production_version'] == 'EVIDENCE_SUFFICIENCY_V1'
    assert len(freeze['production_file_sha256']) == 4
