"""WebSocket streaming orchestration for the /ws/query endpoint.

Drives a Text2QueryWorkflow stream over an active WebSocket connection,
handling client cancellation and human-in-the-loop checkpoints along the way.
"""

import asyncio
import json
import time
import uuid

from fastapi import WebSocket

from api.mapping import state_summary_to_query_response
from api.serialization import create_workflow_state_from_agent_state
from models.models import AgentState
from workflow import Text2QueryWorkflow
from workflow.state import StateManager

_STREAM_EXHAUSTED = object()


def _next_state_or_sentinel(stream):
    """Advance a workflow stream, returning a sentinel instead of raising StopIteration.

    Runs on a worker thread via run_in_executor; asyncio Futures refuse to carry a
    StopIteration (PEP 479), so exhaustion has to be signaled with a plain value instead.
    """
    try:
        return next(stream)
    except StopIteration:
        return _STREAM_EXHAUSTED


async def _check_for_cancellation(websocket: WebSocket, timeout: float = 0.01) -> bool:
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


async def _send_state_update(websocket: WebSocket, state: AgentState):
    """Send workflow state update to client."""
    workflow_state = create_workflow_state_from_agent_state(state)
    message = {"type": "state_update", "state": workflow_state}
    await websocket.send_text(json.dumps(message))


async def _send_cancellation_message(
    websocket: WebSocket, message: str = "Workflow cancelled by user"
):
    """Send cancellation confirmation to client."""
    await websocket.send_text(json.dumps({"type": "cancelled", "message": message}))


async def _handle_hitl_checkpoint(
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
            await _send_cancellation_message(
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
        response = state_summary_to_query_response(summary)
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
        if await _check_for_cancellation(websocket):
            print("Workflow cancelled by user")
            await _send_cancellation_message(websocket)
            cancelled = True
            break

        # Get next state from workflow (offloaded to a worker thread so the
        # blocking LLM call inside next() doesn't stall the event loop)
        loop = asyncio.get_running_loop()
        state = await loop.run_in_executor(None, _next_state_or_sentinel, stream)
        if state is _STREAM_EXHAUSTED:
            break

        final_state = state
        update_count += 1
        print(f"Received state update #{update_count}: {state.current_step}")

        # Send state update to client
        try:
            await _send_state_update(websocket, state)
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
                cancelled, new_stream = await _handle_hitl_checkpoint(
                    websocket, state, pending, wf
                )

                if cancelled:
                    break

                if new_stream:
                    stream = new_stream
                    continue

    return cancelled, final_state, update_count
