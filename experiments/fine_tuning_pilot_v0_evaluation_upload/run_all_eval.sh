#!/usr/bin/env bash
set -euo pipefail
bash "$(dirname "$0")/run_preflight.sh" "$@"
bash "$(dirname "$0")/run_general_eval.sh" "$@"
bash "$(dirname "$0")/run_campus_eval.sh" "$@"
python scripts/build_general_comparison.py
python scripts/compare_results.py
python scripts/validate_outputs.py
python scripts/build_final_report.py
