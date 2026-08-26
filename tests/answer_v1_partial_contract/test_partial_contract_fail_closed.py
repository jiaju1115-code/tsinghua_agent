import json
from pathlib import Path

from src.answer_generation_v1 import runtime
from src.answer_generation_v1.policy import load_config


def _context_package():
    return {
        'support_status': 'PARTIAL',
        'required_point_support': [
            {'point_id': 'P1', 'point_text': 'first', 'mapping_status': 'SUPPORTED', 'support_unit_ids': ['U1']},
            {'point_id': 'P2', 'point_text': 'second', 'mapping_status': 'PARTIALLY_SUPPORTED', 'support_unit_ids': ['U2']},
        ],
        'usable_source_ids': ['S1'],
    }


def _context():
    return {'unit_map': {'U1': {'span_text': 'first fact', 'source_id': 'S1'}, 'U2': {'span_text': 'second fact', 'source_id': 'S1'}}}


def test_partial_contract_rejects_duplicate_wrong_and_missing_scope():
    package = _context_package()
    context = _context()
    config = load_config()
    cases = [
        ('{"answer_status":"PARTIAL_ANSWER","claims":[{"required_point_id":"P1","claim_text":"first fact","support_unit_ids":["U1"]},{"required_point_id":"P1","claim_text":"another fact","support_unit_ids":["U1"]}]}', 'ANSWER_SCHEMA_INVALID'),
        ('{"answer_status":"PARTIAL_ANSWER","claims":[{"required_point_id":"P1","claim_text":"first fact","support_unit_ids":["U1"]},{"required_point_id":"P2","claim_text":"second fact","support_unit_ids":["U1"]}]}', 'INVALID_SUPPORT_REFERENCE'),
        ('{"answer_status":"PARTIAL_ANSWER","claims":[{"required_point_id":"P1","claim_text":"first fact","support_unit_ids":["U1"]}]}', 'PARTIAL_SCOPE_VIOLATION'),
    ]
    for raw, expected in cases:
        records, code, _ = runtime._parse_model_output(raw, package, context, config)
        assert records is None
        assert code == expected


def test_partial_contract_accepts_valid_partial_shape_and_preserves_scope():
    raw = '{"answer_status":"PARTIAL_ANSWER","claims":[{"required_point_id":"P1","claim_text":"first fact","support_unit_ids":["U1"]},{"required_point_id":"P2","claim_text":"second fact","support_unit_ids":["U2"]}]}'
    records, code, message = runtime._parse_model_output(raw, _context_package(), _context(), load_config())
    assert code is None, message
    assert [row['required_point_ids'] for row in records] == [['P1'], ['P2']]


def test_runtime_trace_matrix_records_three_real_failures_as_one_family():
    root = Path(__file__).resolve().parents[2]
    matrix = json.loads((root / 'experiments/answer_v1_partial_contract_fix/audit/answer_v1_partial_contract_failure_matrix.json').read_text(encoding='utf-8'))
    assert [row['case_id'] for row in matrix['cases']] == ['POS002', 'POS006', 'POS008']
    assert all(row['same_family'] and row['root_cause'] == 'MODEL_SCHEMA_NONCOMPLIANCE' for row in matrix['cases'])
    assert matrix['fix_decision']['status'] == 'ANSWER_PARTIAL_CONTRACT_FIX_BLOCKED'
