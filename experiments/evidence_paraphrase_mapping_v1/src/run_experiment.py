from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.evidence_sufficiency_v1.policy import compact, decompose_query, extract_entities
from src.evidence_sufficiency_v1.runtime import evaluate_evidence
from src.runtime_v1.freeze_loader_v1_1 import build_dense_retriever_v1

from mapping_candidates import evaluate_candidate

EXP = ROOT / 'experiments/evidence_paraphrase_mapping_v1'
CFG = json.loads((EXP / 'config/experiment_config.json').read_text(encoding='utf-8'))


def cases():
    demo = [json.loads(line) for line in (ROOT / 'experiments/demo_runtime_validation_v1/data/demo_question_set_v1.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    positive = [json.loads(line) for line in (ROOT / 'experiments/positive_demo_validation_v1/data/positive_demo_question_set_v1.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    by_demo = {row['demo_id']: row for row in demo}
    by_pos = {row['demo_id']: row for row in positive}
    selected = [
        {'case_id': 'DEMO002', 'query': by_demo['DEMO002']['query'], 'label': 'TARGET_FALSE_NEGATIVE', 'expected_baseline': 'INSUFFICIENT'},
        {'case_id': 'POS003', 'query': by_pos['POS003']['query'], 'label': 'TARGET_FALSE_NEGATIVE', 'expected_baseline': 'INSUFFICIENT'},
        {'case_id': 'DEMO013', 'query': by_demo['DEMO013']['query'], 'label': 'TARGET_FALSE_NEGATIVE', 'expected_baseline': 'INSUFFICIENT'},
        {'case_id': 'POS001', 'query': by_pos['POS001']['query'], 'label': 'POSITIVE_FULL', 'expected_baseline': 'SUFFICIENT'},
        {'case_id': 'POS004', 'query': by_pos['POS004']['query'], 'label': 'POSITIVE_PARTIAL', 'expected_baseline': 'PARTIAL'},
        {'case_id': 'POS007', 'query': by_pos['POS007']['query'], 'label': 'POSITIVE_PARAPHRASE', 'expected_baseline': 'PARTIAL'},
        {'case_id': 'DEMO005', 'query': by_demo['DEMO005']['query'], 'label': 'SAFETY_REFUSAL', 'expected_baseline': 'INSUFFICIENT'},
        {'case_id': 'DEMO012', 'query': by_demo['DEMO012']['query'], 'label': 'SAFETY_CITATION_BOUNDARY', 'expected_baseline': 'SUFFICIENT'},
        {'case_id': 'DEMO006', 'query': by_demo['DEMO006']['query'], 'label': 'SAFETY_INSUFFICIENT', 'expected_baseline': 'INSUFFICIENT'},
        {'case_id': 'HN_ENTITY_OTHER', 'query': '北京大学奖学金申请需要哪些基本条件？', 'label': 'HARD_NEGATIVE_ENTITY', 'expected_baseline': 'INSUFFICIENT'},
        {'case_id': 'HN_AMOUNT', 'query': '清华大学奖学金金额是多少？', 'label': 'HARD_NEGATIVE_NUMERIC', 'expected_baseline': 'INSUFFICIENT'},
        {'case_id': 'HN_CONTACT', 'query': '清华大学奖学金申请联系电话是什么？', 'label': 'HARD_NEGATIVE_CONTACT', 'expected_baseline': 'INSUFFICIENT'},
    ]
    return selected


def main():
    EXP.joinpath('audit').mkdir(parents=True, exist_ok=True)
    EXP.joinpath('data').mkdir(parents=True, exist_ok=True)
    EXP.joinpath('results').mkdir(parents=True, exist_ok=True)
    EXP.joinpath('reports').mkdir(parents=True, exist_ok=True)
    selected = cases()
    (EXP / 'data/targeted_mapping_cases.jsonl').write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in selected) + '\n', encoding='utf-8')
    retriever = build_dense_retriever_v1()
    baseline_rows = []
    for case in selected:
        retrieval = retriever.retrieve(case['query'], case['case_id'])
        evidence = evaluate_evidence(case['query'], case['case_id'], retrieval)
        row = {**case, 'retrieval': retrieval, 'evidence': evidence}
        baseline_rows.append(row)
    hashes = {}
    for path in [ROOT / 'src/evidence_sufficiency_v1/runtime.py', ROOT / 'src/evidence_sufficiency_v1/policy.py', ROOT / 'src/evidence_sufficiency_v1/schema.py', ROOT / 'evaluation/evidence_sufficiency/v1/config/runtime_v1.json']:
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    freeze = {'version': 'EVIDENCE_PARAPHRASE_MAPPING_BASELINE_FREEZE_V1', 'production_version': 'EVIDENCE_SUFFICIENCY_V1', 'config': CFG['production_evidence_thresholds'], 'cases': [{'case_id': row['case_id'], 'decision': row['evidence']['decision'], 'required_points': row['evidence']['required_points'], 'requested_attributes': row['evidence']['requested_attributes'], 'missing_requested_attributes': row['evidence']['missing_requested_attributes'], 'entity_trace': {'query_entities': row['evidence']['diagnostics'].get('query_entities'), 'missing_query_entities': row['evidence']['diagnostics'].get('missing_query_entities')}, 'reason_codes': row['evidence']['reason_codes']} for row in baseline_rows], 'production_file_sha256': hashes}
    (EXP / 'audit/baseline_freeze.json').write_text(json.dumps(freeze, ensure_ascii=False, indent=2), encoding='utf-8')
    candidate_rows = []
    thresholds = {'supported': 0.52, 'partial': 0.18, 'document_relevance': 0.08, 'rescue_lower': 0.15, 'rescue_upper': 0.18, 'rescue_dense': 0.60}
    for row in baseline_rows:
        for candidate in ['BASELINE', 'ENTITY_GUARD', 'PARAPHRASE_NORMALIZATION', 'SEMANTIC_RESCUE']:
            if candidate == 'BASELINE':
                result = {'decision': row['evidence']['decision'], 'required_points': [{'point_id': p['point_id'], 'status': p['status'], 'best_score': p['best_support_score'], 'rescue': False} for p in row['evidence']['required_points']], 'entity_trace': {'before': row['evidence']['diagnostics'].get('query_entities', []), 'after': row['evidence']['diagnostics'].get('query_entities', []), 'ignored': [], 'passed': not bool(row['evidence']['diagnostics'].get('missing_query_entities'))}, 'candidate': candidate}
            else:
                result = evaluate_candidate(row, candidate, thresholds)
            candidate_rows.append({'case_id': row['case_id'], 'label': row['label'], 'expected_baseline': row['expected_baseline'], **result})
    (EXP / 'results/case_level_results.jsonl').write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in candidate_rows) + '\n', encoding='utf-8')
    print(json.dumps({'cases': len(selected), 'candidate_rows': len(candidate_rows)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
