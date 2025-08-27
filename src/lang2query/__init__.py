"""Lang2Query: A natural language to query agentic AI system."""

__version__ = "0.1.0"
__author__ = "Nithin Pradeep"
__email__ = "nithinp150@gmail.com"

from .agents.query_agent import QueryGenerationAgent, SQLQuery
from .core.workflow import run_query_workflow
from .utils.db_parser import Column, DatabaseSchema, MarkdownDBParser, Table

__all__ = [
    "run_query_workflow",
    "QueryGenerationAgent",
    "SQLQuery",
    "MarkdownDBParser",
    "DatabaseSchema",
    "Table",
    "Column",
]
