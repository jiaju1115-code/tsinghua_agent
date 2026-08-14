# Academic retrieval analysis

Academic retrieval is judged by knowledge sufficiency: whether the evidence contains suitable definitions, formulas, theorems, conditions, derivations, or general methods for later independent reasoning. It is not an assertion that a model will solve the submitted problem correctly.

## Live evaluation result

Of the 10 frozen academic questions, 5 were routed to `ACADEMIC_RETRIEVAL` and produced retained knowledge evidence, yielding an Academic Knowledge Sufficiency Proxy of 50.0%. The other five were routed to `GENERAL_WEB` by the intentionally limited keyword router; this is a Router V0 limitation, not evidence of academic sufficiency.

The rewriter transformed the integration and Poisson prompts into method/formula queries rather than full answer searches. One of ten academic records raised `POSSIBLE_DIRECT_ANSWER_SOURCE`; it was not retained as preferred evidence, yielding a Direct-answer Leakage Rate of 10.0%.
