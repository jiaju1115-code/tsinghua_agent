# Migration Log

## 2026-08-17

### Workflow isolation

- **Change:** Created `TEST_SUBMISSION_V1_WORKFLOW_V2`.
- **Reason:** Preserve the existing V1 workflow and Frozen runtime.
- **Result:** New workflow ID `7674999313944018944`; V1 unchanged.
- **Decision:** KEEP.

### Seven-class router

- **Change:** Added an Intent Recognition node with seven explicit classes and
  a default exit; bound query to `Start.input`.
- **Reason:** Avoid treating every request as identical KB QA.
- **Result:** All exits saved and completed in representative live runs.
- **Decision:** KEEP.

### Shared retrieval chain

- **Change:** Converged all exits on one hybrid retrieval node and a combined
  evidence-gated LLM answer node.
- **Reason:** Platform UI made a full split judge/validator/selector graph
  expensive to construct in this iteration; shared chain was the closest
  executable approximation.
- **Result:** End-to-end runtime works, but general requests still incur
  retrieval latency and the judge is not independently inspectable.
- **Decision:** TEMPORARY; replace with split branches next.

### LLM parameter binding

- **Change:** Renamed selected inputs from their auto-generated names `input`
  and `outputList` to `query` and `evidence`, then committed on blur.
- **Reason:** Mustache variables were empty in the first diagnostic run.
- **Result:** Names persisted after reload and grounded answers were produced.
- **Decision:** KEEP.

### General conversation exemption

- **Change:** Added an explicit rule allowing clearly non-campus chat and
  creation to answer without evidence.
- **Reason:** Initial general test produced a mechanical missing-KB refusal.
- **Result:** Same cold-joke query returned a natural concise answer.
- **Decision:** KEEP until General LLM gets a dedicated branch.

### Knowledge expansion

- **Change:** Added 13 approved public canonical files, one at a time.
- **Reason:** V1's seven documents could not cover core campus intents.
- **Result:** 7 -> 20 documents; 11 -> 45 segments; 6.45 -> 28.42 KB.
- **Decision:** KEEP.

### Retriever settings

- **Change:** No parameter change; kept hybrid, Top-K 5, threshold 0.5,
  query rewrite and rerank.
- **Reason:** Expansion and routing correctness were higher priority, and the
  representative queries retrieved the expected new source without relaxing
  the threshold.
- **Result:** Correct new-source hit observed; latency remains variable.
- **Decision:** KEEP pending controlled Top-K 3/5/8 experiment.

### Citation handling

- **Change:** Prohibited invented sources and used a generic fragment fallback
  when title/URL was unavailable.
- **Reason:** Current outputList did not reliably expose citation metadata to
  the prompt.
- **Result:** No fabricated links observed, but strict source-level citation
  remains incomplete.
- **Decision:** TEMPORARY.

### Partial and advice-oriented live check

- **Change:** Ran a mixed fact/current request and an aid-preparation request
  after the final prompt and KB expansion were saved.
- **Reason:** Distinguish implemented behavior from prompt-only intent.
- **Result:** The mixed national-scholarship query failed closed without
  confusing scholarship with aid or inventing a current deadline. The aid
  query returned supported eligibility/process facts, explicitly identified
  the missing materials detail, and provided responsible next-step channels.
- **Decision:** KEEP behavior; split the judge into an inspectable node next.

## 2026-08-18

### Isolated V3 candidate

- **Change:** Created `TEST_SUBMISSION_V3_READY` (`7675204261298307072`) in
  the existing draft project; V1 and V2 were not edited.
- **Reason:** Turn the V2 combined gate/answer approximation into an
  inspectable submission candidate without touching the frozen baseline.
- **Result:** Six nodes and twelve saved edges: router -> retrieval -> judge
  -> answer -> end.
- **Decision:** KEEP as draft; do not publish or submit.

### Independent evidence and conversational answer

