# Lang2Query

🤖 **Lang2Query** - Transform natural language into SQL queries with AI-powered precision using multi-agent workflows and intelligent knowledge base retrieval.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-15.5.4-black.svg)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agents-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/yourusername/lang2query.git
cd lang2query

# Copy environment file
cp env.example .env
# Edit .env with your OpenAI API key

# Start with Docker Compose
docker-compose up -d
```

**Web Interface**: Visit `http://localhost:3000` for the modern web UI  
**API Documentation**: Visit `http://localhost:8000/docs` for interactive API docs

### Option 2: Local Development

```bash
git clone https://github.com/yourusername/lang2query.git
cd lang2query

# Setup Python environment
make venv
source venv/bin/activate  # Windows: venv\Scripts\activate
make install
make download

# Start the application
make run
```

## ✨ Features

### 🤖 AI-Powered Query Generation

- **Multi-Agent Workflow**: Intelligent LangGraph agents for database identification, table selection, and SQL generation
- **Natural Language Processing**: Convert complex queries like "Show me all customers with pending verification" into precise SQL
- **Context-Aware**: Understands database schemas and relationships for accurate query generation

### 🧠 Knowledge Base & Retrieval

- **Vector Search**: ChromaDB-powered semantic search over database documentation
- **Schema Understanding**: Automatic database, table, and column identification
- **BGE-M3 Embeddings**: State-of-the-art multilingual embeddings for precise retrieval

### 🎨 Modern User Interface

- **Next.js Frontend**: React 19 with TypeScript for type-safe development
- **Real-time Updates**: Live WebSocket streaming of workflow progress
- **Interactive Mode**: Step-by-step query processing visualization
- **Responsive Design**: Clean, modern UI with Tailwind CSS

### ⚡ High-Performance Backend

- **FastAPI**: Async Python API with automatic OpenAPI documentation
- **WebSocket Support**: Real-time communication for live updates
- **Multiple LLM Providers**: Support for OpenAI, Ollama, NVIDIA, and local models
- **Modular Architecture**: Extensible agent system for custom workflows

## 📦 Installation

### Prerequisites

- **Python 3.8+** (recommended: Python 3.11+)
- **Node.js 18+** (for frontend)
- **Git**

### 🛠️ Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/lang2query.git
   cd lang2query
   ```

2. **Setup Python environment:**

   ```bash
   make venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   make install
   make download
   ```

3. **Setup frontend:**
   ```bash
   cd app
   npm install
   cd ..
   ```

### 🎯 Make Commands

| Command         | Description                                         |
| --------------- | --------------------------------------------------- |
| `make run`      | Start the complete application (backend + frontend) |
| `make install`  | Install Python dependencies                         |
| `make download` | Download required models                            |
| `make venv`     | Create Python virtual environment                   |
| `make clean`    | Clean up temporary files                            |
| `make test`     | Run test suite                                      |

### 🐳 Docker Commands

| Command                                          | Description                      |
| ------------------------------------------------ | -------------------------------- |
| `docker-compose up -d`                           | Start all services in background |
| `docker-compose down`                            | Stop all services                |
| `docker-compose logs -f`                         | View logs in real-time           |
| `docker-compose build`                           | Rebuild all images               |
| `docker-compose -f docker-compose.dev.yml up -d` | Start development environment    |

## 🚀 Usage

### 🌐 Web Interface (Recommended)

Start the complete application:

```bash
make run
```

This will start both the FastAPI backend (`http://localhost:8000`) and Next.js frontend (`http://localhost:3000`).

#### Web Interface Features:

- **🎯 Mode Selection**: Choose between Interactive and Normal processing modes
- **📡 Live Updates**: Real-time WebSocket streaming of workflow progress
- **🔍 Dynamic Discovery**: Watch as databases, tables, and columns are identified
- **📊 Clean Results**: View formatted SQL queries and detailed summaries
- **📱 Responsive Design**: Modern interface that works on all devices

#### Example Queries:

- "Show me all customers with pending verification"
- "List all payment transactions from last month"
- "Find products with low inventory levels"
- "Get user profiles created in the last 30 days"

### 💻 Development Mode

#### Backend Only:

