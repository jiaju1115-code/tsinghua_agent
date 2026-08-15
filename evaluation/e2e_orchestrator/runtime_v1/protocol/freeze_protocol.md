# Held-out protocol freeze rules

- Do not add, remove, rewrite, or replace cases after answers are observed.
- Freeze case file, schema, sampling rationale, rubric, reviewer instructions, and runtime manifest with SHA-256 sidecars.
- Keep contract fixtures, natural runtime checks, historical sets, and held-out cases in disjoint files and reports.
- Any runtime or upstream freeze hash change invalidates the scheduled evaluation and requires a new protocol version.
- This repository currently contains no populated held-out E2E case file and no held-out answer file.
