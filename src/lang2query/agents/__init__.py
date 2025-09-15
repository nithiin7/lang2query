"""
Agents package for the refined text2query system.

Contains all specialized agents for the new hybrid architecture:
- Schema Retrieval Agent
- Query Planner Agent
- SQL Generator Agent
- SQL Executor Agent
- Response Generator Agent

All agents use a generic model wrapper that can work with any transformer model.
"""

from .base_agent import BaseAgent
from .column_identifier import ColumnIdentifier
from .database_identifier import DatabaseIdentifierAgent
from .models import (
    AgentMessage,
    AgentResult,
    AgentState,
    AgentType,
    ColumnInfo,
    DatabaseInfo,
    Query,
    SubQuery,
    TableInfo,
)
from .query_generator import QueryGeneratorAgent
from .query_planner import QueryPlannerAgent
from .query_validator import QueryValidatorAgent
from .table_identifier import TableIdentifier

__all__ = [
    "BaseAgent",
    "DatabaseIdentifierAgent",
    "TableIdentifier",
    "ColumnIdentifier",
    "QueryPlannerAgent",
    "QueryGeneratorAgent",
    "QueryValidatorAgent",
    "AgentState",
    "AgentResult",
    "AgentType",
    "DatabaseInfo",
    "TableInfo",
    "ColumnInfo",
    "Query",
    "AgentMessage",
    "SubQuery",
]
