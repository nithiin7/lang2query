# Text-to-Query Agentic Workflow

A LangGraph-based system that converts natural language requests into SQL queries using database metadata stored in markdown format.

## 🚀 Features

- **Natural Language Processing**: Convert plain English requests to SQL queries
- **Database Schema Awareness**: Uses markdown-based database metadata
- **LangGraph Workflow**: Multi-agent orchestration with state management
- **Query Validation**: Built-in safety checks and validation
- **Interactive CLI**: Easy-to-use command-line interface
- **Extensible Architecture**: Easy to add new agents and workflows

## 🏗️ Architecture

The system follows the LangGraph pattern with these components:

```
User Request → Schema Parser → Query Agent → Validator → Response Formatter
```

### Components

1. **Database Parser** (`src/utils/db_parser.py`)
   - Parses markdown files containing database schema
   - Extracts tables, columns, relationships, and metadata

2. **Query Generation Agent** (`src/agents/query_agent.py`)
   - Uses OpenAI's GPT models to generate SQL queries
   - Incorporates database schema context
   - Returns structured query objects with explanations

3. **LangGraph Workflow** (`src/query_workflow.py`)
   - Orchestrates the entire process
   - Manages state between nodes
   - Handles conditional routing and error handling

4. **CLI Interface** (`src/cli.py`)
   - Command-line interface for easy testing
   - Interactive mode for exploration
   - Single query mode for automation

## 📋 Prerequisites

- Python 3.12+
- OpenAI API key
- Poetry (for dependency management)

## 🛠️ Installation

1. Clone the repository:
```bash
git clone <your-repo>
cd lang2query
```

2. Install dependencies:
```bash
poetry install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## 🚀 Usage

### Quick Start

1. **Test the system** (without API calls):
```bash
python test_workflow.py
```

2. **Run a single query**:
```bash
poetry run query "Show me all users who have placed orders"
```

3. **Interactive mode**:
```bash
poetry run query --interactive
```

4. **Run the main application**:
```bash
poetry run agent
```

### Example Queries

Try these natural language requests:

- "Show me all users who have placed orders"
- "What are the top 5 products by price?"
- "Find orders with total amount greater than $100"
- "Show me users and their order counts"
- "List products in the Electronics category"

## 📊 Database Schema

The system uses a markdown file (`db_metadata.md`) that contains:

- **Tables**: users, orders, products, categories, order_items
- **Columns**: name, type, nullability, keys, description, category
- **Relationships**: Foreign key relationships between tables
- **Notes**: Additional database constraints and information

### Schema Format

```markdown
### table_name
| Column | Type | Null | Key | Description | Category |
|--------|------|------|-----|-------------|----------|
| id | INT | NOT NULL | PRIMARY KEY | Unique identifier | Identity |
```

## 🔧 Customization

### Adding New Database Schemas

1. Create a new markdown file with your schema
2. Update the file path in your workflow
3. The parser will automatically handle the new structure

### Extending the Workflow

1. **Add new nodes** to `src/query_workflow.py`
2. **Create new agents** in `src/agents/`
3. **Modify the state** in `WorkflowState` class
4. **Update routing logic** in `should_continue` function

### Example: Adding a Query Execution Node

```python
def execute_query_node(state: WorkflowState) -> WorkflowState:
    """Execute the generated SQL query against a database."""
    # Your database execution logic here
    return state

# Add to workflow
workflow.add_node("execute_query", execute_query_node)
workflow.add_edge("validate_query", "execute_query")
workflow.add_edge("execute_query", "format_response")
```

## 🧪 Testing

Run the test suite:

```bash
# Test basic functionality
python test_workflow.py

# Run unit tests
poetry run test

# Lint and type check
poetry run lint
poetry run type-check
```

## 📝 Configuration

### Environment Variables

- `API_KEY`: Your OpenAI API key
- `MODEL`: Model to use (default: gpt-4o-mini)
- `LOG_LEVEL`: Logging level (default: INFO)

### Model Configuration

Update the model in `src/agents/query_agent.py`:

```python
self.llm = ChatOpenAI(
    model="gpt-4",  # Change model here
    api_key=api_key,
    temperature=0.1
)
```

## 🔍 Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your `.env` file contains `OPENAI_API_KEY`
2. **Schema Parse Error**: Check your markdown file format
3. **Import Errors**: Ensure you're running from the project root

### Debug Mode

Enable verbose logging:

```bash
poetry run query --verbose "your query here"
```

## 🚧 Future Enhancements

- [ ] Database connection and query execution
- [ ] Query result visualization
- [ ] Support for multiple database types
- [ ] Query optimization suggestions
- [ ] Natural language query refinement
- [ ] Query history and learning
- [ ] Web interface

## 📚 Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.
