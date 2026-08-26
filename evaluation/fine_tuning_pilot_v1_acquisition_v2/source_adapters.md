# Source adapters

All records retain `metadata.raw_fields`, source row identity, fixed Stage 1 revision, config and split. Adapters are therefore reversible. Nemotron/Tulu select user/assistant messages; Dolly maps instruction/context/response; SQuAD selects first gold answer; RuleTaker retains final label only; bAbI expands question turns; coding retains source tests.
