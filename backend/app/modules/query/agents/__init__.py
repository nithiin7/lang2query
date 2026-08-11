"""
Agents package for the refined text2query system.

Contains all specialized agents for the new hybrid architecture:
- Router Agent
- Metadata Agent
- Database Identifier Agent
- Table Identifier Agent
- Column Identifier Agent
- Schema Retrieval Agent
- Query Planner Agent
- Query Generator Agent
- Query Validator Agent

All agents use a generic model wrapper that can work with any transformer model.
"""

from models.models import AgentResult, AgentState, AgentType, Query

from .agent_utils import AgentUtils
from .base_agent import BaseAgent
from .column_identifier import ColumnIdentifier
from .database_identifier import DatabaseIdentifierAgent
from .human_in_the_loop import HumanInTheLoopAgent
from .metadata_agent import MetadataAgent
from .query_generator import QueryGeneratorAgent
from .query_planner import QueryPlannerAgent
from .query_validator import QueryValidatorAgent
from .router import RouterAgent
from .schema_builder import SchemaBuilderAgent
from .sql_safety_guard import SQLSafetyGuardAgent
from .table_identifier import TableIdentifier

__all__ = [
    "BaseAgent",
    "AgentUtils",
    "RouterAgent",
    "MetadataAgent",
    "DatabaseIdentifierAgent",
    "TableIdentifier",
    "ColumnIdentifier",
    "SchemaBuilderAgent",
    "QueryPlannerAgent",
    "QueryGeneratorAgent",
    "SQLSafetyGuardAgent",
    "QueryValidatorAgent",
    "AgentState",
    "AgentResult",
    "AgentType",
    "Query",
    "HumanInTheLoopAgent",
]
