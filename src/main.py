"""
Main entry point for the text2query application.

This module provides an interface to the LangGraph-based agent workflow.
"""

import json
import os
import urllib3
import logging
import time

from lib import ModelWrapper
from workflow import Text2QueryWorkflow
from utils import setup_colored_logging, log_section_header, Colors
from pathlib import Path
import config as app_config

# Disable SSL verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

# Provider/model configuration
PROVIDER = getattr(app_config, "PROVIDER", "ollama")
OLLAMA_MODEL = getattr(app_config, "OLLAMA_MODEL", "gpt-oss:20b")
OLLAMA_BASE_URL = getattr(app_config, "OLLAMA_BASE_URL", "http://localhost:11434")
NVIDIA_BASE_URL = getattr(app_config, "NVIDIA_BASE_URL", None)
NVIDIA_MODEL = getattr(app_config, "NVIDIA_MODEL", None)

# Knowledge Base configuration
MD_DIRECTORY = getattr(app_config, "MD_DIRECTORY", "input")
KB_DIRECTORY = getattr(app_config, "KB_DIRECTORY", "src/kb")
COLLECTION_NAME = getattr(app_config, "COLLECTION_NAME", "sql_generation_kb")
EMBEDDING_MODEL_PATH = getattr(app_config, "EMBEDDING_MODEL_PATH", None)

# Set up beautiful colored logging
logger = setup_colored_logging(level=logging.INFO)
main_logger = logging.getLogger(__name__)


def create_model_wrapper() -> ModelWrapper:
    """Create and return model wrapper based on config provider."""
    provider = PROVIDER.lower()
    main_logger.info(f"📥 Initializing {provider.upper()} model wrapper...")

    if provider == "nvidia":
        return ModelWrapper(model=NVIDIA_MODEL)
    elif provider == "ollama":
        return ModelWrapper(model=OLLAMA_MODEL)
    else:
        # For local models, use default quantization
        return ModelWrapper(use_quantization=True)


def display_model_info(model_wrapper: ModelWrapper, provider: str):
    """Display model information based on provider."""
    model_info = model_wrapper.get_model_info()

    if provider.lower() == "nvidia":
        main_logger.info(f"📊 Connected to NVIDIA model: {model_info['model']}")
    elif provider.lower() == "ollama":
        main_logger.info(f"📊 Connected to Ollama: {model_info.get('model', 'unknown')}")
    else:
        main_logger.info(f"📊 Using local model: {model_info['model_type']} from {model_info['model_path']}")
        main_logger.info(f"🔧 Device: {model_info['device']}, Quantization: {model_info['quantization']}")


