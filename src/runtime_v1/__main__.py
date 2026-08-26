from __future__ import annotations

import json
import sys

from .runtime import answer_query


def main() -> int:
    query = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else input("Query: ").strip()
    result = answer_query(query)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "RUNTIME_ERROR" else 2


if __name__ == "__main__":
    raise SystemExit(main())
