from pathlib import Path
import hashlib
root=Path(__file__).resolve().parents[1]; sums=root/'integrity/SHA256SUMS.txt'; bad=[]
for line in sums.read_text(encoding='utf-8').splitlines():
 h,p=line.split('  ',1); q=root/p
 if not q.exists() or hashlib.sha256(q.read_bytes()).hexdigest()!=h: bad.append(p)
print({'policy':'STATIC_INPUT_INTEGRITY','checked':len(sums.read_text(encoding='utf-8').splitlines()),'mismatch':bad,'runtime_artifacts_excluded':True}); raise SystemExit(1 if bad else 0)
