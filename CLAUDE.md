# CLAUDE.md — Lang2Query

This file is the operating manual for any AI assistant (Claude Code, Cowork, etc.) working in this repository. Read it before making changes.

## 1. What this app is

Lang2Query (internally: Text2Query) converts a natural-language question into a correct SQL query against one of several documented databases, without the user needing to know the schema. It was built in a banking/fintech context where the databases involved are things like payment systems, user management, and inventory management — schema accuracy and query safety matter more than in a typical side project.

The core idea: instead of one LLM call given the whole schema and asked to "write SQL," the system funnels a query through a chain of specialized agents that each narrow the search space (which database → which tables → which columns → what query plan → generated SQL → validated SQL), backed by a RAG layer over hand-written schema documentation, with optional human-in-the-loop checkpoints before committing to a set of databases/tables.

**Current status: functional prototype, not production-ready.** It works as a personal/demo tool. It has not been hardened for multi-user concurrent load, does not have execution-time SQL safety guardrails, and has at least one confirmed broken import path (see Section 6). Treat every claim in the README about "production-ready" features skeptically until verified against the actual code.

## 2. Tech stack

**Backend** (`src/`): Python, FastAPI (REST + WebSocket), LangGraph (agent orchestration via `StateGraph`), Pydantic (typed state + structured LLM outputs), ChromaDB (vector store), `sentence-transformers` running BGE-M3 locally for embeddings. LLM providers are pluggable: Ollama (local), OpenAI/ChatGPT, NVIDIA, and local HF models — selected via `src/config.py` / env vars.

**Frontend** (`app/`): Next.js 15, React 19, TypeScript, Tailwind CSS, native WebSocket client for streaming workflow state.

## 3. Architecture (the part you must understand before editing agents or the workflow)

The pipeline is a LangGraph `StateGraph(AgentState)` defined in `src/workflow.py`. Nodes are agents; edges are Python routing functions that inspect state, not free-form LLM decisions:

```
START → router
router → metadata_agent (metadata questions: "list tables", "show columns")
       → database_identifier → [database_human_review] → table_identifier
         → [table_human_review] → column_identifier → schema_builder
         → query_planner → query_generator → query_validator
query_validator → END (valid)
                → database_identifier / table_identifier / query_planner (targeted retry, based on failure reason_code)
                → END (retries exhausted)
```

Key mechanisms — know these cold before touching workflow.py:

- **`AgentState`** (`src/models/models.py`) is the single typed contract every node reads and writes. Do not pass ad-hoc dicts between agents; extend `AgentState` with a new typed field instead.
- **Retries are two-tiered**: a global `retries_left` budget for the whole query, and a per-step `step_retries_left` dict. Any change to retry/routing logic must respect both, or you risk infinite loops or silent early termination.
- **Human-in-the-loop is a real graph node**, not a UI-only concept — it's a checkpoint enforced by LangGraph's `MemorySaver` checkpointer, which is also what makes WebSocket pause/resume possible (see `src/api/routes/query.py`).
- **Structured outputs**: agents never parse free-text JSON out of an LLM response. They pass a Pydantic `schema_class` (e.g. `RoutingInfo`, `QueryValidation`) into `BaseAgent.generate_with_llm()`, which constrains the LLM's output to that schema. If you add a new agent, define its output schema in `models/models.py` first, with `field_validator`s for anything with a constrained value set (see `QueryValidation.verdict`).
- **RAG retrieval is agentic, not naive**: `src/tools/retriever_tools.py` exposes retrieval as LangChain `@tool`-decorated functions (`semantic_search`, `search_by_database`, `search_by_table`, `complex_filter_search`, etc.) that the LLM itself chooses to call. Don't collapse this back into "always inject top-k chunks into every prompt" — the agentic pattern is intentional and better suited to progressively narrowing a large schema.
- **Ingestion is a separate, idempotent pipeline** (`src/retriever/create_sql_kb_embeddings.py` + `sql_kb_chunker.py`): markdown schema docs → hierarchical chunks (database/table/column, not fixed-size text splitting) → BGE-M3 embeddings → ChromaDB, skipping chunk IDs that already exist so re-ingestion after adding one doc doesn't re-embed everything.

## 4. Repository structure and what belongs where

```
src/
├── agents/          # One file per LangGraph node. Each agent: read AgentState in, return AgentResult (state_updates) out. No cross-agent side effects.
├── api/              # FastAPI routes + request/response mapping/serialization. HTTP/WS concerns only — no business logic here.
├── helper/           # Cross-cutting utilities used BY the workflow (logging, routing, state management) — logic here stays generic/reusable, not agent-specific.
├── lib/              # LLM provider abstraction (ModelWrapper + provider-specific implementations: ollama, chatgpt, nvidia). New provider = new file here, same interface.
├── models/            # Pydantic schemas: AgentState, per-agent output schemas, API request/response models. Single source of truth for shapes.
├── retriever/        # Ingestion (chunking + embedding) pipeline, plus the query-side retriever. [Renamed from `retreiver` — see Section 6.]
├── tools/            # LangChain @tool-decorated functions the LLM can call (retrieval, date utilities, etc.)
├── utils/            # Small stateless helpers (logging formatting, etc.)
└── workflow.py        # Graph wiring only: nodes, edges, routing. Business logic belongs in agents/helper, not here.

app/src/
├── components/       # One folder per component (ComponentName/ComponentName.tsx + index.ts barrel export)
├── hooks/             # Custom React hooks
├── lib/               # API client (api.ts) + WebSocket client (websocket.ts) — no business logic, just transport
└── types/             # Shared TypeScript types
```

