# Lang2Query Agent

A multi-language natural language to query agent built using LangGraph for converting natural language queries to structured queries in any language with high accuracy.

## 🚀 Features

- **Multi-Language Support**: Generate queries in SQL, MongoDB, Elasticsearch, Cypher, and more
- **Multi-Agent Architecture**: Uses LangGraph for orchestrating specialized domain agents
- **Intelligent Routing**: Automatically routes queries to appropriate domain agents
- **Fuzzy Matching**: Implements fuzzy string matching for improved query understanding
- **Query Validation**: Multi-step validation process for query generation
- **Dynamic Knowledge Base**: Generates knowledge base from database schema and sample data
- **Environment-Based Configuration**: All settings configurable via environment variables
- **Production Ready**: Proper error handling, logging, and performance optimization

## 📋 Prerequisites

- Python 3.12 or higher
- Poetry (for dependency management)

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/lang2query.git
cd lang2query
```

### 2. Install Poetry (if not already installed)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 3. Install dependencies
```bash
poetry install
```

### 4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

## 🏃‍♂️ Running the Application

### Quick Start
```bash
# Using Poetry
poetry run agent

# Using Make
make run
```

### Alternative Run Methods
```bash
# Direct Python execution
poetry run python src/main.py

# Activate virtual environment first
poetry shell
python src/main.py
```

## 🏗️ Project Structure

```
lang2query/
├── src/
│   ├── main.py                     # Main application entry point
│   ├── config.py                   # Configuration management
│   ├── agent_graph.py              # LangGraph agent orchestration
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py          # Base agent class
│   │   └── sample_agent.py        # Sample agent implementation
│   └── utils/
│       ├── __init__.py
│       └── logger.py               # Logging utilities
├── tests/                          # Test suite
├── .env.example                    # Environment variables template
├── pyproject.toml                  # Poetry configuration and dependencies
├── poetry.lock                     # Locked dependency versions
├── Makefile                        # Development commands
└── README.md                       # This file
```

## 🎯 Supported Query Languages

- **SQL**: MySQL, PostgreSQL, SQLite, Oracle, SQL Server
- **MongoDB**: Aggregation pipelines, find queries
- **Extensible**: Easy to add new query languages

## ⚙️ Configuration

The system is highly configurable through environment variables. Copy `.env.example` to `.env` and customize:

### **Required Environment Variables**

```bash
# API Keys (Required)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database Configuration
ACTIVE_DATABASE=mysql
MYSQL_CONNECTION_STRING=mysql+mysqlconnector://user:pass@host/database
```

## 🧪 Development

### Code Quality Commands
```bash
# Format code
make format
poetry run format

# Lint code
make lint
poetry run lint

# Fix linting issues
make lint-fix
poetry run lint-fix

# Type checking
make type-check
poetry run type-check

# Run tests
make test
poetry run test
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
poetry run precommit install

# Run all pre-commit checks
poetry run precommit run --all-files
```

### Commit Standards
```bash
# Use conventional commits
poetry run commit

# Generate changelog
poetry run changelog
```

## 📦 Dependencies

### Core Dependencies
- **LangGraph** (≥0.6.6): Agent orchestration framework
- **LangChain** (≥0.3.27): LLM integration and utilities
- **OpenAI** (≥1.101.0): OpenAI API client
- **Pydantic** (≥2.11.7): Data validation and settings
- **Rich** (≥14.1.0): Terminal formatting and UI

### Development Dependencies
- **pytest**: Testing framework
- **black**: Code formatter
- **ruff**: Fast Python linter
- **mypy**: Static type checker
- **pre-commit**: Git hooks for code quality
- **commitizen**: Conventional commit management

## 🚀 Deployment

### Local Development
```bash
# Install in development mode
poetry install

# Run with hot reload (if implemented)
poetry run agent
```

### Production
```bash
# Build the package
poetry build

# Install in production
pip install dist/lang2query-*.whl
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow conventional commit standards
4. Run code quality checks before committing
5. Add tests for new features
6. Update documentation
7. Submit a pull request

### Development Setup
```bash
# Install development dependencies
poetry install --with dev

# Set up pre-commit hooks
poetry run precommit install
```

## 🐛 Troubleshooting

### Common Issues

1. **Poetry not found**: Install Poetry using the official installer
2. **Python version mismatch**: Ensure you have Python 3.12+
3. **Environment variables**: Check that `.env` file exists and is properly configured
4. **Dependencies**: Run `poetry install` to ensure all dependencies are installed

### Getting Help

1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information including:
   - Python version
   - Poetry version
   - Error messages
   - Steps to reproduce

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues and questions:

1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information

## 🔄 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.
