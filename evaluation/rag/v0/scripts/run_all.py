from __future__ import annotations

import json

from build_kb import DEFAULT_CONFIG, build
from run_smoke_tests import DEFAULT_CASES, run
from validate_kb import validate


if __name__ == "__main__":
    print(json.dumps({"build": build(DEFAULT_CONFIG), "smoke": run(DEFAULT_CONFIG, DEFAULT_CASES), "validation": validate()}, ensure_ascii=False, indent=2))