**Separation-of-concerns rule for the backend**: an agent file (`agents/*.py`) should contain _decision logic_ — what to ask the LLM, how to interpret the structured response, what state to update. It should not contain generic plumbing (logging formatting, routing between nodes, model-provider details) — that belongs in `helper/`, `workflow.py`, and `lib/` respectively. `helper/workflow_helpers.py`'s `WorkflowLogger` / `WorkflowRouter` / `StateManager` split is the right pattern already in the codebase — follow it when adding new cross-cutting concerns instead of inlining them into an agent.

## 5. Code standards

Follow `CONTRIBUTING.md`'s baseline (PEP 8, Black, isort, flake8, type hints on all function signatures, Google-style docstrings, ESLint/Prettier on the frontend, functional React components with typed props). On top of that, for this project specifically:

- **DRY**: if the same retrieval call, prompt-formatting logic, or state-update pattern appears in more than one agent, extract it — into `agent_utils.py` (agent-facing helpers) or `helper/` (workflow-facing helpers). Do not copy-paste a file's contents into another file as a starting point for a new script (this is exactly how the Section 6 bug happened).
- **Abstraction boundaries must stay real, not just aspirational**: `ModelWrapper` exists so agents never talk to a specific provider's SDK directly — if you add code that imports `openai` or `ollama` directly inside an agent file, that's a boundary violation, fix it by extending `lib/`.
- **No new agent without a typed output schema.** Every agent's LLM call must go through `generate_with_llm(schema_class=...)`, never raw text parsing.
- **Naming must be exact and consistent** — Python's import system does not forgive typos or synonyms. Before renaming or creating a module, `grep` for every place that imports it. (See Section 6 for what happens when this isn't done.)
- **Errors are typed and logged, not swallowed.** Follow the existing pattern of `AgentUtils.create_error_result(str(e))` — don't add bare `except: pass` blocks (a couple already exist in the ingestion code as tech debt; don't add more).
- **Shared expensive resources (model instances, DB connections) are initialized once and injected**, not constructed inline per call. `Text2QueryWorkflow.__init__` does this correctly for the retriever; new code should follow that pattern, not the anti-pattern currently in `retriever_tools.py` (see Section 6).
- **Every new SQL-generation or SQL-execution code path must be read-only by design** until an explicit, reviewed decision is made to support writes. Given the fintech context, this is a hard rule, not a style preference.

## 6. Known issues / confirmed tech debt (fix these with understanding, not blind acceptance)

These are verified against the actual code, not guesses — treat this as the starting punch list. Items 1–4 and 6 below were fixed and each fix was verified by actually running the affected code path (not just re-reading the diff) — see the dated notes. Item 7 remains open.