```bash
cd src
python -m api.app
# or
uvicorn api.app:create_app --factory --host 0.0.0.0 --port 8000
```

#### Frontend Only:

```bash
cd app
npm run dev
```

### 🔧 CLI Mode

For command-line usage:

```bash
python src/main.py
```

## ⚙️ Configuration

### 🤖 LLM Provider Setup

Edit `src/config.py` to configure your preferred LLM provider:

#### OpenAI (ChatGPT) - Recommended

```python
PROVIDER = "chatgpt"
OPENAI_API_KEY = "your-api-key-here"  # Set via environment variable
OPENAI_MODEL = "gpt-4o"  # or gpt-4o-mini for cost efficiency
```

**Setup:**

1. Get API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Set environment variable:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

#### Ollama (Local)

```python
PROVIDER = "ollama"
OLLAMA_MODEL = "llama3.1"  # or any Ollama model
```

**Setup:**

1. Install [Ollama](https://ollama.ai)
2. Pull a model: `ollama pull llama3.1`

#### NVIDIA API

```python
PROVIDER = "nvidia"
NVIDIA_MODEL = "meta/llama3-70b"  # or other NVIDIA model
```

#### Local Models

```python
PROVIDER = "local"
# Models auto-downloaded via make download
```

### 🗄️ Knowledge Base Setup

1. **Add your database documentation** to `src/retreiver/input/` as markdown files
2. **Create embeddings:**
   ```bash
   python -m src.retreiver.create_sql_kb_embeddings --md-dir src/retreiver/input
   ```

## 🏗️ Architecture

### Backend (Python)

- **FastAPI**: High-performance async API
- **LangGraph**: Multi-agent workflow orchestration
- **ChromaDB**: Vector database for knowledge retrieval
- **BGE-M3**: Multilingual embeddings for semantic search

### Frontend (Next.js)

- **React 19**: Modern UI with TypeScript
- **Tailwind CSS**: Utility-first styling
- **WebSocket**: Real-time communication
- **Axios**: HTTP client for API calls

### Agents

- **Database Identifier**: Finds relevant databases
- **Table Identifier**: Selects appropriate tables
- **Column Identifier**: Identifies required columns
- **Query Generator**: Creates SQL queries
- **Query Validator**: Validates and optimizes queries

## 📁 Project Structure

```
lang2query/
├── app/                          # Next.js frontend
│   ├── src/
│   │   ├── components/           # React components
│   │   ├── lib/                  # Utilities and API client
│   │   └── types/                # TypeScript definitions
│   ├── Dockerfile                # Frontend production image
│   ├── Dockerfile.dev            # Frontend development image
│   └── package.json
├── src/                          # Python backend
│   ├── agents/                   # LangGraph agents
│   ├── api/                      # FastAPI application
│   ├── retreiver/                # Knowledge base system
│   ├── tools/                    # LangChain tools
│   └── workflow.py               # Main workflow
├── docker-compose.yml            # Production Docker setup
├── docker-compose.dev.yml        # Development Docker setup
├── Dockerfile                    # Backend production image
├── .dockerignore                 # Docker ignore file
├── env.example                   # Environment variables template
├── requirements.txt              # Python dependencies
└── Makefile                     # Build automation
```

## 🐳 Docker Setup

Lang2Query includes comprehensive Docker support for easy deployment and development.

### Quick Docker Start

```bash
# Clone and start with Docker
git clone https://github.com/yourusername/lang2query.git
cd lang2query
cp env.example .env
# Edit .env with your API keys
docker-compose up -d
```

### Docker Services

- **Backend**: FastAPI application with LangGraph agents
- **Frontend**: Next.js React application
- **Redis**: Caching and session storage
- **ChromaDB**: Vector database for knowledge retrieval

### Development with Docker

```bash
# Start development environment with hot reload
docker-compose -f docker-compose.dev.yml up -d
```

For detailed Docker documentation, see [DOCKER.md](DOCKER.md).

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://langchain.com) for the agent framework
- [FastAPI](https://fastapi.tiangolo.com) for the backend framework
- [Next.js](https://nextjs.org) for the frontend framework
- [ChromaDB](https://www.trychroma.com) for vector storage
- [BAAI](https://huggingface.co/BAAI/bge-m3) for the embedding model
