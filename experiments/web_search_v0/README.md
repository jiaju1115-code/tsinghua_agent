# Web Search V0

Independent public-web retrieval and evidence pipeline for the Tsinghua AI project. It does not modify the local RAG corpus, answer generation, prompt experiments, Human Audit, or production.

## Setup

1. Create `web_search_v0/.env` with `TAVILY_API_KEY=` and provide the key locally, or set `TAVILY_API_KEY` in the environment.
2. Install `pip install -r requirements.txt`.
3. Run `python run_evaluation.py --query "清华大学 本科生 奖助学金 最新通知"`.

If no key is available, execution returns `TAVILY_API_KEY_NOT_CONFIGURED` without exposing secrets or a traceback.

## V0 behavior

- Rule-based routing: `CAMPUS_PUBLIC`, `ACADEMIC_RETRIEVAL`, `GENERAL_WEB`, `NO_WEB_NEEDED`, and `UNCERTAIN`.
- Campus queries search `tsinghua.edu.cn` first; broader search is only a fallback.
- Academic queries are rewritten into concept/theorem/formula/method searches; direct-answer-like pages are flagged and excluded from preferred evidence.
- Tavily search (top 5), ranked URL selection, extract (top 3), quality gate, compact evidence spans, and JSON cache are all separate stages.
- Only public pages are permitted. No campus portal login, WebVPN, account use, or automatic RAG ingestion occurs.
