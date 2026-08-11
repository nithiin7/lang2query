"""
Structured LLM output schemas for the text2query agent system.

Each agent that calls generate_with_llm(schema_class=...) uses one of these
as its constrained output shape. Also includes Query, the generated-query
result type stored on AgentState.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Query(BaseModel):
    """Generated query with metadata."""
    query: str
    database: str
    tables_used: List[str]
    columns_used: List[str]
    explanation: Optional[str] = None
    query_type: str = "generic"  # sql, graphql, rest, etc.


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
