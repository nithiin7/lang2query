# Contributing to Lang2Query

Thank you for your interest in contributing to Lang2Query! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues

- Use the GitHub issue tracker to report bugs or request features
- Search existing issues before creating a new one
- Provide detailed information about the issue, including:
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment details (OS, Python version, Node.js version)
  - Error messages or logs

### Suggesting Enhancements

- Use the "Enhancement" label for feature requests
- Describe the use case and expected behavior
- Consider the impact on existing functionality
- Provide examples of how the feature would be used

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following our coding standards
4. **Add tests** for new functionality
5. **Run the test suite** to ensure everything works
6. **Commit your changes** with clear, descriptive messages
7. **Push to your fork** and create a Pull Request

## 🛠️ Development Setup

### Prerequisites

- Python 3.8+ (recommended: Python 3.11+)
- Node.js 18+ (recommended: Node.js 20+)
- Git
- Virtual environment (venv, conda, or pipenv)

### Backend Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/lang2query.git
cd lang2query

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Install pre-commit hooks
pre-commit install
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd app

# Install dependencies
npm install

# Start development server
npm run dev
```

### Full Development Environment

```bash
# From project root, start both backend and frontend
make run
```

## 📝 Coding Standards

### Python (Backend)

- **Style**: Follow PEP 8 with line length of 127 characters
- **Formatting**: Use Black for code formatting
- **Imports**: Use isort for import sorting
- **Linting**: Use flake8 for linting
- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Use Google-style docstrings for all public functions and classes

```python
def process_query(query: str, mode: str = "normal") -> Dict[str, Any]:
    """Process a natural language query.

    Args:
        query: The natural language query to process
        mode: Processing mode ("normal" or "interactive")

    Returns:
        Dictionary containing the processed query results

    Raises:
        ValueError: If query is empty or invalid
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")

    # Implementation here
    return {"result": "processed"}
```

### TypeScript/React (Frontend)

- **Style**: Follow ESLint configuration
- **Formatting**: Use Prettier for code formatting
- **Type Safety**: Use TypeScript for all new code
- **Components**: Use functional components with hooks
- **Props**: Define interfaces for all component props
- **Error Handling**: Implement proper error boundaries and error handling

```typescript
interface QueryFormProps {
  onSubmit: (query: string) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export const QueryForm: React.FC<QueryFormProps> = ({
  onSubmit,
  isLoading = false,
  placeholder = "Enter your query...",
}) => {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSubmit(query.trim());
    }
  };

  return <form onSubmit={handleSubmit}>{/* Component implementation */}</form>;
};
```

## 🧪 Testing

### Backend Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_agents.py

# Run with verbose output
pytest -v
```

### Frontend Testing

```bash
# Run tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

### Writing Tests

- Write tests for all new functionality
- Aim for high test coverage (>80%)
- Use descriptive test names
- Test both success and error cases
- Mock external dependencies

```python
# Backend test example
def test_process_query_success():
    """Test successful query processing."""
    query = "Show me all users"
    result = process_query(query)

    assert result["status"] == "success"
    assert "sql" in result
    assert result["sql"] is not None

def test_process_query_empty():
    """Test query processing with empty input."""
    with pytest.raises(ValueError, match="Query cannot be empty"):
        process_query("")
```

```typescript
// Frontend test example
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryForm } from "./QueryForm";

describe("QueryForm", () => {
  it("should submit query when form is submitted", () => {
    const mockOnSubmit = jest.fn();
    render(<QueryForm onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText("Enter your query...");
    const submitButton = screen.getByRole("button", { name: /submit/i });

    fireEvent.change(input, { target: { value: "test query" } });
    fireEvent.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledWith("test query");
  });
});
```

## 📋 Pull Request Guidelines

### Before Submitting

- [ ] Code follows the project's coding standards
- [ ] All tests pass
- [ ] New functionality has tests
- [ ] Documentation is updated
- [ ] No merge conflicts
- [ ] Commit messages are clear and descriptive

### Pull Request Template

```markdown
## Description

Brief description of changes

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs automatically
2. **Code Review**: At least one maintainer reviews the code
3. **Testing**: All tests must pass
4. **Documentation**: Documentation must be updated if needed
5. **Approval**: Maintainer approves and merges the PR

## 🏗️ Project Structure

### Backend (`src/`)

```
src/
├── agents/           # LangGraph agents
├── api/             # FastAPI application
├── retreiver/       # Knowledge base system
├── tools/           # LangChain tools
├── lib/             # Core libraries
├── utils/           # Utilities
└── models/          # Pydantic models
```

### Frontend (`app/`)

```
app/
├── src/
│   ├── components/  # React components
│   ├── lib/         # Utilities and API client
│   ├── hooks/       # Custom React hooks
│   └── types/       # TypeScript definitions
└── public/          # Static assets
```

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Environment**:

   - OS and version
   - Python version
   - Node.js version
   - Browser (for frontend issues)

2. **Steps to Reproduce**:

   - Clear, numbered steps
   - Expected behavior
   - Actual behavior

3. **Additional Context**:
   - Error messages
   - Screenshots (for UI issues)
   - Log files
   - Configuration files (sanitized)

## 💡 Feature Requests

When suggesting features:

1. **Use Case**: Describe the problem you're trying to solve
2. **Proposed Solution**: How you think it should work
3. **Alternatives**: Other solutions you've considered
4. **Additional Context**: Any other relevant information

## 📚 Documentation

- Update documentation for any new features
- Add docstrings to new functions and classes
- Update README files if needed
- Include examples in your documentation

## 🎯 Areas for Contribution

- **New Agents**: Add new LangGraph agents for specific tasks
- **UI Components**: Create new React components
- **API Endpoints**: Add new API endpoints
- **Documentation**: Improve existing documentation
- **Tests**: Add more test coverage
- **Performance**: Optimize existing code
- **Accessibility**: Improve accessibility features
- **Internationalization**: Add multi-language support

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Discord**: Join our community Discord (if available)
- **Email**: Contact maintainers directly for sensitive issues

## 📄 License

By contributing to Lang2Query, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be recognized in:

- CONTRIBUTORS.md file
- Release notes
- Project documentation
- GitHub contributors page

Thank you for contributing to Lang2Query! 🚀
