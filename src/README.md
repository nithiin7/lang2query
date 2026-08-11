# Lang2Query Backend

🚀 **Python Backend** for Lang2Query - A high-performance FastAPI application with multi-agent workflows for natural language to SQL conversion.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agents-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-purple.svg)](https://www.trychroma.com)

## 🏗️ Architecture

### Core Components

- **FastAPI Application** (`api/`): High-performance async API with WebSocket support
- **LangGraph Agents** (`agents/`): Multi-agent workflow for intelligent query processing
- **Knowledge Base** (`retriever/`): Vector search system with ChromaDB and BGE-M3 embeddings
- **LangChain Tools** (`tools/`): Specialized tools for database operations
- **Workflow Engine** (`workflow.py`): Orchestrates the complete query processing pipeline

### Agent System

The backend uses a sophisticated multi-agent system powered by LangGraph:

1. **Router Agent** (`router.py`): Routes queries to appropriate processing paths
2. **Database Identifier** (`database_identifier.py`): Identifies relevant databases
3. **Table Identifier** (`table_identifier.py`): Selects appropriate tables
4. **Column Identifier** (`column_identifier.py`): Identifies required columns
5. **Query Generator** (`query_generator.py`): Generates SQL queries
6. **Query Validator** (`query_validator.py`): Validates and optimizes queries
7. **Schema Builder** (`schema_builder.py`): Builds database schemas
8. **Metadata Agent** (`metadata_agent.py`): Handles metadata operations
9. **Human-in-the-Loop** (`human_in_the_loop.py`): Enables human validation

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ (recommended: Python 3.11+)
- Virtual environment (venv, conda, or pipenv)

### Installation

1. **Create virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Download models:**

   ```bash
   python download.py
   ```

4. **Start the server:**
   ```bash
   python -m api.app
   # or
   uvicorn api.app:create_app --factory --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

## 📁 Project Structure

```
src/
├── agents/                    # LangGraph agents
│   ├── __init__.py
│   ├── base_agent.py         # Base agent class
│   ├── router.py             # Query routing agent
│   ├── database_identifier.py # Database identification
│   ├── table_identifier.py   # Table selection
│   ├── column_identifier.py  # Column identification
│   ├── query_generator.py    # SQL generation
│   ├── query_validator.py    # Query validation
│   ├── schema_builder.py     # Schema building
│   ├── metadata_agent.py     # Metadata handling
│   ├── human_in_the_loop.py  # Human validation
│   └── agent_utils.py        # Agent utilities
├── api/                      # FastAPI application
│   ├── __init__.py
│   ├── app.py               # Main FastAPI app
│   ├── mapping.py           # Data mapping
│   ├── serialization.py     # Data serialization
│   └── routes/              # API routes
│       ├── __init__.py
│       ├── query.py         # Query endpoints
│       └── system.py        # System endpoints
├── retriever/               # Knowledge base system
│   ├── __init__.py
│   ├── create_sql_kb_embeddings.py  # Embedding creation
│   ├── retrieve_sql_kb.py           # Knowledge retrieval
│   ├── sql_kb_chunker.py            # Document chunking
│   ├── input/               # Sample database docs
│   └── output/              # Generated chunks
├── tools/                   # LangChain tools
│   ├── __init__.py
│   ├── retriever_tools.py   # Knowledge base tools
│   └── date_tools.py        # Date manipulation tools
├── lib/                     # Core libraries
│   ├── __init__.py
│   ├── agent.py            # Agent utilities
│   ├── chatgpt.py          # OpenAI integration
│   ├── langchain.py        # LangChain utilities
│   └── nvidia.py           # NVIDIA API integration
├── utils/                   # Utilities
│   ├── __init__.py
│   ├── chunk_parsers.py    # Chunk parsing
│   └── logging.py          # Logging configuration
├── models/                  # Model definitions
│   ├── __init__.py
│   └── models.py           # Pydantic models
├── config.py               # Configuration
├── download.py             # Model downloader
├── main.py                 # CLI entry point
└── workflow.py             # Main workflow orchestration
```

## 🔧 Configuration

### Environment Variables

```bash
# OpenAI Configuration
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_MODEL="gpt-4o"  # or gpt-4o-mini

# Ollama Configuration
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="llama3.1"

# NVIDIA Configuration
export NVIDIA_API_KEY="your-nvidia-api-key"
export NVIDIA_BASE_URL="https://api.nvcf.nvidia.com/v1"

# Database Configuration
export DATABASE_URL="postgresql://user:pass@localhost/db"
export KB_DIRECTORY="./src/kb"
export COLLECTION_NAME="sql_generation_kb"
```

### Configuration File (`config.py`)

```python
# LLM Provider
PROVIDER = "chatgpt"  # "chatgpt", "ollama", "nvidia", "local"

# Model Settings
OPENAI_MODEL = "gpt-4o"
OLLAMA_MODEL = "llama3.1"
NVIDIA_MODEL = "meta/llama3-70b"

# Knowledge Base
KB_DIRECTORY = "./src/kb"
COLLECTION_NAME = "sql_generation_kb"

# API Settings
API_HOST = "0.0.0.0"
API_PORT = 8000
```

## 🧠 Knowledge Base System

### Adding Database Documentation

1. **Create markdown files** in `retriever/input/` following this format:

```markdown
# Workbook: YourDatabase.xlsx

## Sheet: Database Schema

### Database Info

- System Name:: Your System
- Module Name:: Your Module
- Db Name:: your_database
- Purpose:: Database purpose
- Status:: Active

### Table Name

| Attribute  | Value         |
| ---------- | ------------- |
| Table Name | table_name    |
| Purpose    | Table purpose |

#### Columns

| Column  | Data Type   | Key | Null | Description | Category |
| ------- | ----------- | --- | ---- | ----------- | -------- |
| column1 | VARCHAR(50) | PRI | NO   | Description | Primary  |
| column2 | INT         | MUL | YES  | Description | Foreign  |
```

2. **Generate embeddings:**
   ```bash
   python -m retriever.create_sql_kb_embeddings --md-dir retriever/input
   ```

### Knowledge Base Tools

The system provides several LangChain tools for knowledge retrieval:

- `semantic_search`: General semantic search across all databases
- `search_by_database`: Search within specific databases
- `search_by_table`: Search within specific tables
- `get_all_databases`: List all available databases
- `get_tables_in_database`: List tables in a database
- `get_columns_by_table`: Get detailed column information
- `validate_database_exists`: Validate database existence
- `validate_table_exists`: Validate table existence

## 🔌 API Endpoints

### Query Processing

- `POST /api/query/process` - Process natural language query
- `POST /api/query/stream` - Stream query processing (WebSocket)
- `GET /api/query/history` - Get query history

### System

- `GET /api/system/status` - Get system status
- `GET /api/system/health` - Health check
- `GET /api/system/databases` - List available databases

### WebSocket

- `WS /ws/query` - Real-time query processing updates

## 🧪 Testing

### Run Tests

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_agents.py

# Run with coverage
python -m pytest --cov=src tests/
```

### Test Structure

```
tests/
├── test_agents/          # Agent tests
├── test_api/            # API endpoint tests
├── test_retriever/      # Knowledge base tests
├── test_tools/          # Tool tests
└── conftest.py          # Test configuration
```

## 🚀 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
EXPOSE 8000

CMD ["uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Setup

1. **Use a production ASGI server:**

   ```bash
   pip install gunicorn uvicorn[standard]
   gunicorn src.api.app:create_app --factory -w 4 -k uvicorn.workers.UvicornWorker
   ```

2. **Configure reverse proxy** (nginx):

   ```nginx
   location / {
       proxy_pass http://localhost:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

3. **Set up monitoring** with tools like:
   - Prometheus + Grafana
   - ELK Stack
   - Sentry for error tracking

## 🔍 Debugging

### Logging

The system uses structured logging with different levels:

```python
import logging
from utils.logging import setup_logging

# Setup logging
setup_logging(level=logging.DEBUG)

# Use in code
logger = logging.getLogger(__name__)
logger.info("Processing query: %s", query)
```

### Common Issues

1. **Model not found**: Ensure models are downloaded via `python download.py`
2. **Knowledge base empty**: Run embedding creation for your database docs
3. **API key issues**: Check environment variables and configuration
4. **Memory issues**: Reduce batch sizes or use smaller models

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `python -m pytest`
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.
