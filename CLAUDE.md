# CLAUDE.md — Lang2Query

This file is the operating manual for any AI assistant (Claude Code, Cowork, etc.) working in this repository. Read it before making changes.

## 1. What this app is

Lang2Query (internally: Text2Query) converts a natural-language question into a correct SQL query against one of several documented databases, without the user needing to know the schema. It was built in a banking/fintech context where the databases involved are things like payment systems, user management, and inventory management — schema accuracy and query safety matter more than in a typical side project.

The core idea: instead of one LLM call given the whole schema and asked to "write SQL," the system funnels a query through a chain of specialized agents that each narrow the search space (which database → which tables → which columns → what query plan → generated SQL → validated SQL), backed by a RAG layer over hand-written schema documentation, with optional human-in-the-loop checkpoints before committing to a set of databases/tables.

**Current status: functional prototype, not production-ready.** It works as a personal/demo tool. It has not been hardened for multi-user concurrent load, does not have execution-time SQL safety guardrails, and has at least one confirmed broken import path (see Section 6). Treat every claim in the README about "production-ready" features skeptically until verified against the actual code.

## 2. Tech stack

**Backend** (`backend/app/`): Python, FastAPI (REST + WebSocket), LangGraph (agent orchestration via `StateGraph`), Pydantic (typed state + structured LLM outputs), ChromaDB (vector store), `sentence-transformers` running BGE-M3 locally for embeddings. LLM providers are pluggable: Ollama (local), OpenAI/ChatGPT, and local HF models — selected via `backend/app/core/config.py` / env vars.

**Frontend** (`frontend/`): Next.js 15, React 19, TypeScript, Tailwind CSS, native WebSocket client for streaming workflow state.

## 3. Architecture (the part you must understand before editing agents or the workflow)

The pipeline is a LangGraph `StateGraph(AgentState)` defined in `backend/app/modules/query/workflow/graph.py`. Nodes are agents; edges are Python routing functions that inspect state, not free-form LLM decisions:

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

Key mechanisms — know these cold before touching the `modules/query/workflow/` package:

- **`AgentState`** (`backend/app/models/models.py`) is the single typed contract every node reads and writes. Do not pass ad-hoc dicts between agents; extend `AgentState` with a new typed field instead.
- **Retries are two-tiered**: a global `retries_left` budget for the whole query, and a per-step `step_retries_left` dict. Any change to retry/routing logic must respect both, or you risk infinite loops or silent early termination.
- **Human-in-the-loop is a real graph node**, not a UI-only concept — it's a checkpoint enforced by LangGraph's `MemorySaver` checkpointer, which is also what makes WebSocket pause/resume possible (see `backend/app/api/routes/query.py`).
- **Structured outputs**: agents never parse free-text JSON out of an LLM response. They pass a Pydantic `schema_class` (e.g. `RoutingInfo`, `QueryValidation`) into `BaseAgent.generate_with_llm()`, which constrains the LLM's output to that schema. If you add a new agent, define its output schema in `models/models.py` first, with `field_validator`s for anything with a constrained value set (see `QueryValidation.verdict`).
- **RAG retrieval is agentic, not naive**: `backend/app/tools/retriever_tools.py` exposes retrieval as LangChain `@tool`-decorated functions (`semantic_search`, `search_by_database`, `search_by_table`, `complex_filter_search`, etc.) that the LLM itself chooses to call. Don't collapse this back into "always inject top-k chunks into every prompt" — the agentic pattern is intentional and better suited to progressively narrowing a large schema.
- **Ingestion is a separate, idempotent pipeline** (`backend/app/workers/create_sql_kb_embeddings.py` + `backend/app/ai/sql_kb_chunker.py`): markdown schema docs → hierarchical chunks (database/table/column, not fixed-size text splitting) → BGE-M3 embeddings → ChromaDB, skipping chunk IDs that already exist so re-ingestion after adding one doc doesn't re-embed everything.

## 4. Repository structure and what belongs where

