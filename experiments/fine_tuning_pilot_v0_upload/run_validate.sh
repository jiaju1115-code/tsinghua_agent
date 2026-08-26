#!/usr/bin/env bash
set -euo pipefail
python scripts/verify_integrity.py
python scripts/validate_data.py
python scripts/inspect_dataset.py
python scripts/audit_truncation_and_masking.py
python scripts/token_length_discrepancy_check.py
python scripts/dry_validate_runtime.py
