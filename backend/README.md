# Lang2Query Backend

FastAPI + LangGraph backend that turns a natural-language question into validated SQL. All Python code lives under `app/`. See the [root README](../README.md) for the product overview and the [architecture diagram](../README.md#how-it-works).

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agents-1C3C3C?style=flat-square&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-FF6F00?style=flat-square)](https://www.trychroma.com)

## Agents (`app/modules/query/agents/`)

Each file is one LangGraph node — decision logic only (what to ask the LLM, how to interpret the structured response, what state to update):

| Agent | Role |
| --- | --- |
| `router.py` | Routes each question to the metadata path or the full query pipeline |
| `metadata_agent.py` | Answers schema questions ("list tables", "show columns") directly |
| `database_identifier.py` | Identifies relevant database(s) |
| `table_identifier.py` | Selects relevant tables |
| `column_identifier.py` | Selects relevant columns |
| `schema_builder.py` | Assembles the narrowed schema context |
| `query_planner.py` | Plans the query before SQL is generated |
| `query_generator.py` | Generates the SQL |
| `query_validator.py` | Validates the SQL and decides whether to retry |
| `sql_safety_guard.py` | Enforces read-only query generation |
| `human_in_the_loop.py` | Pauses the graph for a human review checkpoint |

Cross-cutting workflow concerns (routing, retries, resume, display) live in `app/modules/query/workflow/`, not in the agent files — see [CLAUDE.md](../CLAUDE.md#3-architecture-the-part-you-must-understand-before-editing-agents-or-the-workflow).

## Quick Start

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install .                 # from backend/
python app/download.py        # download local models

cd app && python -m main      # or: uvicorn main:create_app --factory --host 0.0.0.0 --port 8000
```

API → `http://localhost:8000` · interactive docs → `http://localhost:8000/docs`

## Project Structure

```
app/
├── main.py       # create_app()/lifespan/CLI entrypoint
├── core/         # config.py (runtime configuration), logging.py
├── modules/
│   └── query/
│       ├── agents/    # LangGraph nodes (see table above)
│       └── workflow/  # Graph wiring, routing, retries, resume, display
├── ai/           # LLM provider abstraction (llm/) + RAG retrieval stack (chunking, embeddings, retriever, input/output/kb data)
├── workers/      # Ingestion CLI (document_ingestion.py)
├── api/          # FastAPI app, routes, request/response mapping
├── models/       # Pydantic schemas — AgentState + per-agent output schemas
├── tools/        # LangChain @tool retrieval functions
├── utils/        # Small stateless helpers
└── download.py   # Model downloader
```

## Configuration

Set via environment variables (see [env.example](../env.example)) or `app/core/config.py`:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o"          # or gpt-4o-mini
export OLLAMA_MODEL="llama3.1"        # if PROVIDER=ollama
export KB_DIRECTORY="./app/ai/kb"
export COLLECTION_NAME="sql_generation_kb"
```

## Knowledge Base

Add database documentation as markdown files under `app/ai/input/` (database → table → column sections), then build embeddings:

```bash
make embeddings   # from repo root
```

Re-ingestion is idempotent — chunk IDs that already exist in ChromaDB are skipped, so adding one new doc doesn't re-embed everything.

Agents access this knowledge base through ~13 LangChain-decorated retrieval tools in `app/tools/retriever_tools.py` (`semantic_search`, `search_by_database`, `search_by_table`, `complex_filter_search`, `get_columns_by_table`, `validate_database_exists`, ...) that the LLM itself chooses to call.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/query` | Process a natural-language query |
| `WS` | `/ws/query` | Real-time streaming of workflow progress |
| `GET` | `/health` | Health check |
| `GET` | `/workflow/steps` | List workflow step metadata |

## Testing

```bash
pytest                              # from backend/
pytest --cov=app --cov-report=html
```

Test coverage is currently thin — see [CLAUDE.md's production-readiness notes](../CLAUDE.md#6-production-readiness-gaps-roadmap-context-for-future-feature-work) before assuming a change is covered.

## License

MIT — see [LICENSE](../LICENSE).