def display_workflow_results_header():
    """Display the workflow results header."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}📊 Workflow Results:{Colors.RESET}")


def display_status_line(label: str, value: str, color: str = Colors.BRIGHT_WHITE):
    """Display a status line with consistent formatting."""
    print(f"{color}{label}: {Colors.BRIGHT_YELLOW}{value}{Colors.RESET}")


def display_boolean_status(label: str, value: bool, count: int = None, details: str = None):
    """Display boolean status with appropriate colors and symbols."""
    status_color = Colors.BRIGHT_GREEN if value else Colors.BRIGHT_RED
    status_symbol = "✅" if value else "❌"
    count_text = f" ({count})" if count is not None else ""
    details_text = f" ({details})" if details else ""
    print(f"{Colors.BRIGHT_WHITE}{label}: {status_color}{status_symbol}{Colors.RESET}{count_text}{details_text}")


def highlight_sql_query(query: str) -> str:
    """Apply SQL syntax highlighting to query text."""
    if not query:
        return query

    highlighted = query.replace('SELECT', f'{Colors.BOLD}{Colors.BRIGHT_BLUE}SELECT{Colors.RESET}')
    highlighted = highlighted.replace('FROM', f'{Colors.BOLD}{Colors.BRIGHT_GREEN}FROM{Colors.RESET}')
    highlighted = highlighted.replace('WHERE', f'{Colors.BOLD}{Colors.BRIGHT_YELLOW}WHERE{Colors.RESET}')
    highlighted = highlighted.replace('ORDER BY', f'{Colors.BOLD}{Colors.BRIGHT_MAGENTA}ORDER BY{Colors.RESET}')
    highlighted = highlighted.replace('LIMIT', f'{Colors.BOLD}{Colors.BRIGHT_CYAN}LIMIT{Colors.RESET}')
    highlighted = highlighted.replace('JOIN', f'{Colors.BOLD}{Colors.BRIGHT_RED}JOIN{Colors.RESET}')
    highlighted = highlighted.replace('INNER JOIN', f'{Colors.BOLD}{Colors.BRIGHT_RED}INNER JOIN{Colors.RESET}')
    highlighted = highlighted.replace('LEFT JOIN', f'{Colors.BOLD}{Colors.BRIGHT_RED}LEFT JOIN{Colors.RESET}')
    highlighted = highlighted.replace('RIGHT JOIN', f'{Colors.BOLD}{Colors.BRIGHT_RED}RIGHT JOIN{Colors.RESET}')

    return highlighted


def display_sql_query(query: str):
    """Display SQL query with syntax highlighting."""
    if query:
        print(f"\n{Colors.BOLD}{Colors.BRIGHT_MAGENTA}🔍 Generated SQL Query:{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")
        highlighted_query = highlight_sql_query(query)
        for line in highlighted_query.split('\n'):
            if line.strip():
                print(f"   {line}")
        print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")
    else:
        print(f"{Colors.BRIGHT_RED}Query: None{Colors.RESET}")


def display_query_plan(plan_preview: str):
    """Display query plan if available."""
    if plan_preview:
        print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}🧠 Query Plan:{Colors.RESET}")
        print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

        # Try to parse and format the plan as JSON
        try:
            plan_data = json.loads(plan_preview) if isinstance(plan_preview, str) else plan_preview

            # Format schema assessment
            if "schema_assessment" in plan_data:
                print(f"{Colors.BRIGHT_WHITE}Schema Assessment:{Colors.RESET}")
                print(f"   {plan_data['schema_assessment']}")
                print("")

            # Format plan steps
            if "plan" in plan_data and isinstance(plan_data["plan"], list):
                print(f"{Colors.BRIGHT_WHITE}Execution Plan:{Colors.RESET}")
                for i, step in enumerate(plan_data["plan"], 1):
                    print(f"   {Colors.BRIGHT_BLUE}{i}.{Colors.RESET} {step}")

        except (json.JSONDecodeError, TypeError):
            # Fallback to plain text if not JSON
            print(f"{Colors.BRIGHT_WHITE}{plan_preview}{Colors.RESET}")

        print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")


def check_embeddings_exist(kb_directory: str = "src/kb") -> bool:
    """
    Check if embeddings exist (ChromaDB files exist).

    Args:
        kb_directory: Directory where ChromaDB is stored

    Returns:
        True if embeddings exist, False otherwise
    """
    kb_path = Path(kb_directory)
    db_file = kb_path / "chroma.sqlite3"

    if db_file.exists():
        main_logger.info("✅ Knowledge base embeddings found and ready to use")
        return True
    else:
        main_logger.error("❌ Knowledge base embeddings not found")
        main_logger.info("💡 Run 'make embeddings' to create the knowledge base embeddings")
        return False


def display_success_message():
    """Display success message."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}✅ Query processed successfully!{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BRIGHT_GREEN}{'='*60}{Colors.RESET}")


def display_welcome_message():
    """Display welcome message and example queries."""
    print("\n" + "="*70)
    print("🚀 Text2Query - Natural Language to Query Processing")
    print("="*70)
    print("Type your query and press Enter.")
    print("Type 'quit' or 'exit' to stop the program.")
    print("="*70)

    print("\n📊 METADATA QUERIES:")
    metadata_queries = [
        "List all databases",
        "Show me all tables in the system",
        "What columns are in the users table?",
        "Describe the database schema",
        "Show available tables in kyc_db",
        "What are the column names in transactions table?"
    ]
    for query in metadata_queries:
        print(f"  • {query}")

    print("\n🔍 DATA QUERIES:")
    data_queries = [
        "Find all customers with pending KYC verification",
        "Show me payment transactions for the last 30 days",
        "Get user profiles who haven't logged in for 90 days",
        "List all orders with their current status",
        "Find users who made payments above 1000 Rs",
        "Get customer details with their KYC status",
        "Show wallet transactions with customer names and amounts"
    ]
    for query in data_queries:
        print(f"  • {query}")

    print("="*70)


def display_workflow_summary(summary, final_state=None):
    """Display workflow summary with consistent formatting."""
    # Check if this is a metadata query
    is_metadata_query = summary['status'] == 'metadata_completed'
    
    if is_metadata_query and final_state and hasattr(final_state, 'metadata_response'):
        display_metadata_response(summary, final_state)
    else:
        display_sql_workflow_summary(summary)


