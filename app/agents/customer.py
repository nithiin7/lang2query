import pickle
import re
from operator import add
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

from app.agents.helpers.customer_helper import *
from app.config import KB_CONFIG

load_dotenv()

# Load knowledge base from config
with open(KB_CONFIG["file_path"], "rb") as f:
    knowledge_base = pickle.load(f)


class CustomerAgentState(TypedDict):
    """State for the customer domain agent workflow."""

    user_query: str
    table_lst: list[str]
    table_extract: Annotated[list[str], add]
    column_extract: Annotated[list[str], add]


def extract_subquestions_from_query(user_query: str, table_descriptions: str):
    """Extract subquestions from the user query using table descriptions."""
    response = chain_subquestion.invoke(
        {"tables": table_descriptions, "user_query": user_query}
    ).replace("```", "")

    # Extract the structured response using regex
    match = re.search(r"\[\s*\[.*?\]\s*(,\s*\[.*?\]\s*)*\]", response, re.DOTALL)
    if match:
        result = match.group(0)
        return result
    return "[]"


def resolve_subquestions_to_tables(user_query: str, table_list: list[str]):
    """Resolve subquestions to specific tables based on knowledge base."""
    table_descriptions = []

    for table_name in table_list:
        if table_name in knowledge_base:
            description = knowledge_base[table_name][0]
            table_descriptions.append([table_name, description])

    # Convert to dictionary for easier processing
    table_info = {item[0]: item[1] for item in table_descriptions}

    # Generate subquestions for the tables
    subquestions = extract_subquestions_from_query(user_query, str(table_info))
    return eval(subquestions)


def extract_columns_for_subquestions(main_question: str, subquestion: str, table_columns: str):
    """Extract relevant columns for the identified subquestions."""
    response = chain_column_extractor.invoke(
        {"columns": table_columns, "query": subquestion, "main_question": main_question}
    ).replace("```", "")

    # Extract the structured response
    match = re.search(r"\[\s*\[.*?\]\s*(,\s*\[.*?\]\s*)*\]", response, re.DOTALL)
    if match:
        result = match.group(0)
    else:
        result = "[[]]"

    return result


def process_table_column_extraction(subquestions: list, table_columns: str):
    """Process table and column extraction for all subquestions."""
    extracted_columns = []

    for subquestion in subquestions:
        if len(subquestion) == 0:
            continue

        table_name = subquestion[1]
        if table_name in knowledge_base:
            columns_info = knowledge_base[table_name][1]
            extracted_columns.append([table_name, columns_info])

    return extracted_columns


# Workflow Node Functions


def subquestion_extraction_node(state: CustomerAgentState):
    """Extract subquestions from the user query."""
    user_query = state["user_query"]
    table_list = state["table_lst"]

    subquestions = resolve_subquestions_to_tables(user_query, table_list)
    return {"table_extract": subquestions}


def column_extraction_node(state: CustomerAgentState):
    """Extract relevant columns for the identified subquestions."""
    subquestions = state["table_extract"]
    main_question = state["user_query"]

    extracted_columns = process_table_column_extraction(subquestions, table_columns)
    return {"column_extract": extracted_columns}


# Build the customer agent workflow
customer_agent_builder = StateGraph(CustomerAgentState)

# Add workflow nodes
customer_agent_builder.add_node("subquestion_extraction", subquestion_extraction_node)
customer_agent_builder.add_node("column_extraction", column_extraction_node)

# Define workflow edges
customer_agent_builder.add_edge(START, "subquestion_extraction")
customer_agent_builder.add_edge("subquestion_extraction", "column_extraction")
customer_agent_builder.add_edge("column_extraction", END)

# Compile the workflow
graph_final = customer_agent_builder.compile()
