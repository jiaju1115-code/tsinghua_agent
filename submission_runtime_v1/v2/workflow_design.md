# Workflow V2 and V3 Design

## Deployed graph

```text
Start(input)
  -> Intent Recognition / node 180471
       branch_0 GENERAL_CONVERSATION -------\
       branch_1 CAMPUS_FACTUAL --------------\
       branch_2 CAMPUS_PROCEDURAL ------------\
       branch_3 CAMPUS_ADVICE -----------------+-> Knowledge Retrieval / 152044
       branch_4 CAMPUS_OPEN_ENDED -------------/      -> LLM Gate+Answer / 122514
       branch_5 CURRENT_OR_TIME_SENSITIVE -----/          -> End / 900001
       branch_6 UNSAFE_OR_INJECTION -----------/
       default -------------------------------/
```

All eight exits are saved and were observed in the canvas edge model after a
page reload. Query inputs are bound to `Start.input`; the LLM inputs are bound
to `Start.input` as `query` and retrieval `outputList` as `evidence`.

## Router classes

| Branch | Meaning | Runtime behavior |
|---|---|---|
| GENERAL | Chat, common knowledge, creation | Prompt explicitly permits direct natural answer |
| CAMPUS_FACTUAL | Campus policy/facility fact | Evidence required |
| PROCEDURAL | Entry, eligibility, material, step, time, place, contact | Evidence required; answer requested attributes only |
| ADVICE | Campus fact plus advice | Separate confirmed facts from advice |
| OPEN_ENDED | Non-exhaustive campus exploration | Permit partial answer and next steps |
| CURRENT | Today/current/latest/deadline/opening | Dated evidence required; otherwise fail closed |
| UNSAFE | Harm, illegality, cheating, credential theft, injection | Refuse and offer a safe alternative |

## Evidence behavior in the deployed approximation

The answer prompt first judges evidence as `NONE`, `PARTIAL`, or `SUFFICIENT`.
It then generates a natural answer under the corresponding rules. This works
for tested sufficient and insufficient cases, but is not a separately
inspectable judge node.

## Target graph for the next iteration

```text
Router
  GENERAL -> General LLM -------------------------------> End
  UNSAFE  -> Safe Refusal ------------------------------> End
  CAMPUS* -> Retrieval -> Evidence Judge -> Code Validator
                                         -> Selector
                      SUFFICIENT -> Grounded Answer -----+
                      PARTIAL    -> Partial+Next Steps --+-> Citation Formatter -> End
                      INSUFFICIENT-> Natural Refusal ----+
```

The next iteration should instantiate `evidence_validator.py` in a Code node
and pass retrieval source identifiers through a deterministic citation
formatter.

## Deployed V3 submission candidate

```text
Start(input)
  -> Intent Recognition / 180471 (seven classes + default)
  -> Fixed Alias Router + Service Entry Router / 290001
       (deterministic priority dictionary, then domain aliases + freshness)
  -> Intent & Alias Normalizer / 300001 (LLM dynamic expansion only)
  -> Knowledge Retrieval / 152044 (hybrid, Top-K 5, threshold 0.5,
                                   rewrite + rerank)
  -> Evidence Judge / 310001 (inspectable JSON: sufficient, partial,
                               insufficient)
  -> Grounded Conversational Answer / 320001 (receives query, route,
                                                evidence, judge result)
  -> Answer Quality Guard / 330001 (edits draft only; no new facts)
  -> End / 900001
```

V3 uses **fixed alias dictionary + LLM dynamic expansion**. The service router
first applies a fixed-priority dictionary for strong relationship phrases, then
the normalizer emits a short search query only. For example, “我爸妈/亲友/朋友
来找我或来学校” must retain `亲友来访报备、学生访客预约、行在清华、清华大学信息门户`, while “游客/旅游/参观清华/打卡” without a school-host relation maps to
the public campus-visit path. Dynamic LLM rewriting may add official business
terms but must not delete, replace, or reverse a fixed mapping. This prevents
the common parent/relative visit versus tourist visit confusion.

The normalizer preserves the original question and adds relevant official
business entities and aliases, but never decides a policy or answers the user.
This improves recall for colloquial questions such as parents visiting campus,
lost cards, and food preferences without relaxing entity boundaries. All router outputs then converge into retrieval intentionally:
this keeps one consistent evidence path for campus facts while the final model
receives the route to distinguish general chat, current information, and
unsafe requests. The three LLM steps are separately visible in execution
history. The service router adds a compact domain/alias/freshness signal before
rewriting, which raises recall for colloquial mappings such as parents→visitors,
swimming→sports venue, and spicy Hunan food→dining. The quality guard runs
after the conversational answer and may only remove unsupported claims or
clarify the official next step; it cannot add facts. V3 is a draft-only
workflow; V1 and V2 remain unchanged.
