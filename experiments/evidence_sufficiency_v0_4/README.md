# Evidence Sufficiency V0.4: Semantic Support Representation

`SEMANTIC_ENGINE_UNAVAILABLE`

V0.4-a was frozen after the V0.3 input/protocol audit passed. The selected sole local engine, `deepseek-r1:7b` served from local Ollama, returned HTTP 502 on the first frozen real-sample prompt. The fixed candidate supplies up to eight 480-character spans plus the required schema/prompt, exceeding the locally served model's 4096-token context.

The candidate was not changed after freeze. No semantic matrix, CV, or regression was run, because shrinking spans, changing the prompt, or replacing the model would violate the frozen single-candidate protocol.

This is a blocked calibration run, not a blind evaluation and not a negative model comparison.
