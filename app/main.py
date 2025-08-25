import pickle
from datetime import datetime
from typing import TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph
from sqlalchemy import create_engine

from app.agents.customer import graph_final
from app.agents.helpers.customer_helper import (
    chain_filter_extractor,
    chain_query_extractor,
    chain_query_validator,
)
from app.agents.router import route_query_to_domains
from app.services.fuzzy import apply_fuzzy_matching_to_filters
from app.config import (
    get_database_config,
    get_domain_config,
    get_table_config,
    KB_CONFIG,
    validate_config,
)

# Validate configuration on startup
validate_config()

# Get configuration
database_config = get_database_config()
domain_config = get_domain_config()
table_config = get_table_config()

# Database connection
database_engine = create_engine(database_config["connection_string"])

# Load knowledge base
with open(KB_CONFIG["file_path"], "rb") as f:
    knowledge_base = pickle.load(f)


def deduplicate_extracted_columns(agent_outputs):
    """Remove duplicate columns extracted by different agents."""
    seen_columns = set()
    unique_columns = []

    for agent_key in ("cust_out", "order_out", "product_out"):
        if agent_key in agent_outputs:
            for column_item in agent_outputs[agent_key]["column_extract"]:
                column_key = tuple(column_item)
                if column_key not in seen_columns:
                    unique_columns.append(column_item)
                    seen_columns.add(column_key)

    return unique_columns


class QueryProcessingState(TypedDict):
    """State for the query processing workflow."""

    user_query: str
    routed_domains: list[str]
    customer_agent_output: str
    orders_agent_output: str
    product_agent_output: str
    extracted_columns: str
    filter_conditions: list[str]
    fuzzy_matched_filters: list[str]
    generated_query: str
    validated_query: str


# Workflow Node Functions


def route_query_to_domains_node(state: QueryProcessingState):
    """Route user query to appropriate domain agents."""
    user_query = state["user_query"]
    routed_domains = route_query_to_domains(user_query)
    return {"routed_domains": eval(routed_domains)}


def determine_routing_path(state: QueryProcessingState):
    """Determine which domain agents should process the query."""
    routed_domains = state["routed_domains"]
    print(f"Routing query to {routed_domains} domain agents")
    return routed_domains


def should_apply_fuzzy_filtering(state: QueryProcessingState):
    """Check if fuzzy filtering is needed based on filter conditions."""
    if len(state["filter_conditions"]) == 1:
        return "no"
    else:
        return "yes"


def process_customer_domain(state: QueryProcessingState):
    """Process query using customer domain agent."""
    user_query = state["user_query"]
    print("Extracting relevant tables and columns from customer domain agent...")
    agent_output = graph_final.invoke(
        {"user_query": user_query, "table_lst": table_config["customer_tables"]}
    )
    return {"customer_agent_output": agent_output}


def process_orders_domain(state: QueryProcessingState):
    """Process query using orders domain agent."""
    user_query = state["user_query"]
    print("Extracting relevant tables and columns from orders domain agent...")
    agent_output = graph_final.invoke(
        {"user_query": user_query, "table_lst": table_config["orders_tables"]}
    )
    return {"orders_agent_output": agent_output}


def process_product_domain(state: QueryProcessingState):
    """Process query using product domain agent."""
    user_query = state["user_query"]
    print(f"Processing query: {user_query}")
    print("Extracting relevant tables and columns from product domain agent...")
    agent_output = graph_final.invoke(
        {"user_query": user_query, "table_lst": table_config["product_tables"]}
    )
    print(f"Product agent output: {agent_output}")
    return {"product_agent_output": agent_output}


def extract_filter_conditions(state: QueryProcessingState):
    """Extract and analyze filter conditions from the query."""
    user_query = state["user_query"]
    agent_outputs = {}
    column_data = []

    for agent_key in ["orders_agent_output", "customer_agent_output", "product_agent_output"]:
        if agent_key in state:
            agent_outputs[agent_key] = state.get(agent_key)
            column_data.append(state[agent_key])

    unique_columns = deduplicate_extracted_columns(agent_outputs)
    print("Analyzing filter conditions...")

    filter_response = chain_filter_extractor.invoke(
        {"columns": str(unique_columns), "query": user_query}
    ).replace("```", "")

    return {"filter_conditions": eval(filter_response), "extracted_columns": str(unique_columns)}


def apply_fuzzy_matching(state: QueryProcessingState):
    """Apply fuzzy matching to filter values for better accuracy."""
    filter_conditions = state["filter_conditions"]
    print("Applying fuzzy matching to filter values...")
    matched_filters = apply_fuzzy_matching_to_filters(filter_conditions)
    print("Fuzzy matching completed")
    return {"fuzzy_matched_filters": matched_filters}


def generate_query(state: QueryProcessingState):
    """Generate the final query in the target language."""
    user_query = state["user_query"]
    table_columns = state["extracted_columns"]

    if state.get("fuzzy_matched_filters"):
        filter_conditions = state.get("fuzzy_matched_filters")
    else:
        filter_conditions = ""

    print("Generating query...")
    generated_query = chain_query_extractor.invoke(
        {"columns": table_columns, "query": user_query, "filters": filter_conditions}
    )
    return {"generated_query": generated_query}


