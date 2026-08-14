# Web Search V0 vs Academic Retrieval V0.1

| Measure | Web Search V0 | V0.1 Frozen Academic 10 |
|---|---:|---:|
| Academic Router Accuracy | 50% | 100% |
| Academic Knowledge Sufficiency | 50% | 100% |
| Direct-answer Leakage | 10% | 0% |

The V0 shortfall was primarily a Router V0 error: five academic prompts were routed to General Web before academic planning could run. V0.1 fixes those five without changing the frozen questions. The 30-question routing regression is 100%, so Campus and General routing did not regress.

The independent Shadow Set is weaker: router accuracy is 66.67%, retrieval-level atom coverage is 100%, and end-to-end Academic Knowledge Sufficiency is 66.67%. This demonstrates that the current dictionary/structure Router is not yet general enough for Integration V0.
