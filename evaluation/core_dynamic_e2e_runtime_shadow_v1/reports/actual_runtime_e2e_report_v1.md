# Actual Frozen Runtime E2E Shadow Execution V1

## Outcome

Actual execution is **blocked before retrieval**. `DenseRetrieverV1._verify_bundle()` rejects both freeze manifests because their working-tree SHA256 values differ from checked sidecars. No proxy output is counted as an actual runtime metric.

## Execution

- Cases: 80 (unchanged input hash recorded)
- Retrieval executed: 0
- Evidence executed: 0
- Citation executed: 0
- Answer executed: 0
- Runtime errors: 80

## Required fix

Determine why Git working-tree bytes differ from frozen sidecar hashes (likely line-ending materialization), then create a separately versioned valid frozen bundle or make the freeze process platform-stable. Do not edit the current frozen files in place. After a new valid bundle is approved, rerun this exact case file.

## Readiness

`NEEDS_RUNTIME_INTEGRATION_FIX`
