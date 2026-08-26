# Freeze Portability Report V1

Root cause: `LINE_ENDING_ONLY`. Both mismatched manifests contain one CRLF in the Windows working tree. CRLF-to-LF normalization exactly reproduces each expected sidecar hash and the Git blob bytes; parsed JSON is equal. All nested manifest hashes pass under the declared V1.1 hash modes.

Legacy Frozen V1 remains unchanged and read-only. Frozen V1.1 is now `APPROVED` as the active recommended canonical cross-platform freeze reference. Runtime E2E was not rerun because this task is limited to freeze approval and integrity; production remains disabled.
