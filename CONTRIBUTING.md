# Contributing to Lang2Query

Thanks for your interest in contributing. This doc covers the mechanics of getting set up and submitting a change — for architecture and design conventions, see [CLAUDE.md](CLAUDE.md).

## Reporting Issues

Use the GitHub issue tracker. Include steps to reproduce, expected vs. actual behavior, environment (OS, Python/Node version), and any error messages or logs.

## Making a Change

1. Fork the repo and create a branch: `git checkout -b feature/amazing-feature`
2. Make your change, following the coding standards below
3. Add or update tests for the behavior you changed
4. Run the test suite and linters (see [Testing](#testing))
5. Commit with a clear, descriptive message and push to your fork
6. Open a Pull Request

## Development Setup

**Prerequisites:** Python 3.11+, Node.js 18+, Git

```bash
git clone https://github.com/nithiin7/lang2query.git
cd lang2query

# Backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
cd backend && pip install ".[dev]" && cd ..   # installs dev tooling (pytest, black, isort, flake8, mypy, ...)
pre-commit install

# Frontend
cd frontend && npm install && cd ..

# Run everything
make dev
```

## Coding Standards

Baseline: PEP 8, Black, isort, flake8, type hints on all function signatures, Google-style docstrings; ESLint/Prettier and functional components with typed props on the frontend. Project-specific rules — DRY across agents, no direct provider SDK calls outside `ai/llm/`, no new agent without a typed output schema, errors typed and logged rather than swallowed — are documented in [CLAUDE.md](CLAUDE.md#5-code-standards).

## Testing

```bash
# Backend (from backend/)
pytest                              # full suite
pytest --cov=app --cov-report=html  # with coverage
pytest tests/test_sql_safety_guard.py -v

# Frontend
cd frontend && npm test
```

Write tests for new functionality, cover both success and error paths, and mock external dependencies (LLM calls, DB connections).

## Pull Requests

Before submitting, check that:

- [ ] Tests pass locally (`pytest`, `npm test`)
- [ ] Code is formatted (`black app/`, `isort app/` from `backend/`) and lints clean (`flake8 app/`)
- [ ] New functionality has tests
- [ ] Docs are updated if behavior changed
- [ ] No unrelated changes mixed in

CI runs these checks automatically; a maintainer reviews and merges once they pass.

## Where to Contribute

New agents, UI components, API endpoints, retrieval tools, documentation, and test coverage are all welcome. For anything nontrivial — a new agent, a routing change, a new LLM provider — open an issue first to align on approach before writing code, especially for changes touching `workflow/` or `agents/`, where a routing mistake can silently create infinite loops or dead-end states.

## License

By contributing, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
