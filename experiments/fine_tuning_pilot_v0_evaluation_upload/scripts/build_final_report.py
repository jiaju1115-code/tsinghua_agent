from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 pair=json.loads((ROOT/'results/model_pair_check.json').read_text(encoding='utf-8'))
 cmp=json.loads((ROOT/'results/comparison/comparison.json').read_text(encoding='utf-8'))
 lines=['# Fine-tuning Pilot V0 Before / After Report','','## Training reference','', '- Pilot run ID: `pilot_v0_20260817T025613Z_seed42`',f"- Adapter SHA-256: `{pair['adapter_sha256']}`",'- Base: Qwen2.5-1.5B-Instruct','- Facts: LoRA r=16, alpha=32, dropout=0.05; q/k/v/o projections; 2 epochs; seed 42; no merge; no GGUF.','','## General','','`POST_TRAINING_BLIND_GENERAL_EVAL_V0_FROZEN` — 100 post-training constructed, blind-before-inference, machine-checkable cases; audit against 757 train and 84 validation rows found zero overlap.','','## Campus — Layer A fixed-input answer generation','','Source: Held-out E2E V1, 50 cases with frozen retrieval replay. `SEMANTIC_MATCH_RAW_HASH_MISMATCH`: current raw bytes differ, while normalized-LF SHA-256 matches the historical freeze digest. Scores below are `PROVISIONAL` deterministic proxies; no external LLM or automatic gold-label creation was used.','','| Metric | Base | Pilot V0 | Delta | Result |','|---|---:|---:|---|---|']
 for m in cmp['campus_metrics']: lines.append(f"| {m['metric']} | {m['base']!s} | {m['pilot_v0']!s} | {m['delta']!s} | PROVISIONAL |")
 lines += ['','## Campus — Layer B system compatibility','','`NOT_EXECUTED`: this package does not modify or substitute a production runtime.','','## Regression cases','','`Base correct/safe → Pilot wrong/unsafe` proxy flags: '+(', '.join(cmp['regression_cases']) or 'none')+'.','','## Improvement cases','','`Base wrong → Pilot correct` proxy flags: '+(', '.join(cmp['improvement_cases']) or 'none')+'.','','## Decision','','`EVALUATION_INSUFFICIENT` — GPU results do not establish General capability and Campus answer correctness lacks gold labels. This is not a `FINAL_MODEL` declaration.']
 (ROOT/'results/comparison/fine_tuning_pilot_v0_before_after_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
if __name__=='__main__':main()
