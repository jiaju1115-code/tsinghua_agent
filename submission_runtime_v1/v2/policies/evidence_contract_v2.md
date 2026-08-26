# Evidence Contract V2

## Status

- `SUFFICIENT`: every material requested point is supported; no required
  freshness check fails.
- `PARTIAL`: at least one requested point is supported and at least one is
  missing or not current enough.
- `INSUFFICIENT`: no material requested point is supported, evidence is wrong
  entity/type, or a required freshness condition fails.

## Structured judge payload

```json
{
  "status": "SUFFICIENT | PARTIAL | INSUFFICIENT",
  "requested_points": [],
  "supported_points": [],
  "missing_points": [],
  "evidence_ids": [],
  "reason_codes": []
}
```

## Deterministic invariants

1. The payload must parse as a JSON object.
2. Status must be one of the three values above.
3. Every `evidence_id` must exist in the retrieved evidence set.
4. `SUFFICIENT` requires non-empty support and empty missing points.
5. `PARTIAL` requires both non-empty support and non-empty missing points.
6. `INSUFFICIENT` must not claim supported points or evidence IDs.
7. Any invariant violation fails closed to `INSUFFICIENT` with a validator
   reason code.
8. Time-sensitive queries require explicit applicable date/time evidence.

Citation formatting may use only validated evidence IDs. It must never ask the
answer model to invent a title or URL.
