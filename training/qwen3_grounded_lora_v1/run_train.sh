#!/usr/bin/env bash
set -euo pipefail
python validate_dataset.py
python train_lora.py "$@"
