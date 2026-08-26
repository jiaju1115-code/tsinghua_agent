# Hugging Face Dataset Research

Six dataset cards were reviewed. No raw Hugging Face rows were downloaded.

| Dataset | License | Decision | Reason |
|---|---|---|---|
| [OpenAssistant/oasst1](https://huggingface.co/datasets/OpenAssistant/oasst1) | Apache-2.0 | Metadata-only recommendation | Human-generated/annotated instruction conversations; future small sample still needs filtering. |
| [Open-Orca/OpenOrca](https://huggingface.co/datasets/Open-Orca/OpenOrca) | MIT | Exclude | Very large synthetic corpus with provenance/contamination and scale concerns. |
| [MU-NLPC/Calc-math_qa](https://huggingface.co/datasets/MU-NLPC/Calc-math_qa) | Apache-2.0 | Future eval only | MathQA lineage creates benchmark leakage risk. |
| [allenai/math_qa](https://huggingface.co/datasets/allenai/math_qa) | Apache-2.0 | Future eval only | Established benchmark. |
| [openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k) | MIT | Future eval only | Established math benchmark. |
| [allenai/ai2_arc](https://huggingface.co/datasets/allenai/ai2_arc) | CC-BY-SA-4.0 | Future eval only | Benchmark leakage plus attribution/share-alike review. |

The future controlled general-data plan is 1,000–5,000 filtered, revision-pinned
examples. Any evaluation benchmark test split remains excluded from training.
