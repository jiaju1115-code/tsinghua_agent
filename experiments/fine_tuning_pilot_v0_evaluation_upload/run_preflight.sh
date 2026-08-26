#!/usr/bin/env bash
set -euo pipefail
python scripts/check_environment.py "$@"
python scripts/check_frozen_integrity.py
python scripts/check_contamination.py "$@"
python scripts/check_model_pair.py "$@"
