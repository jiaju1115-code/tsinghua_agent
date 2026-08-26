#!/usr/bin/env python3
import hashlib,json,re,sys
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
errors=[]
sums={}
for line in (root/"manifests/SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    digest,name=line.split("  ",1); sums[name]=digest
for name,digest in sums.items():
    p=root/name
    if not p.is_file() or sha(p)!=digest: errors.append("HASH:"+name)
train,val=jl(root/"data/train.jsonl"),jl(root/"data/validation.jsonl")
if (len(train),len(val))!=(1080,120): errors.append("COUNT")
ids=set(); norms={}
for split,rows in (("train",train),("validation",val)):
  for x in rows:
    if not x.get("id") or x["id"] in ids: errors.append("DUPLICATE_ID")
    ids.add(x.get("id")); ms=x.get("messages")
    if not isinstance(ms,list) or len(ms)<2 or ms[-1].get("role")!="assistant" or not ms[-1].get("content","").strip(): errors.append("SCHEMA")
    if any(m.get("role") not in {"system","user","assistant"} or not m.get("content","").strip() for m in ms): errors.append("ROLE_OR_EMPTY")
    md=x.get("metadata",{})
    required=("task_family","subtype","source","publisher","license","source_revision","source_config","source_split","source_file","source_row_id","source_row_index","raw_sha256","normalized_sha256")
    if any(md.get(k) in (None,"") for k in required): errors.append("PROVENANCE")
    if len(md.get("source_revision",""))!=40 or md.get("license_status")!="PASS": errors.append("LICENSE_OR_REVISION")
    n=md.get("normalized_sha256")
    if n in norms and norms[n]!=split: errors.append("TRAIN_VAL_NORMALIZED_OVERLAP")
    norms[n]=split
counts=Counter(x["metadata"]["task_family"] for x in train+val)
target={"INSTRUCTION_VALUE_FIDELITY":300,"GENERAL_QA_SCIENCE_READING":264,"GENERAL_REASONING":240,"WRITING_MULTILINGUAL":120,"CODING":96,"PROGRAMMATIC_MATH":120,"OTHER_MATH":60}
if dict(counts)!=target: errors.append("FAMILY_COUNTS")
freeze=json.loads((root/"manifests/dataset_freeze_manifest.json").read_text(encoding="utf-8"))
if freeze.get("freeze_id")!="PILOT_V1_GENERAL_REPLAY_FROZEN" or freeze.get("status")!="FROZEN": errors.append("FREEZE")
if freeze.get("general_v0_1_leakage",{}).get("accepted_overlap_count")!=0: errors.append("GENERAL_V0_1_LEAKAGE")
overlap=freeze.get("train_validation_overlap",{})
if overlap.get("status")!="PASS" or any(overlap.get(k)!=0 for k in ("exact_overlap","normalized_overlap","lexical_near_overlap","semantic_near_overlap")): errors.append("TRAIN_VAL_NEAR_OVERLAP")
lic=json.loads((root/"manifests/license_manifest.json").read_text(encoding="utf-8"))
if not lic.get("all_pass") or any(x.get("status")!="PASS" for x in lic.get("sources",[])): errors.append("LICENSE")
for p in root.rglob("*"):
  rel=p.relative_to(root).as_posix()
  if p.is_file() and not rel.startswith(("data/","tokenizer/")) and p.suffix.lower() in {".json",".jsonl",".md",".txt",".py"}:
    text=p.read_text(encoding="utf-8",errors="replace")
    if re.search(r"(?i)(?:[A-Z]:\\(?![nrt\\\"'])|[A-Z]:/)",text): errors.append("WINDOWS_ABSOLUTE_PATH:"+rel)
if errors:
  print("PACKAGE_VALIDATION_FAIL",sorted(set(errors))); sys.exit(1)
print("PACKAGE_VALIDATION_PASS")