```
backend/                        # Python, FastAPI
├── app/
│   ├── main.py       # create_app()/lifespan/CLI entrypoint. Run with `python -m main` from inside app/.
│   ├── core/          # Cross-cutting: config.py (paths/provider/model settings), logging.py (colored console logging helpers).
│   ├── modules/
│   │   └── query/     # The NL-to-SQL pipeline — the app's one real "module" today.
│   │       ├── agents/    # One file per LangGraph node. Each agent: read AgentState in, return AgentResult (state_updates) out. No cross-agent side effects.
│   │       └── workflow/  # Everything workflow-orchestration related. graph.py: Text2QueryWorkflow — graph wiring (nodes/edges) + public API only, no business logic. router.py: WorkflowRouter — all routing/retry decisions. resume.py: ResumeRouter — resolves which node a paused/resumed run continues from. display.py: WorkflowLogger/WorkflowDisplay — step-name-to-display-text mapping and result logging. state.py: StateManager — state-update helpers. Nothing outside this package should import from `workflow.graph` directly; import `Text2QueryWorkflow` from `modules.query.workflow`.
│   ├── ai/            # LLM provider abstraction + the RAG retrieval stack.
│   │   ├── llm/            # ModelWrapper (agent.py) + provider-specific implementations: ollama.py, chatgpt.py. New provider = new file here, same interface.
│   │   ├── embedding_utils.py  # BGE-M3 embedding function for ChromaDB.
│   │   ├── sql_kb_chunker.py   # Hierarchical (database/table/column) markdown chunker used by ingestion.
│   │   ├── retrieve_sql_kb.py  # Query-side retriever (SQLKnowledgeBaseRetriever) used by schema_builder and the retriever tools.
│   │   ├── input/          # Hand-written markdown schema docs (tracked in git) — source of truth for the KB.
│   │   ├── output/         # Generated per-database chunk JSON (mostly gitignored cache).
│   │   └── kb/              # ChromaDB persistence directory (gitignored).
│   ├── workers/        # Offline/background jobs. create_sql_kb_embeddings.py: the idempotent ingestion CLI (`make embeddings`).
│   ├── api/            # FastAPI routes + request/response mapping/serialization. HTTP/WS concerns only — no business logic here.
│   ├── models/          # Pydantic schemas: AgentState, per-agent output schemas, API request/response models. Single source of truth for shapes.
│   ├── tools/           # LangChain @tool-decorated functions the LLM can call (retrieval, date utilities, etc.)
│   └── utils/            # Small stateless helpers not tied to core/ (e.g. chunk_parsers.py).
├── tests/
└── pyproject.toml

frontend/                        # Next.js
├── src/
│   ├── app/
│   │   ├── page.tsx              # "/" — redirects to /chat
│   │   ├── layout.tsx            # Root layout (Toaster, globals.css)
│   │   └── (dashboard)/
│   │       └── chat/page.tsx     # "/chat" — the query UI (Header + Sidebar + ChatContainer)
│   ├── components/
│   │   ├── chat/       # One folder per component (ComponentName/ComponentName.tsx + index.ts barrel export). Chat-domain: ChatContainer, ChatMessage, QueryInput, ResultsDisplay, SelectionReviewCard, Sidebar, StatusPanel.
│   │   ├── ui/         # Generic, non-chat-specific presentational components (e.g. MarkdownRenderer).
│   │   └── Header/     # App-wide chrome shared across (future) dashboard pages — not chat-specific, so it stays outside both chat/ and ui/.
│   ├── hooks/          # Custom React hooks
│   ├── lib/            # API client (api.ts) + WebSocket client (websocket.ts) — no business logic, just transport
│   ├── types/          # Shared TypeScript types
│   └── styles/         # globals.css
└── public/
```

`modules/`, `ai/`, `core/`, and `workers/` mirror a generic RAG-app template adopted ahead of upcoming features; `db/` and `core/security.py` from that template are deliberately not present yet — there's no relational store or auth code to justify them, and empty stub packages aren't worth the confusion. Add `modules/{auth,users,...}` siblings to `modules/query/` as those features land, rather than restructuring again. Same idea on the frontend: `(dashboard)/chat/` exists because the chat page is real; sibling route groups like `(auth)/login` or `(dashboard)/documents` aren't stubbed in until there's actual auth/documents code behind them.

