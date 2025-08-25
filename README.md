# Lang2Query Agent

A production-ready, multi-language natural language to query agent built using LangGraph for converting natural language queries to structured queries in any language with high accuracy.

## 🚀 Features

- **Multi-Language Support**: Generate queries in SQL, MongoDB, Elasticsearch, Cypher, and more
- **Multi-Agent Architecture**: Uses LangGraph for orchestrating specialized domain agents
- **Intelligent Routing**: Automatically routes queries to appropriate domain agents
- **Fuzzy Matching**: Implements fuzzy string matching for improved query understanding
- **Query Validation**: Multi-step validation process for query generation
- **Dynamic Knowledge Base**: Generates knowledge base from database schema and sample data
- **Configurable**: Easy configuration for different databases, query languages, and domains
- **Production Ready**: Proper error handling, logging, and performance optimization

## 🏗️ Project Structure

```
lang2query/
├── app/
│   ├── main.py                     # Main application entry point
│   ├── config.py                   # Configuration for databases, languages, domains
│   ├── agents/
│   │   ├── customer.py             # Customer domain agent
│   │   ├── router.py               # Query routing agent
│   │   └── helpers/
│   │       └── customer_helper.py  # Helper functions for agents
│   ├── services/
│   │   └── fuzzy.py                # Fuzzy matching utilities
│   └── kb/
│       └── build_kb.py             # Knowledge base generator
├── db/
│   └── create_tables.py            # Database setup and table creation
├── scripts/                         # Helper scripts
├── kb.pkl                          # Serialized knowledge base
├── requirements.txt                 # Dependencies
├── pyproject.toml                  # uv scripts, tooling config
├── Makefile                        # Development commands
└── README.md                       # This file
```

## 🎯 Supported Query Languages

- **SQL**: MySQL, PostgreSQL, SQLite, Oracle, SQL Server
- **MongoDB**: Aggregation pipelines, find queries
- **Elasticsearch**: Query DSL, aggregations
- **Cypher**: Neo4j graph queries
- **Extensible**: Easy to add new query languages

## 🗄️ Supported Domains

- **E-commerce**: Customers, orders, products, payments
- **Healthcare**: Patients, appointments, diagnoses, billing
- **Finance**: Customers, transactions, investment products
- **Extensible**: Easy to add new domains

## 🚀 Quick Start

1. **Setup Environment**:

   ```bash
   # Install uv and create virtual environment
   uv venv .venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

2. **Setup Database**:

   ```bash
   uv run db
   ```

3. **Generate Knowledge Base**:

   ```bash
   uv run kb
   ```

4. **Run the Agent**:
   ```bash
   uv run dev
   ```

## 🛠️ Development Commands

```bash
# Code quality
uv run format          # Format code with Ruff
uv run lint            # Lint code with Ruff

# Development workflow
make setup             # Setup development environment
make format            # Format code
make lint              # Lint code
make hooks             # Run pre-commit hooks
make cz                # Create conventional commit
make bump              # Bump version and update changelog
```

## 🏗️ Architecture

The system uses a sophisticated multi-agent approach:

- **Router Agent**: Determines which domain agents should handle the query
- **Domain Agents**: Extract relevant tables and columns for their domain
- **Filter Agent**: Identifies and extracts filter conditions
- **Query Generator**: Converts extracted information into target language queries
- **Query Validator**: Ensures generated queries are correct and optimized

## ⚙️ Configuration

The system is highly configurable through `app/config.py`:

- **Database**: Switch between MySQL, PostgreSQL, SQLite
- **Query Language**: Configure for SQL, MongoDB, Elasticsearch, etc.
- **Domain**: Adapt for e-commerce, healthcare, finance, etc.
- **Models**: Configure different LLM providers and models
- **Performance**: Tune timeouts, retries, and caching

## 🔧 Adding New Query Languages

1. Add language configuration to `QUERY_LANGUAGE_CONFIG`
2. Create language-specific prompt templates
3. Implement language-specific validation logic
4. Update the query generation pipeline

## 🔧 Adding New Domains

1. Add domain configuration to `DOMAIN_CONFIGS`
2. Create domain-specific agent logic
3. Update routing and knowledge base generation
4. Add domain-specific validation rules

## 📊 Performance & Production

- **Concurrent Processing**: Multiple agents can run simultaneously
- **Caching**: Results are cached for improved performance
- **Error Handling**: Comprehensive error handling and retry logic
- **Logging**: Structured logging for monitoring and debugging
- **Metrics**: Performance metrics and query analytics

## 🧪 Testing

```bash
# Run tests
uv run test

# Run with coverage
uv run test --cov
```

## 📝 Contributing

1. Follow conventional commit standards
2. Run code quality checks before committing
3. Add tests for new features
4. Update documentation

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues and questions:

1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information
