#!/usr/bin/env bash
set -euo pipefail
python scripts/check_environment.py
python scripts/check_model_access.py
