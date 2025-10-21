# Text2Query

Natural language to SQL query generator using LangGraph agents and knowledge base retrieval.

## Quick Start

```bash
git clone <repository-url>
cd Text2Query

make venv
source venv/bin/activate  # Windows: venv\Scripts\activate
make install
make download
make run
```

## Features

- **Multi-Agent System**: LangGraph workflow with intelligent query routing
- **Knowledge Base**: Vector search over documentation using ChromaDB
- **Interactive CLI**: Easy-to-use command-line interface
- **Modern Web UI**: Next.js frontend with real-time WebSocket updates
- **Live Status Updates**: Real-time workflow progress with WebSocket streaming
- **FastAPI Backend**: High-performance async API with WebSocket support
- **Makefile Automation**: Simple setup and execution commands

## Installation

### Requirements

- Python 3.8+
- Git

### Setup

```bash
git clone <repository-url>
cd Text2Query

make venv
source venv/bin/activate  # Windows: venv\Scripts\activate
make install
make download
```

### Make Commands

```bash
make run       # Run the application
make download  # Download models
make install   # Install dependencies
make venv      # Create virtual environment
make clean     # Clean up files
```

## Usage

### Interactive CLI Mode

```bash
make run
```

### Web Interface (Next.js + FastAPI)

#### Backend (FastAPI)

```bash
cd src
python -m api.app
# or
uvicorn api.app:create_app --factory --host 0.0.0.0 --port 8000
```

#### Frontend (Next.js)

```bash
cd app
npm install
npm run dev
```

Access the modern web interface at `http://localhost:3000` with:

- **Mode Selection**: Choose between Interactive and Normal processing modes
- **Live WebSocket Updates**: Real-time workflow progress with live status updates
- **Dynamic State Display**: See databases, tables, and columns as they're identified
- **Clean Results Display**: View formatted SQL queries and workflow summaries
- **Responsive UI**: Modern interface with real-time progress indicators

Enter natural language queries like:

- "Show me all customers with pending KYC"
- "List all tables in the database"
- "Find transactions from last month"

### Configuration

Edit `src/config.py` to change:

- `PROVIDER`: "ollama", "nvidia", or "local"
- `OLLAMA_MODEL`: Model name for Ollama
- `NVIDIA_MODEL`: Model for NVIDIA API

## Requirements

- Python 3.8+
- Dependencies: See `requirements.txt`
- Models: Auto-downloaded via `make download`
