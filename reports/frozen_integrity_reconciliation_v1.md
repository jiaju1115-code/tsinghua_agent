# Frozen Integrity Reconciliation V1

## Decision

**FROZEN_INTEGRITY_CONFIRMED**

The three apparent mismatches are a Windows line-ending representation difference, not a content change. `core.autocrlf=true` checked the three text files out with CRLF. Replacing each CRLF with LF reproduces both the original frozen SHA256 and the exact Git blob at commit `75a6b89d7a0c2550f6dc3805b5e37feeec61f176`.

| File | Raw mismatch | CRLF count | Canonical result |
| --- | --- | ---: | --- |
| `manifests/source_manifest.jsonl` | yes | 122 | exact frozen/Git blob match |
| `chunks/chunks.jsonl` | yes | 488 | exact frozen/Git blob match |
| `config/retriever_v1.json` | yes | 1 | exact frozen/Git blob match |
| `index/document_embeddings.npy` | no | n/a | raw binary match |

## Semantic comparison

The source-manifest records are equal (122/122); source IDs and metadata are unchanged. Chunk records are equal (488/488), including chunk IDs, source IDs, text, offsets, provenance, and ordering. Parsed retriever configuration is equal; no retrieval parameters changed.

## Runtime mapping

The submission-candidate `RuntimeV1` uses `Frozen Bundle V1.1` through `src/runtime_v1/freeze_loader_v1_1.py`. Its approved portability loader reads the same `data/03_knowledge_base/v1` paths and validates text with `CANONICAL_TEXT_V1` and the embedding index with raw SHA256. The legacy direct `src/retrieval_v1/adapter.py` retains raw-byte checks and is not the candidate runtime entrypoint.

No historical freeze manifest was modified. The current verification JSON is an additive reconciliation record, not a replacement manifest.
