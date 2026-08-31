$ErrorActionPreference = 'Stop'
python validate_dataset.py
python train_lora.py @args
