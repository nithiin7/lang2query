"""
Data models for the text2query agent system.

Defines the state structure and message types used by the agents.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Types of agents in the system."""

    DATABASE_IDENTIFIER = "database_identifier"
    TABLE_SCHEMA_RETRIEVER = "table_schema_retriever"
    COLUMN_IDENTIFIER = "column_identifier"
    QUERY_PLANNER = "query_planner"
    QUERY_GENERATOR = "query_generator"
    QUERY_VALIDATOR = "query_validator"
    WORKFLOW_SUCCESS = "success"


class DatabaseInfo(BaseModel):
    """Information about a database."""

    name: str
    description: str
    type: str  # mysql, postgresql, oracle, etc.
    connection_string: Optional[str] = None


class TableInfo(BaseModel):
    """Information about a table."""

    name: str
    description: str
    database: str
    columns: List[str] = []
    row_count: Optional[int] = None


class ColumnInfo(BaseModel):
    """Information about a column."""

    name: str
    data_type: str
    description: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    nullable: bool = True


class Query(BaseModel):
    """Generated query with metadata."""

    query: str
    database: str
    tables_used: List[str]
    columns_used: List[str]
    confidence_score: float = Field(ge=0.0, le=1.0)
    explanation: Optional[str] = None
    query_type: str = "generic"  # sql, graphql, rest, etc.


class AgentMessage(BaseModel):
    """Message passed between agents."""

    sender: AgentType
    receiver: AgentType
    content: str
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class SubQuery(BaseModel):
    """A sub-query generated from the main query breakdown."""

    id: str
    query: str
    intent: str  # 'database', 'tables', 'columns'
    priority: int = 1
    dependencies: List[str] = []  # IDs of other sub-queries this depends on


class AgentState(BaseModel):
    """State maintained throughout the agent workflow."""

    # Input
    natural_language_query: str

    # Two-tiered schema retrieval
    relevant_databases: List[str] = []  # List of potential databases
    relevant_tables: List[str] = []  # List of potential tables
    relevant_columns: List[str] = []  # List of potential columns

    # Table to database mapping
    related_db: Dict[str, str] = {}  # Maps table names to their database names

    # Retrieval flags for agent context
    db_retrieved: bool = False
    tables_retrieved: bool = False
    columns_retrieved: bool = False

    # Query planning
    query_plan: str = ""

    # Generated Query
    generated_query: Optional[Query] = None

    # Validation
    is_query_valid: bool = False
    # Structured feedback: {"type": "syntax|logic|schema|unknown", "details": str}
    query_validation_feedback: Dict[str, Any] = {}

    # Flow control
    current_step: str = "initialized"
    retries_left: int = 3

    # Metadata
    confidence_score: float = 0.0
    iteration_count: int = 0

    # Routing and diagnostics
    last_error_type: Optional[str] = (
        None  # e.g., 'schema_missing', 'sql_generation_issue', 'insufficient_data'
    )
    route_to: Optional[str] = (
        None  # one of nodes: 'table_identifier', 'query_planner', 'database_identifier', 'end'
    )
    user_message: Optional[str] = None  # surfaced to user on early exit

    class Config:
        arbitrary_types_allowed = True


class AgentResult(BaseModel):
    """Result from an agent execution."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    next_agent: Optional[AgentType] = None
    state_updates: Optional[Dict[str, Any]] = None

    # Flow control
    needs_more_data: bool = False
    data_requirements: List[str] = []
    should_go_back_to: Optional[AgentType] = None
    confidence_level: str = "medium"  # low, medium, high
