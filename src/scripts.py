"""Development script entry points for Poetry."""

import subprocess
import sys


def run_command(command: list[str], description: str) -> None:
    """Run a command and handle errors gracefully."""
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        print(f"✅ {description} completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr, file=sys.stderr)
        sys.exit(e.returncode)
    except FileNotFoundError as e:
        print(f"❌ Command not found: {e}")
        sys.exit(1)


def format() -> None:
    """Format code using black."""
    run_command(["black", "src", "tests"], "Code formatting")


def lint() -> None:
    """Lint code using ruff."""
    run_command(["ruff", "check", "src", "tests"], "Code linting")


def lint_fix() -> None:
    """Fix linting issues using ruff."""
    run_command(["ruff", "check", "src", "tests", "--fix"], "Lint fixing")


def type_check() -> None:
    """Run type checking using mypy."""
    run_command(["mypy", "src"], "Type checking")


def test() -> None:
    """Run tests using pytest."""
    run_command(["pytest", "--cov"], "Testing")


def precommit() -> None:
    """Run pre-commit hooks."""
    run_command(["pre-commit", "run", "--all-files"], "Pre-commit hooks")


def commit() -> None:
    """Create a conventional commit."""
    run_command(["cz", "commit"], "Conventional commit")


def changelog() -> None:
    """Generate changelog."""
    run_command(["cz", "changelog"], "Changelog generation")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts.py <command>")
        print(
            "Available commands: format, lint, lint-fix, type-check, test, precommit, "
            "commit, changelog"
        )
        sys.exit(1)

    command = sys.argv[1]
    commands = {
        "format": format,
        "lint": lint,
        "lint-fix": lint_fix,
        "type-check": type_check,
        "test": test,
        "precommit": precommit,
        "commit": commit,
        "changelog": changelog,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        print("Available commands:", ", ".join(commands.keys()))
        sys.exit(1)
