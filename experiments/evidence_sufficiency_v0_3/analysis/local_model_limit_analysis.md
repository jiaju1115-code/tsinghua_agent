# Local-model semantic-limit analysis

`LOCAL_MODEL_CAPABILITY_LIMIT_SUSPECTED: NO`

No local Qwen or other local language model was used in this V0.3 candidate. The classifier is an offline Random Forest over generic length, overlap, point-count, requested-attribute, and evidence-shape features. Consequently, missed semantic support cannot be attributed to a local LLM capability ceiling.

There is a stable semantic-support weakness—17 sufficient examples are missed across Real and Synthetic CV—but the immediate cause is the proxy feature/rule design and three-class calibration. The prerequisite for recommending a model ablation is not met: the rule/decomposition layer is not yet clearly stable. No model ablation is recommended at this stage.
