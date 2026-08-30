# Trusted Campus Agent V2 knowledge candidate

This directory is independent from frozen `data/03_knowledge_base/v1`.

- `metadata_catalog.jsonl`: generated inventory. `serving` rows come from frozen KB V1; `auto_review_candidate` rows are processed by the automated trust gate. Legacy `review_required` is read-only compatibility data, not a human-review requirement.
- `public_crawl_v1/` and `portal_crawl_v1/`: isolated, resumable raw crawl evidence; generated state and authentication artifacts are ignored by Git.
- `crawl_candidate_manifest.jsonl`: deduplicated crawl inventory after the automated campus-affairs quality gate.
- `crawl_quality_report.json`: rejection, date and eight-scenario queue statistics.
- `attachment_crawl_v1/`: size-limited, signature-checked official PDF/Office downloads and extracted text; binary files are ignored by Git.
- `attachment_candidate_manifest.jsonl`: text-extracted official attachments waiting for strict automated authority, freshness, quality and conflict checks.
- `shadow_bundle_v1/`: opt-in, unpublished local RAG bundle; only high-confidence public official, actionable and dated crawl candidates are auto-admitted with an audit trail.
- `coverage_matrix.json` / `.md`: eight-scenario coverage and metadata-quality view.
- No staging source is used for answers by default.
- The three frozen restricted sources stay in inventory but are excluded from default retrieval until an authorization context exists.
- No file here changes, deletes, republishes or unfreezes the existing agent.

Regenerate with:

```powershell
python scripts/process_trusted_campus_v2_crawl.py --force
python scripts/download_trusted_campus_v2_attachments.py --force
python scripts/build_trusted_campus_v2_assets.py --force
python scripts/build_trusted_campus_v2_shadow_bundle.py --force --build-dense
python scripts/chat_trusted_campus_v2.py --shadow
```

The local CLI prewarms the dense Full Path before accepting a query. Use
`--no-warmup` only for diagnostics. Fast Path questions never initialize dense
retrieval in the agent runtime.

The `--force` flag only replaces these generated candidate artifacts.
