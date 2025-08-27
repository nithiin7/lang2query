"""Command-line interface for the Lang2Query system."""

import argparse
import sys

from .core.workflow import run_query_workflow
from .utils.logger import logger


def main():
    """CLI main function."""
    parser = argparse.ArgumentParser(
        description="Lang2Query: Text-to-Query Agentic Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
            %(prog)s "Show me all users who have placed orders"
            %(prog)s "What are the top 5 products by price?"
            %(prog)s --interactive
        """,
    )

    parser.add_argument(
        "query", nargs="?", help="Natural language query to convert to SQL"
    )

    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel("DEBUG")

    if args.interactive:
        run_interactive_mode()
    elif args.query:
        run_single_query(args.query)
    else:
        parser.print_help()
        sys.exit(1)


def run_single_query(query: str):
    """Run a single query and display the result."""
    try:
        print(f"🔄 Processing: {query}")
        print("-" * 50)

        result = run_query_workflow(query)

        print("\n📋 Result:")
        print(result)

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


def run_interactive_mode():
    """Run the application in interactive mode."""
    try:
        print("🚀 Lang2Query: Text-to-Query Agentic Workflow (Interactive Mode)")
        print("=" * 60)
        print()

        # Example queries to test
        example_queries = [
            "Show me all users who have placed orders",
            "What are the top 5 products by price?",
            "Find orders with total amount greater than $100",
            "Show me users and their order counts",
            "List products in the Electronics category",
        ]

        print("Example queries you can try:")
        for i, query in enumerate(example_queries, 1):
            print(f"{i}. {query}")
        print()

        while True:
            try:
                # Get user input
                user_input = input(
                    "Enter your query request (or 'quit' to exit): "
                ).strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    print("Goodbye! 👋")
                    break

                if not user_input:
                    print("Please enter a query request.")
                    continue

                print(f"\n🔄 Processing: {user_input}")
                print("-" * 50)

                # Run the workflow
                result = run_query_workflow(user_input)

                print("\n📋 Result:")
                print(result)
                print("\n" + "=" * 50)

            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")
                print(f"❌ Error: {e}")
                print("Please try again.")

    except Exception as e:
        logger.error(f"Fatal error in interactive mode: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