def validate_generated_query(state: QueryProcessingState):
    """Validate and finalize the generated query."""
    print("Validating and finalizing query...")
    validated_query = chain_query_validator.invoke(
        {
            "columns": state["extracted_columns"],
            "query": state["user_query"],
            "filters": state.get("fuzzy_matched_filters"),
            "sql_query": state["generated_query"],
        }
    )
    return {"validated_query": validated_query}


# Build the workflow graph
query_workflow_builder = StateGraph(QueryProcessingState)

# Add workflow nodes
query_workflow_builder.add_node("route_query", route_query_to_domains_node)
query_workflow_builder.add_node("customer_domain", process_customer_domain)
query_workflow_builder.add_node("orders_domain", process_orders_domain)
query_workflow_builder.add_node("product_domain", process_product_domain)
query_workflow_builder.add_node("extract_filters", extract_filter_conditions)
query_workflow_builder.add_node("fuzzy_filtering", apply_fuzzy_matching)
query_workflow_builder.add_node("query_generation", generate_query)
query_workflow_builder.add_node("query_validation", validate_generated_query)

# Define workflow edges
query_workflow_builder.add_edge(START, "route_query")

query_workflow_builder.add_conditional_edges(
    "route_query", determine_routing_path, ["customer_domain", "orders_domain", "product_domain"]
)

query_workflow_builder.add_edge("customer_domain", "extract_filters")
query_workflow_builder.add_edge("orders_domain", "extract_filters")
query_workflow_builder.add_edge("product_domain", "extract_filters")

query_workflow_builder.add_conditional_edges(
    "extract_filters",
    should_apply_fuzzy_filtering,
    {"no": "query_generation", "yes": "fuzzy_filtering"},
)

query_workflow_builder.add_edge("fuzzy_filtering", "query_generation")
query_workflow_builder.add_edge("query_generation", "query_validation")
query_workflow_builder.add_edge("query_validation", END)

# Compile the workflow
query_workflow = query_workflow_builder.compile()


def safe_extract_value(record, key):
    """Safely extract a value from a record."""
    return record.get(key) if key in record else None


def process_natural_language_query(user_query: str):
    """Process a natural language query and return the generated query."""
    workflow_result = query_workflow.invoke({"user_query": user_query})

    # Normalize the results for logging/analysis
    normalized_results = []
    normalized_data = {
        "user_query": workflow_result.get("user_query"),
        "routed_domains": workflow_result.get("routed_domains"),
        "customer_agent_output": workflow_result.get("customer_agent_output")
        if workflow_result.get("customer_agent_output")
        else None,
        "orders_agent_output": workflow_result.get("orders_agent_output")
        if workflow_result.get("customer_agent_output")
        else None,
        "product_agent_output": workflow_result.get("product_agent_output")
        if workflow_result.get("customer_agent_output")
        else None,
        "extracted_columns": workflow_result.get("extracted_columns"),
        "filter_conditions": workflow_result.get("filter_conditions"),
        "generated_query": workflow_result.get("generated_query"),
        "validated_query": workflow_result.get("validated_query"),
    }

    normalized_results.append(normalized_data)

    # Create DataFrame for analysis
    results_df = pd.DataFrame(normalized_results)
    results_df["processed_at"] = datetime.now()
    results_df["version"] = "v1"

    return results_df, workflow_result


def main():
    """Main function demonstrating the query processing workflow."""
    # Example simple query
    simple_query = "Give me list of customers from São Paulo state that made at least 1 payment through credit card"
    results_df, workflow_result = process_natural_language_query(simple_query)

    # Example complex query
    complex_query = """For each state, compute the average review score for orders that were delayed by more than 5 days (based on estimated delivery), 
and where the product price was above the average price of its category. Only include states with at least 100 such orders, 
and rank them from highest to lowest average score."""

    complex_results_df, complex_workflow_result = process_natural_language_query(complex_query)

    # Collection of test queries for validation
    test_queries = [
        "What are the total number of orders made?",
        """For each state, compute the average review score for orders that were delayed by more than 5 days (based on estimated delivery), 
    and where the product price was above the average price of its category. Only include states with at least 100 such orders, 
    and rank them from highest to lowest average score.""",
        """Among sellers who have sold at least 50 items, which seller had the highest percentage of orders with a 5-star review and what is that percentage? 
    Only include orders where the product was delivered on time (i.e., delivered on or before the estimated delivery date), and the payment was made in installments.""",
        """For each state, compute the average review score for orders that were delayed by more than 5 days (based on estimated delivery),
    and where the product price was above the average price of its category.
    Only include states with at least 100 such orders, and rank them from highest to lowest average score.""",
    ]

    print("Query processing workflow completed successfully!")


if __name__ == "__main__":
    main()