def display_metadata_response(summary, final_state):
    """Display metadata query response."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN}📊 Metadata Query Response:{Colors.RESET}")
    print(f"{Colors.DIM}{'═' * 60}{Colors.RESET}")
    
    # Display the metadata response with proper formatting
    if hasattr(final_state, 'metadata_response') and final_state.metadata_response:
        query_part, response_part = _parse_metadata_response(final_state.metadata_response)
        _display_query_and_response(query_part, response_part)
    else:
        print(f"{Colors.BRIGHT_RED}No metadata response available{Colors.RESET}")
    
    # Display execution time and status
    print(f"\n{Colors.BRIGHT_WHITE}Execution Time: {Colors.BRIGHT_BLUE}{summary.get('execution_time', 'N/A')}{Colors.RESET}")
    print(f"{Colors.BRIGHT_WHITE}Status: {Colors.BRIGHT_GREEN}✅ Successfully completed{Colors.RESET}")


def _parse_metadata_response(metadata_response):
    """Parse metadata response into query and response parts."""
    response_parts = metadata_response.split('\n\nResponse: ', 1)
    if len(response_parts) == 2:
        query_part = response_parts[0].replace('Query: ', '')
        response_part = response_parts[1]
        return query_part, response_part
    return "", metadata_response


def _display_query_and_response(query_part, response_part):
    """Display formatted query and response."""
    if query_part:
        print(f"{Colors.BRIGHT_WHITE}Query:{Colors.RESET} {Colors.BRIGHT_CYAN}{query_part}{Colors.RESET}")
        print()
    
    print(f"{Colors.BRIGHT_WHITE}Response:{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")
    
    # Format each line with appropriate colors
    for line in response_part.split('\n'):
        if line.strip():
            formatted_line = _format_response_line(line)
            print(f"   {formatted_line}")
    
    print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")


def _format_response_line(line):
    """Format a single line of response with appropriate colors."""
    if line.startswith('|') and '|' in line:
        return f"{Colors.BRIGHT_WHITE}{line}{Colors.RESET}"
    elif line.startswith('#') or line.startswith('**'):
        return f"{Colors.BOLD}{Colors.BRIGHT_YELLOW}{line}{Colors.RESET}"
    elif line.startswith('-'):
        return f"{Colors.BRIGHT_GREEN}{line}{Colors.RESET}"
    else:
        return line


def display_sql_workflow_summary(summary):
    """Display SQL workflow summary with consistent formatting."""
    display_workflow_results_header()

    # Status line with color based on validation
    status_color = Colors.BRIGHT_GREEN if 'validated' in summary['status'] else Colors.BRIGHT_RED
    display_status_line("Query", summary['natural_language_query'])
    print(f"{Colors.BRIGHT_WHITE}Status: {status_color}{summary['status']}{Colors.RESET}")
    display_status_line("Retries Left", str(summary['retries_left']))

    # Database info
    db_details = ', '.join(summary['databases']['identified']) if summary['databases']['identified'] else "None"
    display_boolean_status("Databases Identified", summary['databases']['count'] > 0,
                          summary['databases']['count'], db_details)

    # Tables and columns status
    display_boolean_status("Tables Retrieved", summary['tables']['retrieved'], summary['tables']['count'])
    display_boolean_status("Columns Retrieved", summary['columns']['retrieved'], summary['columns']['count'])

    # Query plan status
    display_boolean_status("Query Plan", summary['query_plan']['created'], summary['query_plan']['count'])

    # Execution time
    print(f"{Colors.BRIGHT_WHITE}Execution Time: {Colors.BRIGHT_BLUE}{summary.get('execution_time', 'N/A')}{Colors.RESET}")


def main():
    """Main function for the LangGraph-based text2query workflow."""
    try:
        log_section_header(main_logger, "🚀 TEXT2QUERY WORKFLOW 🚀")

        # Check if knowledge base embeddings exist
        embeddings_ready = check_embeddings_exist(kb_directory=str(KB_DIRECTORY))

        if not embeddings_ready:
            main_logger.error("❌ Knowledge base embeddings not found. Please run 'make embeddings' first.")
            return

        # Initialize the model wrapper
        model_wrapper = create_model_wrapper()

        # Display model information
        display_model_info(model_wrapper, PROVIDER)
        
        # Initialize the workflow
        workflow = Text2QueryWorkflow(model_wrapper, docs_dir="docs")
        
        # Interactive query input
        display_welcome_message()
        
        while True:
            try:
                # Get user input
                user_query = input("\n💬 Enter your query: ").strip()
                
                # Check for exit commands
                if user_query.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                # Check for empty input
                if not user_query:
                    print("❌ Please enter a valid query.")
                    continue

                # Get interaction mode
                print("\n🎯 Choose interaction mode:")
                print("  1. Ask mode - Automatic processing (default)")
                print("  2. Interactive mode - Human-in-the-loop for Agentic selection approval")

                mode_input = input("Enter mode (1 or 2, default is 1): ").strip()

                if mode_input == "2":
                    interaction_mode = "interactive"
                    print("👤 Interactive mode selected - you'll be asked to approve Agent selections")
                else:
                    interaction_mode = "ask"
                    print("🤖 Ask mode selected - automatic processing")

                print("-" * 50)
                
                # Time the workflow execution
                start_time = time.time()
                
                # Process the query through the workflow
                final_state = workflow.process_query(user_query, interaction_mode=interaction_mode)
                
                workflow_time = time.time() - start_time
                
                # Get workflow summary and add execution time
                summary = workflow.get_workflow_summary(final_state)
                summary['execution_time'] = "{:.2f} seconds".format(workflow_time)

                # Display results with consolidated formatting
                display_workflow_summary(summary, final_state)
                
                # Only display SQL-specific sections for non-metadata queries
                if summary['status'] != 'metadata_completed':
                    display_sql_query(summary['query']['query'])
                    display_query_plan(summary['query_plan']['preview'])
                
                display_success_message()
                
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