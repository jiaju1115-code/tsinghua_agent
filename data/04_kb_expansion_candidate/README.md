# KB Expansion Candidate Pipeline

Isolated candidate-only flow: `raw → source validation → dedup → quality/privacy check → category → chunk candidate → KB V2 candidate`.

`pipeline.py input.jsonl output.jsonl` accepts raw records with `source_url`, `title`, and `text`. It does not read, rewrite, re-chunk, or admit data to KB V1. Every record remains pending/manual-review until a future KB V2 process approves it.
