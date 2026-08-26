# Cross-Platform Freeze Specification V1.1

## Binary artifacts

Use raw-byte SHA256 (`RAW_BINARY`).

## Text artifacts

Decode strict UTF-8 (UTF-8 BOM is removed), normalize CRLF and bare CR to LF, preserve all other content and existing final-newline state, then compute SHA256 (`CANONICAL_TEXT_V1`). Record both `raw_sha256` and `canonical_sha256`. Invalid UTF-8 fails closed. JSON key ordering and whitespace are not rewritten.

Verification must reject missing hashes, semantic changes, unsupported hash modes, and canonical mismatches. Legacy V1 remains read-only.
