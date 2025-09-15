"""
Main entry point for the lang2query application.

This module provides an interface to the LangGraph-based agent workflow.
"""

import logging
import os
import time

from lang2query.models.wrapper import ModelWrapper
from lang2query.utils import Colors, log_section_header, setup_colored_logging
from lang2query.workflow import Text2QueryWorkflow

OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")

logger = setup_colored_logging(level=logging.INFO)
main_logger = logging.getLogger(__name__)


def main():
    """Main function for the LangGraph-based Lang2Query workflow."""
    try:
        log_section_header(main_logger, "🚀 Lang2Query WORKFLOW 🚀")
        main_logger.info(
            "🚀 Starting Lang2Query application with LangGraph workflow..."
        )

        use_ollama = os.environ.get("L2Q_USE_OLLAMA", "1") != "0"
        if use_ollama:
            main_logger.info(f"📥 Connecting to Ollama API at {OLLAMA_ENDPOINT}...")
            main_logger.info(f"🤖 Using model: {OLLAMA_MODEL}")
            model_wrapper = ModelWrapper(
                ollama_endpoint=OLLAMA_ENDPOINT,
                ollama_model=OLLAMA_MODEL,
                ollama_timeout=300,
            )
        else:
            main_logger.info("📥 Loading model from models folder...")
            model_wrapper = ModelWrapper(
                model_path=os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "models",
                    "meta-llama-Llama-3.2-3B-Instruct-FP16",
                ),
                use_quantization=True,
            )

        model_info = model_wrapper.get_model_info()

        if model_wrapper.use_ollama:
            main_logger.info(
                f"📊 Connected to: {model_info['ollama_model']} via {model_info['ollama_endpoint']}"
            )
        else:
            main_logger.info(
                f"📊 Using local model: {model_info['model_type']} from {model_info['model_path']}"
            )
            main_logger.info(
                f"🔧 Device: {model_info['device']}, Quantization: {model_info['quantization']}"
            )

        main_logger.info(f"🔗 Chat format: {model_info['chat_format']}")

        main_logger.info("🔧 Initializing LangGraph workflow...")
        workflow = Text2QueryWorkflow(model_wrapper)

        print("\n" + "=" * 60)
        print("🚀 Lang2Query - Natural Language to Query Generator")
        print("=" * 60)
        print("Type your natural language query and press Enter.")
        print("Type 'quit' or 'exit' to stop the program.")
        print("=" * 60)
        print("\n💡 Example queries you can try:")
        print("  • Find all customers with pending KYC verification")
        print("  • Show me payment transactions for the last 30 days")
        print("  • Get user profiles who haven't logged in for 90 days")
        print("  • List all orders with their current status")
        print("  • Find users who made payments above $1000")
        print("  • Get customer details with their KYC status")
        print("  • Show transactions with customer names and amounts")
        print("=" * 60)

        while True:
            try:
                user_query = input("\n💬 Enter your query: ").strip()

                # Check for exit commands
                if user_query.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Goodbye!")
                    break

                # Check for empty input
                if not user_query:
                    print("❌ Please enter a valid query.")
                    continue

                print(f"\n🔄 Processing query: {user_query}")
                print("-" * 50)

                # Time the workflow execution
                start_time = time.time()

                # Process the query through the workflow
                final_state = workflow.process_query(user_query)

                workflow_time = time.time() - start_time

                # Get workflow summary
                summary = workflow.get_workflow_summary(final_state)

                # Display results with beautiful formatting
                print(
                    f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}📊 Workflow Results:{Colors.RESET}"
                )
                print(
                    f"{Colors.BRIGHT_WHITE}Query: {Colors.BRIGHT_YELLOW}{summary['natural_language_query']}{Colors.RESET}"
                )
                print(
                    f"{Colors.BRIGHT_WHITE}Status: {Colors.BRIGHT_GREEN if 'validated' in summary['status'] else Colors.BRIGHT_RED}{summary['status']}{Colors.RESET}"
                )
                print(
                    f"{Colors.BRIGHT_WHITE}Retries Left: {Colors.BRIGHT_BLUE}{summary['retries_left']}{Colors.RESET}"
                )
                print(
                    f"{Colors.BRIGHT_WHITE}Databases Identified: {Colors.BRIGHT_MAGENTA}{summary['databases']['count']}{Colors.RESET} ({', '.join(summary['databases']['identified'])})"
                )
                print(
                    f"{Colors.BRIGHT_WHITE}Tables Retrieved: {Colors.BRIGHT_GREEN if summary['tables']['retrieved'] else Colors.BRIGHT_RED}{'✅' if summary['tables']['retrieved'] else '❌'}{Colors.RESET} ({summary['tables']['count']} tables)"
                )
                print(
                    f"{Colors.BRIGHT_WHITE}Columns Retrieved: {Colors.BRIGHT_GREEN if summary['columns']['retrieved'] else Colors.BRIGHT_RED}{'✅' if summary['columns']['retrieved'] else '❌'}{Colors.RESET} ({summary['columns']['count']} columns)"
                )
                print(
                    f"{Colors.BRIGHT_WHITE}Query Plan: {Colors.BRIGHT_GREEN if summary['query_plan']['created'] else Colors.BRIGHT_RED}{'✅' if summary['query_plan']['created'] else '❌'}{Colors.RESET} ({summary['query_plan']['count']} chars)"
                )

                # Display the generated query with syntax highlighting
                if summary["query"]["query"]:
                    print(
                        f"\n{Colors.BOLD}{Colors.BRIGHT_MAGENTA}🔍 Generated SQL Query:{Colors.RESET}"
                    )
                    print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")
                    # Apply basic SQL syntax highlighting
                    query = summary["query"]["query"]
                    query = query.replace(
                        "SELECT",
                        f"{Colors.BOLD}{Colors.BRIGHT_BLUE}SELECT{Colors.RESET}",
                    )
                    query = query.replace(
                        "FROM", f"{Colors.BOLD}{Colors.BRIGHT_GREEN}FROM{Colors.RESET}"
                    )
                    query = query.replace(
                        "WHERE",
                        f"{Colors.BOLD}{Colors.BRIGHT_YELLOW}WHERE{Colors.RESET}",
                    )
                    query = query.replace(
                        "ORDER BY",
                        f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}ORDER BY{Colors.RESET}",
                    )
                    query = query.replace(
                        "LIMIT", f"{Colors.BOLD}{Colors.BRIGHT_CYAN}LIMIT{Colors.RESET}"
                    )
                    for line in query.split("\n"):
                        if line.strip():
                            print(f"   {line}")
                    print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")
                else:
                    print(f"{Colors.BRIGHT_RED}Query: None{Colors.RESET}")

                # Display confidence scores with color coding
                confidence = summary["query"]["confidence"]
                confidence_color = (
                    Colors.BRIGHT_GREEN
                    if confidence > 0.7
                    else Colors.BRIGHT_YELLOW
                    if confidence > 0.4
                    else Colors.BRIGHT_RED
                )
                print(
                    f"{Colors.BRIGHT_WHITE}Query Confidence: {confidence_color}{confidence:.2f}{Colors.RESET}"
                )
                print(
                    f"{Colors.BRIGHT_WHITE}Overall Confidence: {confidence_color}{summary['confidence_score']:.2f}{Colors.RESET}"
                )
                print(
                    f"{Colors.BRIGHT_WHITE}Execution Time: {Colors.BRIGHT_BLUE}{workflow_time:.2f} seconds{Colors.RESET}"
                )

                if summary["query_plan"]["preview"]:
                    print(
                        f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}🧠 Query Plan:{Colors.RESET}"
                    )
                    print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")
                    print(
                        f"{Colors.BRIGHT_WHITE}{summary['query_plan']['preview']}{Colors.RESET}"
                    )
                    print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

                print(f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN}{'=' * 60}{Colors.RESET}")
                print(
                    f"{Colors.BOLD}{Colors.BRIGHT_GREEN}✅ Query processed successfully!{Colors.RESET}"
                )
                print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}{'=' * 60}{Colors.RESET}")

            except KeyboardInterrupt:
                print("\n\n👋 Program interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error processing query: {e}")
                main_logger.error(f"Error in main loop: {e}")
                continue

    except Exception as e:
        main_logger.error(f"❌ Application failed: {e}")
        raise


if __name__ == "__main__":
    main()
