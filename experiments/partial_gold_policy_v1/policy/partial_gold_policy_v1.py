"""Experiment-only Gold Policy V1 validator; never imported by production."""
from __future__ import annotations

BLOCKING_CONFLICTS={'entity','numeric','temporal','scope','negation','logic','wrong_attribute','ood','multi_object'}

def classify_gold(required_points, supported_points, unsupported_points, conflicts):
    if conflicts & BLOCKING_CONFLICTS:
        return 'NOT_SUPPORTED'
    if len(required_points) < 2:
        return 'NOT_SUPPORTED'
    if supported_points and unsupported_points:
        return 'PARTIAL'
    return 'SUPPORTED' if len(supported_points)==len(required_points) else 'NOT_SUPPORTED'

def validate_partial_candidate(row):
    required=row['required_points']; supported=row['supported_required_points']; unsupported=row['unsupported_required_points']
    return (len(required)>=2 and bool(supported) and bool(unsupported)
            and not row['conflicting_required_points'] and bool(row['evidence_spans'])
            and row['gold_candidate']=='PARTIAL')
