# Entity Guard Safety Expansion V1

Experiment-only safety expansion for the unchanged `ENTITY_GUARD` candidate from
`evidence_paraphrase_mapping_v1`. This directory does not change production
Evidence semantics, Runtime, Retriever, KB, or frozen evaluation data.

Run from the repository root:

```powershell
python experiments/entity_guard_safety_expansion_v1/scripts/run_entity_guard_safety_expansion_v1.py
pytest -q experiments/entity_guard_safety_expansion_v1/tests
```
