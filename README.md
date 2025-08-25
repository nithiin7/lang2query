# Lang2Query Agent

A production-ready Lang2Query agent built using LangGraph for converting natural language queries to query statements with high accuracy.

## Project Structure

```
lang2query/
├── app/
│   ├── main.py                 # Main application entry point
│   ├── agents/
│   │   ├── customer.py         # Customer agent
│   │   ├── router.py           # Router agent
│   │   └── helpers/
│   │       └── customer_helper.py
│   ├── services/
│   │   └── fuzzy.py            # Fuzzy matching utilities
│   └── kb/
│       └── build_kb.py         # Knowledge base generator
├── db/
│   └── create_tables.py        # Database setup and table creation
├── kb.pkl                      # Serialized knowledge base
├── scripts/                    # Helper scripts (empty placeholder)
├── requirements.txt            # Dependencies
├── pyproject.toml              # uv scripts, tooling config
└── README.md                   # This file
```

## Features

- **Multi-Agent Architecture**: Uses LangGraph for orchestrating multiple specialized agents
- **Intelligent Routing**: Automatically routes queries to appropriate domain agents (customer, orders, products)
- **Fuzzy Matching**: Implements fuzzy string matching for improved query understanding
- **Query Validation**: Multi-step validation process for SQL query generation
- **Knowledge Base**: Dynamic knowledge base generation from database schema and sample data

## Usage

1. **Setup Database**: `uv run db`
2. **Generate Knowledge Base**: `uv run kb`
3. **Run Main Application**: `uv run dev`

## Architecture

The system uses a multi-agent approach where:

- **Router Agent**: Determines which domain agents should handle the query
- **Domain Agents**: Extract relevant tables and columns for their domain
- **Filter Agent**: Identifies and extracts filter conditions
- **Query Generator**: Converts the extracted information into SQL queries
- **Query Validator**: Ensures the generated SQL is correct and optimized

## Dependencies

- LangGraph
- LangChain
- SQLAlchemy
- Pandas
- MySQL Connector
- Anthropic Claude API
- Groq API

## Production Readiness

This agent is designed for production use with:

- Proper error handling
- Modular architecture
- Scalable design
- High accuracy through multi-step validation
