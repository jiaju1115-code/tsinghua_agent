#!/usr/bin/env bash
set -euo pipefail
python scripts/verify_integrity.py
python scripts/check_model_access.py
python scripts/train_lora.py --config config/training_config.yaml
