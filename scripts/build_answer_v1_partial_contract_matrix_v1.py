from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
trace_path = ROOT / 'experiments/answer_v1_partial_contract_fix/audit/answer_v1_partial_contract_runtime_trace_v1.json'
matrix_path = ROOT / 'experiments/answer_v1_partial_contract_fix/audit/answer_v1_partial_contract_failure_matrix.json'
trace = json.loads(trace_path.read_text(encoding='utf-8'))

rows = []
for case in trace['cases']:
    raw = json.loads(case['raw_model_output'])
    claims = raw['claims']
    if case['case_id'] == 'POS002':
        failed_rule = 'unique required_point_id per factual claim'
        expected = 'one claim for each allowed required point; no duplicate point IDs'
        actual = 'P1 emitted twice; P2 is not allowed by the PARTIAL package'
    elif case['case_id'] == 'POS006':
        failed_rule = 'support_unit_ids must be mapped to the same required point'
        expected = 'every declared support ID belongs to the claim point mapping'
        actual = 'P2 declared CSU-9E5F311CD95CDDBD, which is outside the P2 allowed mapping'
    else:
        failed_rule = 'all allowed required points must be represented'
        expected = 'one claim for every allowed supported/partially-supported point'
        actual = 'P1 emitted; allowed P2 was omitted'
    rows.append({
        'case_id': case['case_id'],
        'raw_output_shape': 'valid JSON object; frozen model keys present',
        'parse_status': 'JSON_PARSE_PASS',
        'validation_status': 'FAIL_CLOSED',
        'failed_rule': failed_rule,
        'expected_contract': expected,
        'actual_contract': actual,
        'root_cause': 'MODEL_SCHEMA_NONCOMPLIANCE',
        'same_family': True,
        'raw_claim_count': len(claims),
        'runtime_reason_code': case['validation_result']['reason_codes'],
        'runtime_final_status': case['runtime_final_status'],
    })

matrix_path.write_text(json.dumps({
    'version': 'ANSWER_V1_PARTIAL_CONTRACT_FAILURE_MATRIX_V1',
    'contract_review': {
        'prompt_contract': 'one exact factual claim per allowed required point with mapped support IDs',
        'parser_contract': 'strict top-level and claim shape; unique point IDs; mapped support IDs; complete allowed scope',
        'validator_contract': 'invalid/malformed/unsupported output fails closed to REFUSAL',
        'runtime_contract': 'PARTIAL support may complete only as PARTIAL_ANSWER with deterministic limitation; invalid model output is not a completed answer',
        'mismatch_found': False,
    },
    'cases': rows,
    'fix_decision': {
        'status': 'ANSWER_PARTIAL_CONTRACT_FIX_BLOCKED',
        'reason': 'All three failures are model schema noncompliance. A parser relaxation would discard or invent semantic claims/support and violate fail-closed rules.',
        'semantic_generation_change': False,
    },
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(matrix_path)
