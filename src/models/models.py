"""
Data models for the text2query agent system.

Defines the state structure and message types used by the agents.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


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
    QUERY_VALIDATOR = "query_validator"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"


class Query(BaseModel):
    """Generated query with metadata."""
    query: str
    database: str
    tables_used: List[str]
    columns_used: List[str]
    explanation: Optional[str] = None
    query_type: str = "generic"  # sql, graphql, rest, etc.


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


class RoutingInfo(BaseModel):
    """Routing information from the router agent."""
    is_metadata_query: bool = Field(default=False, description="Whether this is a metadata query")
    dialect: str = Field(default="sql", description="The dialect of the database to use for the query (eq: sql, postgres, mysql, etc.)")


class ColumnSelection(BaseModel):
    """Column selection result from the column identifier agent."""
    reasoning: str = Field(description="A detailed string explaining your column selection process, referencing specific column purposes and key columns considered")
    columns: Dict[str, Dict[str, str]] = Field(description="A dictionary mapping table names to dictionaries of column names and reasons for selection")


class DatabaseSelection(BaseModel):
    """Database selection result from the database identifier agent."""
    reasoning: str = Field(description="A detailed string explaining your database selection process, referencing specific database purposes and key tables considered")
    database_names: List[str] = Field(description="An array of strings containing the exact database names to use")


class QueryPlan(BaseModel):
    """Query plan result from the query planner agent."""
    schema_assessment: str = Field(description="A detailed string explaining your schema assessment process, referencing specific schema purposes and key tables considered")
    plan: List[str] = Field(description="An array of strings containing the exact query plan to use")


class ValidationReasonCode(str, Enum):
    """Reason codes for query validation results."""
    ACCEPTED = "accepted"
    ACCEPTED_WITH_MINOR_ISSUES = "accepted_with_minor_issues"
    SCHEMA_MISSING = "schema_missing"
    SQL_GENERATION_ISSUE = "sql_generation_issue"
    INSUFFICIENT_DATA = "insufficient_data"
    QUERY_SCOPE_ISSUE = "query_scope_issue"
    DATA_TYPE_MISMATCH = "data_type_mismatch"
    JOIN_RELATIONSHIP_ERROR = "join_relationship_error"
    UNKNOWN = "unknown"


class QueryValidation(BaseModel):
    """Query validation result from the query validator agent."""
    verdict: str = Field(description="The verdict of the query validation (YES or NO)")
    reason: str = Field(description="The reason for the query validation (e.g. 'The query is valid because it uses the correct tables and columns')")
    reason_code: ValidationReasonCode = Field(description="The reason code for the query validation (e.g. 'accepted', 'accepted_with_minor_issues', 'schema_missing', 'sql_generation_issue', 'insufficient_data', 'query_scope_issue', 'data_type_mismatch', 'join_relationship_error', 'unknown')")

    @field_validator('verdict')
    @classmethod
    def validate_verdict(cls, v):
        if v.upper() not in ['YES', 'NO']:
            raise ValueError('verdict must be either "YES" or "NO"')
        return v.upper()


class TableSelection(BaseModel):
    """Table selection result from the table identifier agent."""
    reasoning: str = Field(description="A detailed string explaining your table selection process, referencing specific table purposes and key columns considered")
    table_names: List[str] = Field(description="An array of strings containing the exact table names to use in the format: [database_name1.table_name1, database_name2.table_name2, database_name3.table_name3, ...]")


class HumanFeedback(BaseModel):
    """Human feedback result from the human-in-the-loop agent."""
    selected_values: List[str] = Field(description="Items from the current selection that the user wants to keep. Empty list means user wants to replace all items.")
    suggested_values: List[str] = Field(description="Additional items the user wants to add to the selection. These are new items not in the current selection.")
    approval_status: str = Field(description="Whether the user approves proceeding with the selection. Must be 'APPROVE', 'MODIFY', or 'REJECT'")
    feedback_summary: str = Field(description="A concise summary of what the user wants to change or their approval")
    modification_type: str = Field(description="The type of modification requested. Must be one of: 'approve' (no changes), 'replace' (use only selected_values), 'add' (add suggested_values to current), 'remove' (remove items not in selected_values), 'modify' (general changes needed)")
    valid_suggestions: List[str] = Field(default_factory=list, description="Suggested items that were validated and exist in the knowledge base")
    invalid_suggestions: List[str] = Field(default_factory=list, description="Suggested items that were not found in the knowledge base")

    @field_validator('approval_status')
    @classmethod
    def validate_approval_status(cls, v):
        if v.upper() not in ['APPROVE', 'MODIFY', 'REJECT']:
            raise ValueError('approval_status must be APPROVE, MODIFY, or REJECT')
        return v.upper()

    @field_validator('modification_type')
    @classmethod
    def validate_modification_type(cls, v):
        valid_types = ['approve', 'replace', 'add', 'remove', 'modify']
        if v.lower() not in valid_types:
            raise ValueError(f'modification_type must be one of: {valid_types}')
        return v.lower()


class AgentResult(BaseModel):
    """Result from an agent execution."""
    success: bool
    message: str
    state_updates: Optional[Dict[str, Any]] = None