- **Change:** Added a low-temperature Evidence Judge that outputs compact
  SUFFICIENT/PARTIAL/INSUFFICIENT JSON; passed its result and the router class
  into a separate Grounded Conversational Answer node.
- **Reason:** Ensure campus claims are gated by evidence while ordinary chat
  remains natural and useful.
- **Result:** The judge and answer were independently visible in platform
  execution history for the in-study-certificate procedure.
- **Decision:** KEEP.

### Live V3 regression

- **Change:** Ran six representative calls against the saved draft workflow.
- **Result:** Procedure answer tailored to a graduate student; a current
  library-hours request failed closed; aid preparation returned supported
  eligibility plus a missing-material caveat; credential theft and an explicit
  fabrication/injection request were refused; graduate degree-proof procedure
  retrieved the new source and returned its material, location and contact.
- **Decision:** KEEP; evidence is recorded in `regression/test_results_v3.md`.

### Retrieval focus and concise answer policy

- **Change:** Reduced V3 retrieval from Top-K 5 to Top-K 3 and constrained
  evidence JSON / final response length; passed `classificationId` directly
  into the final answer prompt.
- **Reason:** The first broad procedure answer over-expanded unrelated
  exceptions even though retrieval was correct.
- **Result:** A known-graduate query produced a two-step, identity-specific
  response with only relevant special cases.
- **Decision:** KEEP pending a larger controlled evaluation.

### Synonym retrieval hotfix for reported failures

- **Change:** Added public-source, alias-rich knowledge documents for
  campus public-area visits by parents/relatives and for lost campus-card
  loss reporting/replacement. Added a strict entity-distinction rule to the
  final answer prompt: public-campus admission, student-dorm visits, campus
  cards, and graduation/degree certificates cannot substitute for one
  another.
- **Reason:** A live report showed that “爸妈来学校” retrieved student-dorm
  visitor rules, while “校园卡丢了，怎么补办” had no relevant source at all.
- **Result:** The visitor question retrieved the public real-name reservation
  guidance and answered with the official reservation channels, latest-notice
  caveat, and consultation line—without mentioning dorm hours. The card
  question retrieved loss-reporting, two self-service replacement locations,
  official site, and service contacts; the judge returned `SUFFICIENT` for
  both cases.
- **Decision:** KEEP. Do not relax the retriever threshold merely to mask
  coverage gaps; expand canonical source coverage and aliases first.

### Local approved-knowledge synchronization and alias-normalizer

- **Change:** Uploaded all 30 local, human-approved public-source documents
  to `TEST_SUBMISSION_V1_KB`; added a source-bounded dining preference card;
  inserted `Intent & Alias Normalizer` (node `300001`) between router and
  retrieval; raised V3 Top-K from 3 to 5 while retaining rewrite and rerank.
- **Reason:** The project had only 20 original platform documents despite a
  substantially larger local reviewed corpus. Direct retrieval also lacked a
  distinct step to map colloquial relationships and preferences to the terms
  used by official source material.
- **Result:** Platform API reports 54 documents total, 53 usable; all 30
  synchronized documents parsed successfully. Live runs showed parents map to
  relatives/visitors/appointment, a Hunan-flavour request maps to
  Sichuan-Hunan dining evidence, and a campus-bus query maps to the local
  transportation source and `清华巴士` mini-program.
- **Decision:** KEEP. The judge now treats subjective taste/price as
  PARTIAL unless reliable evidence supports them, so a candidate restaurant
  can be recommended without fabricating a universal “good and cheap” claim.

### Web-search fallback readiness

- **Change:** Audited the platform plugin marketplace and documented the
  knowledge-first fallback design.
- **Result:** `博查搜索` is available in the marketplace but this account is
  marked `未授权`; the project contains no web-search plugin yet.
- **Decision:** Do not claim online search is enabled and do not authorize a
  third party on the user's behalf. After user authorization, add the plugin
  only to the Evidence Judge `INSUFFICIENT` / strongly time-sensitive branch,
  then filter to official sources before answering.
