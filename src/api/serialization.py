"""
Serialization utilities for converting AgentState to JSON-compatible format for WebSocket transmission.
"""

from typing import Any, Dict
from agents import AgentState


def serialize_agent_state(state: AgentState) -> Dict[str, Any]:
    """
    Convert AgentState to a JSON-serializable dictionary for WebSocket transmission.
    
    Args:
        state: The AgentState object to serialize
        
    Returns:
        Dictionary containing all state fields in JSON-compatible format
    """
    serialized = {}
    
    # Basic fields
    serialized["current_step"] = getattr(state, "current_step", "")
    serialized["retries_left"] = getattr(state, "retries_left", 0)
    serialized["is_metadata_query"] = getattr(state, "is_metadata_query", None)
    serialized["dialect"] = getattr(state, "dialect", None)
    serialized["natural_language_query"] = getattr(state, "natural_language_query", "")
    serialized["interaction_mode"] = getattr(state, "interaction_mode", "ask")
    
    # Database, table, and column information
    serialized["relevant_databases"] = getattr(state, "relevant_databases", []) or []
    serialized["relevant_tables"] = getattr(state, "relevant_tables", []) or []
    serialized["relevant_columns"] = getattr(state, "relevant_columns", []) or []
    
    # Query planning and generation
    serialized["query_plan"] = getattr(state, "query_plan", None)
    
    # Generated query
    generated_query = getattr(state, "generated_query", None)
    if generated_query:
        serialized["generated_query"] = {
            "query": getattr(generated_query, "query", ""),
            "explanation": getattr(generated_query, "explanation", "")
        }
    else:
        serialized["generated_query"] = None
    
    # Validation
    serialized["is_query_valid"] = getattr(state, "is_query_valid", None)
    serialized["query_validation_feedback"] = getattr(state, "query_validation_feedback", None)
    
    # Metadata response
    serialized["metadata_response"] = getattr(state, "metadata_response", None)
    
    # Human feedback fields
    serialized["human_approvals"] = getattr(state, "human_approvals", None)
    serialized["human_feedback"] = getattr(state, "human_feedback", None)
    serialized["pending_review"] = getattr(state, "pending_review", None)
    
    # Error handling
    serialized["last_error_type"] = getattr(state, "last_error_type", None)
    
    # Schema context
    serialized["schema_context"] = getattr(state, "schema_context", None)
    
    return serialized


def create_workflow_state_from_agent_state(state: AgentState) -> Dict[str, Any]:
    """
    Create a WorkflowState-compatible dictionary from AgentState for frontend consumption.
    
    Args:
        state: The AgentState object to convert
        
    Returns:
        Dictionary compatible with frontend WorkflowState interface
    """
    return {
        "current_step": getattr(state, "current_step", ""),
        "retries_left": getattr(state, "retries_left", 0),
        "is_metadata_query": getattr(state, "is_metadata_query", None),
        "dialect": getattr(state, "dialect", None),
        "relevant_databases": getattr(state, "relevant_databases", []) or [],
        "relevant_tables": getattr(state, "relevant_tables", []) or [],
        "relevant_columns": getattr(state, "relevant_columns", []) or [],
        "query_plan": getattr(state, "query_plan", None),
        "generated_query": {
            "query": getattr(state.generated_query, "query", "") if getattr(state, "generated_query", None) else None,
            "explanation": getattr(state.generated_query, "explanation", "") if getattr(state, "generated_query", None) else None
        } if getattr(state, "generated_query", None) else None,
        "is_query_valid": getattr(state, "is_query_valid", None),
        "metadata_response": getattr(state, "metadata_response", None)
        ,
        "pending_review": getattr(state, "pending_review", None),
        "human_approved_databases": getattr(state, "human_approved_databases", None),
        "human_approved_tables": getattr(state, "human_approved_tables", None)
    }