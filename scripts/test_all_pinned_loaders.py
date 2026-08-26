import json
from pathlib import Path
from datasets import load_dataset
from huggingface_hub import hf_hub_url

sources = [
 ('nvidia/Nemotron-Instruction-Following-Chat-v1','83dcd3aded0d289b0bbc018d3f9af4c5dd4005df','json','data/structured_outputs.jsonl'),
 ('allenai/tulu-3-sft-personas-instruction-following','fe0c7d350c9b4542b8d829a6f1daa1c259f0ba0e','parquet','data/train-00000-of-00001.parquet'),
 ('databricks/databricks-dolly-15k','bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a','json','databricks-dolly-15k.jsonl'),
 ('rajpurkar/squad','7b6d24c440a36b6815f21b70d25016731768db1f','parquet','plain_text/train-00000-of-00001.parquet'),
 ('tasksource/ruletaker','a3e0880baeb6ec3d478f4c4d85afe04b21b6cf7f','parquet','data/train-00000-of-00001-52adaa842dd7ed92.parquet'),
 ('nvidia/OpenCodeInstruct','8f3ba5bafe4d6e8db46082cf7ae6741bc370604d','parquet','data/train-00000-of-00050.parquet'),
 ('google-research-datasets/mbpp','4bb6404fdc6cacfda99d4ac4205087b89d32030c','parquet','full/train-00000-of-00001.parquet'),
]
result=[]
for ds,rev,fmt,file in sources:
 try:
  url=hf_hub_url(ds,file,repo_type='dataset',revision=rev)
  row=next(iter(load_dataset(fmt,data_files={'train':url},split='train',streaming=True)))
  result.append({'dataset':ds,'ok':True,'keys':sorted(row)})
 except Exception as exc: result.append({'dataset':ds,'ok':False,'error':f'{type(exc).__name__}: {exc}'})
try:
 row=next(iter(load_dataset('facebook/babi_qa','en-10k-qa1',split='train',revision='021d7aeb7307b7856dd0632f92827bc607dc2f1b',streaming=True,trust_remote_code=True)))
 result.append({'dataset':'facebook/babi_qa','ok':True,'keys':sorted(row)})
except Exception as exc: result.append({'dataset':'facebook/babi_qa','ok':False,'error':f'{type(exc).__name__}: {exc}'})
Path('evaluation/fine_tuning_pilot_v1_revision_recovery_v2_1_loader_matrix.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
