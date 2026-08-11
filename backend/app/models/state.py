"""
Workflow state and node I/O contract for the text2query agent system.

AgentState is the single typed contract every LangGraph node reads and
writes; AgentResult is what every agent returns (state_updates) back
to the workflow.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.agent_schemas import Query


class AgentType(str, Enum):
    """Types of agents in the system."""
    LLM_ROUTER = "llm_router"
    METADATA_AGENT = "metadata_agent"
    DATABASE_IDENTIFIER = "database_identifier"
    TABLE_SCHEMA_RETRIEVER = "table_schema_retriever"
    COLUMN_IDENTIFIER = "column_identifier"
    SCHEMA_BUILDER = "schema_builder"
    QUERY_PLANNER = "query_planner"
    QUERY_GENERATOR = "query_generator"
    SQL_SAFETY_GUARD = "sql_safety_guard"
    QUERY_VALIDATOR = "query_validator"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"


class AgentState(BaseModel):
    """State maintained throughout the agent workflow."""
    # Input
    natural_language_query: str

    # Routing information
    is_metadata_query: Optional[bool] = None  # Whether this is a metadata query
    dialect: Optional[str] = None  # Dialect of the database to use for the query (eq: sql, postgres, mysql, etc.)

    # Metadata response
    metadata_response: Optional[str] = None  # Response for metadata queries
    metadata_type: Optional[str] = None  # Type of metadata (databases, tables, columns, etc.)

    # Two-tiered schema retrieval
    relevant_databases: List[str] = []  # List of potential databases
    relevant_tables: List[str] = []  # List of potential tables
    relevant_columns: List[str] = []  # List of potential columns

    # Schema context from knowledge base
    schema_context: Optional[Dict[str, Any]] = None  # Comprehensive schema information

    # Query planning
    query_plan: str = ""

    # Generated Query
    generated_query: Optional[Query] = None

    # Deterministic read-only SQL safety check (runs before semantic validation)
    is_sql_safe: Optional[bool] = None
    sql_safety_violation: Optional[str] = None  # Reason the query was rejected, if unsafe

    # Validation
    is_query_valid: bool = False

    # Structured feedback: {"type": "syntax|logic|schema|unknown", "details": str}
    query_validation_feedback: Dict[str, Any] = {}

    # Flow control
    current_step: str = "initialized"
    retries_left: int = 3
    step_retries_left: Dict[str, int] = Field(default_factory=lambda: {
        "database_identifier": 2,
        "table_identifier": 2,
        "column_identifier": 2,
        "schema_builder": 2,
        "query_planner": 2,
        "query_generator": 2,
        "sql_safety_guard": 1,
        "query_validator": 2,
        "metadata_agent": 2,
        "database_human_review": 2,
        "table_human_review": 2,
    })

    # Human-in-the-loop mode
    interaction_mode: str = "ask"  # "interactive" or "ask"
    api_mode: bool = False  # When true, HITL agents emit pending_review for API/UI flow
    human_feedback: Optional[str] = None  # User's feedback on last selection step
    human_approvals: Dict[str, bool] = {}  # e.g., {"databases": True, "tables": False}
    feedback_processed: bool = False  # Whether user feedback modifications have been processed
    last_modification_type: Optional[str] = None  # Type of last modification: 'add', 'remove', 'modify', 'replace', 'approve', 'reject'

    # Routing and diagnostics
    last_error_type: Optional[str] = None  # e.g., 'schema_missing', 'sql_generation_issue', 'insufficient_data'
    user_message: Optional[str] = None  # surfaced to user on early exit

    # API integration: pending review checkpoint info (set by HITL agent under API mode)
    pending_review: Optional[Dict[str, Any]] = None  # {"type": "databases|tables", "items": [...]} when awaiting approval

    # Resume functionality
    is_resuming: bool = False  # Whether this workflow execution is resuming from a previous state
    resume_start_node: Optional[str] = None  # Node to start from when resuming

    class Config:
        arbitrary_types_allowed = True


class AgentResult(BaseModel):
    """Result from an agent execution."""
    success: bool
    message: str
    state_updates: Optional[Dict[str, Any]] = None