1. ~~**Broken import path: `retreiver` vs `retriever`.**~~ **RESOLVED (2026-08-11).** Directory renamed `src/retreiver/` → `src/retriever/` via `git mv`; all imports across `workflow.py`, `tools/retriever_tools.py`, `agents/schema_builder.py`, `config.py` (`MD_DIRECTORY`), and the Makefile's `embeddings` target updated to match. Verified by importing every module on the request→response path in a real Python process — all resolved cleanly.
2. ~~**`src/retreiver/retrieve_sql_kb.py` does not define `SQLKnowledgeBaseRetriever`.**~~ **RESOLVED (2026-08-11).** `SQLKnowledgeBaseRetriever` implemented in `src/retriever/retrieve_sql_kb.py` with all methods `tools/retriever_tools.py` calls (`semantic_search`, `search_by_chunk_type`, `search_by_database`, `search_by_table`, `search_tables_in_databases`, `complex_filter_search`, `get_all_databases`, `count_databases`, `get_tables_in_database`, `count_tables_in_database`, `get_columns_by_table`). Search methods use `collection.query()` (ANN); enumeration methods (`get_all_databases`, `count_databases`, etc.) deliberately use `collection.get()` with a metadata `where` filter instead, since a top-k vector search offers no completeness guarantee for "list/count everything" questions. The BGE-M3 embedding function is shared (`retriever/embedding_utils.py`) between the ingestion and retrieval code rather than duplicated a third time. Verified by running `make embeddings` end-to-end against `src/retriever/input/*.md` (29 chunks embedded into ChromaDB with no errors) and by a live query that exercised `search_by_chunk_type`, `search_by_table`, and `get_columns_by_table` through the real agent pipeline. **Note**: this verification run surfaced one additional bug the earlier fix missed, since it had only been checked by grepping for the word "retreiver," not by executing the script — `create_sql_kb_embeddings.py` had `sys.path.insert(0, repo_root)` placed *after* its `from src.retriever...` imports instead of before, so `make embeddings` crashed immediately with `ModuleNotFoundError: No module named 'src'`. Fixed by reordering the two lines; no import path or naming changed.
3. ~~**Second naming mismatch**: `tools.retriever_tool` vs `retriever_tools.py`.~~ **RESOLVED (2026-08-11).** `tools/__init__.py` and `agents/human_in_the_loop.py` now import from `tools.retriever_tools` (plural). No remaining references to the singular form anywhere in the repo (confirmed by repo-wide grep).
4. ~~**`retriever_tools.py` recreates `SQLKnowledgeBaseRetriever` inside every tool function call.**~~ **RESOLVED (2026-08-11).** `retriever_tools.py` now exposes `make_retriever_tools(retriever)`, a factory that closes over one already-constructed retriever instance and returns the LangChain tool objects bound to it — `Text2QueryWorkflow.__init__` constructs the retriever once and passes it to every agent, matching the shared-instance pattern already used for the model wrapper. No tool function constructs its own retriever.
5. **No SQL safety guardrail.** ~~Resolved~~ **RESOLVED (2026-08-11).** Added `agents/sql_safety_guard.py`, a deterministic (non-LLM) node wired into `workflow.py` between `query_generator` and `query_validator`. It parses the generated SQL with `sqlglot` and rejects anything whose root statement isn't a read-only `SELECT`/`exp.Query` (covers CTEs, UNION/INTERSECT/EXCEPT) or that contains more than one statement (semicolon-stacked injection) — deliberately AST-based rather than keyword/regex matching, which is trivially defeated by casing, comments, or string literals containing blocked words. A safety failure is a hard stop (routed straight to `END`), not fed into the semantic retry loop, so an unsafe query can never be retried into passing. Verified by a live query that passed the guard, and by reading the routing logic in `workflow.py`'s `_route_after_sql_safety_guard`. **Still open, per the original note**: no read-only DB credentials at the infra level yet — this guard only prevents unsafe SQL from being *returned*, it doesn't (and can't, since nothing here executes SQL yet) enforce anything at a database connection level.
6. ~~**Blocking sync call inside an async WebSocket handler.**~~ **RESOLVED (2026-08-11).** `_process_workflow_stream` in `src/api/routes/query.py` now advances the workflow generator via `loop.run_in_executor(None, _next_state_or_sentinel, stream)` instead of calling `next(stream)` directly, so each agent's blocking LLM call runs on a worker thread instead of stalling the event loop. `_next_state_or_sentinel` exists to work around PEP 479 (asyncio Futures can't carry a raised `StopIteration`). Not independently load-tested under concurrent WebSocket connections — verified only by reading the code and by one successful non-concurrent query.
7. **No re-ranking or hybrid search** in the retrieval layer — pure dense vector similarity via ChromaDB. Acceptable for now given the small, well-structured knowledge base, but worth revisiting if the schema documentation grows significantly. **Still open.**

## 7. Production-readiness gaps (roadmap context for future feature work)

Not urgent, but relevant since the stated direction is evolving this into a real multi-user product: no auth/authorization layer, no per-user/tenant isolation of query history or database access, no rate limiting on LLM calls, no observability (structured tracing across the 8+ LLM calls per query, cost/latency dashboards), no automated test suite currently exercised (`CONTRIBUTING.md` documents a testing approach but coverage should be verified, not assumed), and secrets (`OPENAI_API_KEY` etc.) are currently plain config values rather than a secrets-management integration.

## 8. Working agreement for AI-assisted changes in this repo

- Before implementing a fix or feature, state in plain language what the change is and why it's the right approach — don't just produce a diff. The owner wants to understand every change well enough to explain it in an interview, not just approve it.
- Prefer small, scoped, reviewable changes over large rewrites, especially in `workflow.py` and `agents/` where a routing mistake can silently create infinite loops or dead-end states.
- When adding or renaming a module, grep the whole repo for every import of the old name before considering the change complete — the bugs in Section 6 exist because this wasn't done.
- Don't introduce a new LLM provider call, database connection, or model load outside the existing abstraction layers (`lib/ModelWrapper`, the shared retriever pattern) without a clear reason documented in the commit/PR description.
- Every fix to an item in Section 6 should come with an explanation of why the original code broke, not just the corrected code.

## 9. Common commands

```bash
make venv && make install && make download   # first-time backend setup
make embeddings                                # (re)build the vector KB from src/retriever/input/*.md
make run                                       # run the app (CLI entrypoint, src/main.py)
make dev                                       # run API + frontend together
cd app && npm run dev                          # frontend only
cd src && python -m api.app                    # backend API only
pytest                                         # backend tests
cd app && npm test                             # frontend tests
```
