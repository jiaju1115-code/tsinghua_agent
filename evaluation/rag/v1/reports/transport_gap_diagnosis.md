# Transport Gap Diagnosis

## Finding

The transport smoke failure is primarily **C. Source Quality Failure**, not a retriever failure.

The frozen corpus contains five chunks labelled `交通服务`, from only three sources:

- `STGPUB-0080`: a university-history office link page; it does not describe buses, routes, campus access, or transport services.
- `STGPUB-0081`: a student hardship-aid regulation; the only transport-related phrase is `交通补助`.
- `STGPUB-0082`: a research news article about a flexible visual sensing system; it is unrelated to campus transport.

None supplies adequate evidence for the frozen question “校园交通、校车和进出校路线怎么查询？”. Therefore changing retriever parameters cannot produce a complete answer from the current 238-document corpus.

## Failure taxonomy

- **A. Retriever Failure:** not established. No adequate positive source exists against which a miss can be judged.
- **B. Ranking Failure:** not the primary issue. A ranking improvement among the existing candidates would still surface irrelevant or insufficient evidence.
- **C. Source Quality Failure:** confirmed. The corpus lacks a genuine campus shuttle, campus transport, route, or access-service document, and the present category assignments contain obvious false positives.
- **D. Query Ambiguity:** secondary. The frozen question combines campus transport, shuttle service, and campus entry/exit routes; these could map to several service owners. Even after decomposition, the current corpus still lacks the required documents.

## Deferred gap list

The following sources are needed in a future, separately authorized expansion phase; this RAG V1 run does not crawl them:

1. Campus shuttle routes, stops, schedules, and service changes.
2. Campus gate access and visitor/vehicle entry rules.
3. Bicycle, parking, and internal transport service guidance.
4. Authoritative transport contact or service portal pages.
5. Correction or removal of the three current false-positive `交通服务` sources after Human Audit.

No retrieval score or evaluation query was altered to conceal this gap.
