"""System services for streaming the Text2Query workflow over WebSocket.

Drives a Text2QueryWorkflow stream over an active WebSocket connection,
handling client cancellation and human-in-the-loop checkpoints along the way.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict

from fastapi import WebSocket

from models import AgentState
from modules.query.workflow import Text2QueryWorkflow
from modules.query.workflow.state import StateManager

_STREAM_EXHAUSTED = object()


class SystemServices:
    """WebSocket orchestration, state serialization, and response mapping for workflow runs."""

    @staticmethod
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
        serialized["natural_language_query"] = getattr(
            state, "natural_language_query", ""
        )
        serialized["interaction_mode"] = getattr(state, "interaction_mode", "ask")

        # Database, table, and column information
        serialized["relevant_databases"] = (
            getattr(state, "relevant_databases", []) or []
        )
        serialized["relevant_tables"] = getattr(state, "relevant_tables", []) or []
        serialized["relevant_columns"] = getattr(state, "relevant_columns", []) or []

        # Query planning and generation
        serialized["query_plan"] = getattr(state, "query_plan", None)

        # Generated query
        generated_query = getattr(state, "generated_query", None)
        if generated_query:
            serialized["generated_query"] = {
                "query": getattr(generated_query, "query", ""),
                "explanation": getattr(generated_query, "explanation", ""),
            }
        else:
            serialized["generated_query"] = None

        # Validation
        serialized["is_query_valid"] = getattr(state, "is_query_valid", None)
        serialized["query_validation_feedback"] = getattr(
            state, "query_validation_feedback", None
        )

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

    @staticmethod
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
            "generated_query": (
                {
                    "query": (
                        getattr(state.generated_query, "query", "")
                        if getattr(state, "generated_query", None)
                        else None
                    ),
                    "explanation": (
                        getattr(state.generated_query, "explanation", "")
                        if getattr(state, "generated_query", None)
                        else None
                    ),
                }
                if getattr(state, "generated_query", None)
                else None
            ),
            "is_query_valid": getattr(state, "is_query_valid", None),
            "metadata_response": getattr(state, "metadata_response", None),
            "pending_review": getattr(state, "pending_review", None),
            "human_approved_databases": getattr(
                state, "human_approved_databases", None
            ),
            "human_approved_tables": getattr(state, "human_approved_tables", None),
        }

    @staticmethod
    def state_summary_to_query_response(summary: Dict[str, Any]) -> Dict[str, Any]:
        """Map a workflow summary dict to the API's query response shape."""
        response: Dict[str, Any] = {
            "type": "success",
            "status": summary.get("status"),
            "execution_time": summary.get("execution_time"),
            "is_metadata_query": summary.get("status") == "metadata_completed",
            "query": (summary.get("query", {}) or {}).get("query"),
            "metadata_response": summary.get("metadata_response"),
        }

        dbs = summary.get("databases", {}) or {}
        response["databases"] = {
            "count": dbs.get("count", 0),
            "identified": dbs.get("identified", []) or [],
        }

        tables = summary.get("tables", {}) or {}
        response["tables"] = {
            "retrieved": tables.get("retrieved", False),
            "count": tables.get("count", 0),
            "preview": tables.get("preview"),
        }

        cols = summary.get("columns", {}) or {}
        response["columns"] = {
            "retrieved": cols.get("retrieved", False),
            "count": cols.get("count", 0),
            "preview": cols.get("preview"),
        }

        plan = summary.get("query_plan", {}) or {}
        response["query_plan"] = {"created": plan.get("created", False)}

        val = summary.get("validation", {}) or {}
        response["validation"] = {
            "overall_valid": val.get("overall_valid", False),
            "issues_count": val.get("issues_count", 0),
            "suggestions_count": val.get("suggestions_count", 0),
        }

        return response

    @staticmethod
    def next_state_or_sentinel(stream):
        """Advance a workflow stream, returning a sentinel instead of raising StopIteration.

        Runs on a worker thread via run_in_executor; asyncio Futures refuse to carry a
        StopIteration (PEP 479), so exhaustion has to be signaled with a plain value instead.
        """
        try:
            return next(stream)
        except StopIteration:
            return _STREAM_EXHAUSTED

    @staticmethod
    async def check_for_cancellation(websocket: WebSocket, timeout: float = 0.01) -> bool:
        """Check for cancellation message from client (non-blocking)."""
        try:
            message = await asyncio.wait_for(websocket.receive_text(), timeout=timeout)
            data = json.loads(message)
            if data.get("type") == "cancel":
                print("Received cancellation request from client")
                return True
        except:
            pass
        return False

    @staticmethod
    async def send_state_update(websocket: WebSocket, state: AgentState):
        """Send workflow state update to client."""
        workflow_state = SystemServices.create_workflow_state_from_agent_state(state)
        message = {"type": "state_update", "state": workflow_state}
        await websocket.send_text(json.dumps(message))

    @staticmethod
    async def send_cancellation_message(
        websocket: WebSocket, message: str = "Workflow cancelled by user"
    ):
        """Send cancellation confirmation to client."""
        await websocket.send_text(json.dumps({"type": "cancelled", "message": message}))

    @staticmethod
    async def handle_hitl_checkpoint(
        websocket: WebSocket, state: AgentState, pending: dict, wf: Text2QueryWorkflow
    ):
        """
        Handle human-in-the-loop checkpoint and await user feedback.

        Returns:
            tuple: (cancelled: bool, new_stream: generator or None)
        """
        checkpoint_id = str(uuid.uuid4())

        # Send HITL request to client
        request_msg = {
            "type": "hitl_request",
            "checkpoint": {
                "id": checkpoint_id,
                "review_type": pending.get("type"),
                "items": pending.get("items", []),
            },
        }
        await websocket.send_text(json.dumps(request_msg))

        # Wait for user feedback
        while True:
            feedback_text = await websocket.receive_text()
            feedback = json.loads(feedback_text)

            # Check for cancellation during HITL
            if feedback.get("type") == "cancel":
                print("Received cancellation during HITL review")
                await SystemServices.send_cancellation_message(
                    websocket, "Workflow cancelled by user during review"
                )
                return True, None

            # Ignore non-feedback messages
            if feedback.get("type") != "hitl_feedback":
                continue

            # Ignore feedback for other checkpoints
            fb = feedback.get("payload", feedback)
            if fb.get("checkpointId") != checkpoint_id:
                continue

            # Apply feedback and resume workflow
            StateManager.apply_hitl_feedback(state, fb)
            state.pending_review = None

            # Send acknowledgement
            await websocket.send_text(
                json.dumps({"type": "hitl_feedback_ack", "checkpointId": checkpoint_id})
            )

            # Resume workflow from updated state
            new_stream = wf.resume_from_state(state)
            return False, new_stream

    @staticmethod
    async def send_final_result(
        websocket: WebSocket,
        final_state: AgentState,
        wf: Text2QueryWorkflow,
        start_time: float,
    ):
        """Send final workflow result to client."""
        try:
            summary = wf.get_workflow_summary(final_state)
            summary["execution_time"] = f"{time.time() - start_time:.2f} seconds"
            response = SystemServices.state_summary_to_query_response(summary)
            response["status"] = (
                "Success"
                if summary.get("status")
                in (
                    "workflow_completed",
                    "metadata_completed",
                    "query_validation_completed",
                )
                else summary.get("status")
            )

            final_message = {"type": "final_result", "result": response}
            await websocket.send_text(json.dumps(final_message))
            print("Sent final result")
        except Exception as e:
            print(f"Error sending final result: {e}")
            await websocket.send_text(
                json.dumps(
                    {"type": "error", "message": f"Error sending final result: {str(e)}"}
                )
            )

    @staticmethod
    async def process_workflow_stream(
        websocket: WebSocket,
        wf: Text2QueryWorkflow,
        user_query: str,
        interaction_mode: str,
        start_time: float,
    ):
        """
        Process workflow stream with support for cancellation and HITL checkpoints.

        Returns:
            tuple: (cancelled: bool, final_state: AgentState or None, update_count: int)
        """
        stream = wf.process_query(
            user_query, interaction_mode=interaction_mode, streaming=True
        )
        final_state = None
        update_count = 0
        cancelled = False

        while True:
            # Check for cancellation before processing next state
            if await SystemServices.check_for_cancellation(websocket):
                print("Workflow cancelled by user")
                await SystemServices.send_cancellation_message(websocket)
                cancelled = True
                break

            # Get next state from workflow (offloaded to a worker thread so the
            # blocking LLM call inside next() doesn't stall the event loop)
            loop = asyncio.get_running_loop()
            state = await loop.run_in_executor(
                None, SystemServices.next_state_or_sentinel, stream
            )
            if state is _STREAM_EXHAUSTED:
                break

            final_state = state
            update_count += 1
            print(f"Received state update #{update_count}: {state.current_step}")

            # Send state update to client
            try:
                await SystemServices.send_state_update(websocket, state)
            except Exception as e:
                print(f"Error sending state update #{update_count}: {e}")
                break

            # Handle HITL checkpoint if present
            if interaction_mode == "interactive":
                pending = getattr(state, "pending_review", None)
                if (
                    pending
                    and isinstance(pending, dict)
                    and pending.get("items") is not None
                ):
                    cancelled, new_stream = await SystemServices.handle_hitl_checkpoint(
                        websocket, state, pending, wf
                    )

                    if cancelled:
                        break

                    if new_stream:
                        stream = new_stream
                        continue

        return cancelled, final_state, update_count
