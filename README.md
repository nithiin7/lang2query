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

## 🏗️ Project Structure

```
lang2query/
├── src/
│   ├── main.py                     # Main application entry point
│   ├── config.py                   # Configuration management
│   ├── agents/
│   │   ├── base_agent.py             # Base agent
├── .env.example                     # Environment variables template
├── requirements.txt                 # Dependencies
├── pyproject.toml                  # uv scripts, tooling config
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
