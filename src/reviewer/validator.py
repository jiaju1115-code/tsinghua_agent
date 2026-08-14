from reviewer.schema import validate_review
from utils.json_utils import parse_json_object

def parse_and_validate(text,expected_id):return validate_review(parse_json_object(text),expected_id)