**Separation-of-concerns rule for the backend**: an agent file (`agents/*.py`) should contain _decision logic_ — what to ask the LLM, how to interpret the structured response, what state to update. It should not contain generic plumbing (logging formatting, routing between nodes, model-provider details) — that belongs in `workflow/` (routing, resume, display, state) and `ai/llm/` (model-provider details) respectively. The `workflow/` package's `router.py` / `resume.py` / `display.py` / `state.py` split is the right pattern already in the codebase — follow it when adding new cross-cutting workflow concerns instead of inlining them into an agent or into `workflow/graph.py`.

## 5. Code standards

Follow `CONTRIBUTING.md`'s baseline (PEP 8, Black, isort, flake8, type hints on all function signatures, Google-style docstrings, ESLint/Prettier on the frontend, functional React components with typed props). On top of that, for this project specifically:

- **DRY**: if the same retrieval call, prompt-formatting logic, or state-update pattern appears in more than one agent, extract it — into `agent_utils.py` (agent-facing helpers) or `workflow/` (workflow-facing helpers: routing, resume, display, state). Do not copy-paste a file's contents into another file as a starting point for a new script (this is exactly how the Section 6 bug happened).
- **Abstraction boundaries must stay real, not just aspirational**: `ModelWrapper` exists so agents never talk to a specific provider's SDK directly — if you add code that imports `openai` or `ollama` directly inside an agent file, that's a boundary violation, fix it by extending `ai/llm/`.
- **No new agent without a typed output schema.** Every agent's LLM call must go through `generate_with_llm(schema_class=...)`, never raw text parsing.
- **Naming must be exact and consistent** — Python's import system does not forgive typos or synonyms. Before renaming or creating a module, `grep` for every place that imports it. (See Section 6 for what happens when this isn't done.)
- **Errors are typed and logged, not swallowed.** Follow the existing pattern of `AgentUtils.create_error_result(str(e))` — don't add bare `except: pass` blocks (a couple already exist in the ingestion code as tech debt; don't add more).
- **Shared expensive resources (model instances, DB connections) are initialized once and injected**, not constructed inline per call. `Text2QueryWorkflow.__init__` does this correctly for the retriever; new code should follow that pattern, not the anti-pattern currently in `retriever_tools.py` (see Section 6).
- **Every new SQL-generation or SQL-execution code path must be read-only by design** until an explicit, reviewed decision is made to support writes. Given the fintech context, this is a hard rule, not a style preference.

## 6. Production-readiness gaps (roadmap context for future feature work)

Not urgent, but relevant since the stated direction is evolving this into a real multi-user product: no auth/authorization layer, no per-user/tenant isolation of query history or database access, no rate limiting on LLM calls, no observability (structured tracing across the 8+ LLM calls per query, cost/latency dashboards), no automated test suite currently exercised (`CONTRIBUTING.md` documents a testing approach but coverage should be verified, not assumed), and secrets (`OPENAI_API_KEY` etc.) are currently plain config values rather than a secrets-management integration.

## 7. Working agreement for AI-assisted changes in this repo

- Before implementing a fix or feature, state in plain language what the change is and why it's the right approach — don't just produce a diff. The owner wants to understand every change well enough to explain it in an interview, not just approve it.
- Prefer small, scoped, reviewable changes over large rewrites, especially in `workflow/` and `agents/` where a routing mistake can silently create infinite loops or dead-end states.
- When adding or renaming a module, grep the whole repo for every import of the old name before considering the change complete — the bugs in Section 6 exist because this wasn't done.
- Don't introduce a new LLM provider call, database connection, or model load outside the existing abstraction layers (`ai/llm.ModelWrapper`, the shared retriever pattern) without a clear reason documented in the commit/PR description.
- Every fix to an item in Section 6 should come with an explanation of why the original code broke, not just the corrected code.

## 9. Common commands

```bash
make venv && make install && make download   # first-time backend setup
make embeddings                                # (re)build the vector KB from backend/app/ai/input/*.md
make dev                                       # run API + frontend together
cd frontend && npm run dev                     # frontend only
cd backend/app && python -m main               # backend API only
cd backend && pytest                           # backend tests
cd frontend && npm test                        # frontend tests
```
