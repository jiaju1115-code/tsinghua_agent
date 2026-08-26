# PARTIAL Gold Policy & Fine-tuning Data Preparation V1

## Freeze and policy

Source freeze passed. `PARTIAL Gold Policy V1` is frozen for future evaluation
and candidate-data labelling only, not production. A Gold `PARTIAL` requires at
least two independent required points, a precise conflict-free span supporting at
least one point, and at least one other independently missing point. The supported
part must form a safe sub-answer.

Single incomplete points, wrong attributes/objects, entity/numeric/temporal/scope/
negation/logical conflicts, OOD overlap, and ambiguous multi-object matches are
Gold `NOT_SUPPORTED`.

## Candidate assets

- 16 confirmed false-promote records entered `hard_negative_candidates.jsonl`.
- All 7 policy-mismatch records received `POLICY_REALIGNMENT_PROPOSED`: under
  Gold Policy V1 they are `NOT_SUPPORTED`, while no historical label was changed.
- 20 controlled `EVIDENCE_ABLATION` candidates passed the VALID PARTIAL quality
  gate. Every candidate has exactly two independent points, one retained frozen
  factual span, one independently uncovered point, no conflict, and parent-source
  provenance. Distribution: REAL 0, HISTORICAL 0, CONTROLLED-SYNTHETIC 20.

These are candidate pools only: no train/validation/test split, no model training,
and no external data download occurred.

## F04 and held-out protection

F04 is `PROVENANCE_ATTRIBUTION_ERROR_CONFIRMED`: its production primary result
was `INSUFFICIENT`, while the prior candidate final output was `PARTIAL`; the
previous aggregate description incorrectly treated it as inherited production
PARTIAL. Policy V1 resolves it as `NOT_SUPPORTED` (single incomplete point),
without modifying historical artifacts.

DEMO002, POS003, and DEMO013 are all marked `HELD_OUT_FAMILY` and excluded from
candidate pools, their paraphrases, source-near duplicates, and future training
splits.

## Inventory and decision

The first candidate-asset inventory records 16 hard negatives and 20 valid-partial
candidates. Human Gold, positive inventories, retriever-mined near negatives, and
general-capability datasets remain `NOT_YET_ACQUIRED`.

**PARTIAL_GOLD_POLICY_READY**

Production Evidence, Retriever, KB, Citation, Answer, frozen evaluation data, and
historical experiments are unchanged. No fine-tuning dataset or training process
was started.
