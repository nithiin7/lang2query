# Lang2Query Agent

A production-ready Lang2Query agent built using LangGraph for converting natural language queries to query statements with high accuracy.

## Project Structure

```
lang2query/
├── agent_helpers/
│   └── customer_helper.py      # Helper functions for customer agent
├── create_tables.py            # Database setup and table creation
├── customer_agent.py           # Customer-specific agent logic
├── fuzzy_wuzzy.py              # Fuzzy string matching utilities
├── knowledge_base.py           # Knowledge base generation and management
├── main.py                     # Main application entry point
├── router_agent.py             # Request routing logic
├── kb.pkl                      # Serialized knowledge base
├── test.csv                    # Test data
└── README.md                   # This file
```

## Features

- **Multi-Agent Architecture**: Uses LangGraph for orchestrating multiple specialized agents
- **Intelligent Routing**: Automatically routes queries to appropriate domain agents (customer, orders, products)
- **Fuzzy Matching**: Implements fuzzy string matching for improved query understanding
- **Query Validation**: Multi-step validation process for SQL query generation
- **Knowledge Base**: Dynamic knowledge base generation from database schema and sample data

## Usage

1. **Setup Database**: Run `python create_tables.py` to set up the database and tables
2. **Generate Knowledge Base**: Run `python knowledge_base.py` to create the knowledge base
3. **Run Main Application**: Execute `python main.py` to start the text-to-SQL agent

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