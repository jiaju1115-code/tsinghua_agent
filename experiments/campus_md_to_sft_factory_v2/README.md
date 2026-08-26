# Campus MD to SFT Factory v2

Local Codex-grounded production experiment. It reads only public, eligible canonical MD, writes compact JSONL candidates, performs exact evidence-span validation, and checkpoints after every document. It does not call momoapi or any external LLM API and does not modify production KB, retriever, evidence, citation, answer, router, frozen evaluation, or historical experiments.

Pilot: `python src/run_pilot.py`; full batch after pilot review: `python src/run_full_batch.py`. Full batch is intentionally not started by the pilot runner.
