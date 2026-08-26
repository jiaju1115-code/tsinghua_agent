# Revision pin audit

Stage 1 specified an immutable revision for each permitted source. This run
recorded those revisions in `source_revisions.json`; however, the Hugging Face
Dataset Server `rows` and `filter` endpoints used for bounded sampling do not
return the resolved Git SHA, and their request contract did not provide a
verifiable revision field. Consequently the run cannot establish that the
served rows came from the recorded revisions.

Status: **FAIL — revision pin not verifiable**.

This is a provenance stop condition only. It does not alter the frozen V1.2
pool, the General V0.1 evaluation set, the accepted/rejected artifacts, or the
zero-leakage result. A later replay must use revision-addressable, range-bounded
artifacts and regenerate all Stage 2 outputs before any Pilot V1 dataset build.
