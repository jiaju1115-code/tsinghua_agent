import sys, importlib.util, platform
mods=['torch','transformers','datasets','peft','accelerate','safetensors','yaml','bitsandbytes']
print('python',sys.version); print('platform',platform.platform())
for m in mods: print(m, bool(importlib.util.find_spec(m)))
try:
 import torch
 print('cuda_available',torch.cuda.is_available())
 if torch.cuda.is_available(): print('gpu',torch.cuda.get_device_name(0),'memory_gb',round(torch.cuda.get_device_properties(0).total_memory/2**30,2),'bf16_supported',torch.cuda.is_bf16_supported())
except Exception as e: print('torch_error',repr(e))
