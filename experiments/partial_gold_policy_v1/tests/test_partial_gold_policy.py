import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/partial_gold_policy_v1/policy'))
from partial_gold_policy_v1 import classify_gold, validate_partial_candidate
def test_single_unsupported_is_not_supported(): assert classify_gold(['P1'],[],['P1'],set())=='NOT_SUPPORTED'
def test_multi_point_partial(): assert classify_gold(['P1','P2'],['P1'],['P2'],set())=='PARTIAL'
def test_conflicts_block_partial():
 for c in ['entity','numeric','temporal','negation','wrong_attribute','ood']: assert classify_gold(['P1','P2'],['P1'],['P2'],{c})=='NOT_SUPPORTED'
def test_valid_candidate_shape():
 assert validate_partial_candidate({'required_points':['P1','P2'],'supported_required_points':['P1'],'unsupported_required_points':['P2'],'conflicting_required_points':[],'evidence_spans':[{'span_id':'s'}],'gold_candidate':'PARTIAL'})
