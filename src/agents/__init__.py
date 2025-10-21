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

from .base_agent import BaseAgent
from .agent_utils import AgentUtils
from .router import RouterAgent
from .metadata_agent import MetadataAgent
from .database_identifier import DatabaseIdentifierAgent
from .table_identifier import TableIdentifier
from .column_identifier import ColumnIdentifier
from .schema_builder import SchemaBuilderAgent
from .query_planner import QueryPlannerAgent
from .query_generator import QueryGeneratorAgent
from .query_validator import QueryValidatorAgent
from .human_in_the_loop import HumanInTheLoopAgent
from models.models import (
    AgentState, 
    AgentResult, 
    AgentType, 
    Query
)

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
    "QueryValidatorAgent",
    "AgentState",
    "AgentResult",
    "AgentType",
    "Query",
    "HumanInTheLoopAgent"
] 