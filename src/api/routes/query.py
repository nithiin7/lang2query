import os
import time
import json
from typing import Any, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from dotenv import load_dotenv
from config import KB_DIRECTORY
from lib import ModelWrapper
from workflow import Text2QueryWorkflow
from api.mapping import state_summary_to_query_response
from api.serialization import create_workflow_state_from_agent_state
from models.models import AgentState
import uuid

router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    mode: str = "normal"


def _get_workflow() -> Text2QueryWorkflow:
    # Singleton-ish per process; simple module-level cache
    if not hasattr(_get_workflow, "_wf"):
        load_dotenv()

        provider = os.getenv("PROVIDER", "ollama").lower()
        model_name = os.getenv("MODEL")
        base_url = os.getenv("BASE_URL")

        if provider == "ollama":
            if not model_name:
                raise RuntimeError("MODEL is required for PROVIDER=ollama. Set MODEL in .env or environment")
            mw = ModelWrapper(model=model_name, base_url=base_url)
        elif provider == "nvidia":
            mw = ModelWrapper(model=model_name, base_url=base_url)
        else:
            mw = ModelWrapper(use_quantization=True)

        setattr(_get_workflow, "_wf", Text2QueryWorkflow(mw, docs_dir="docs"))

    return getattr(_get_workflow, "_wf")


@router.post("/query")
def query(request: QueryRequest) -> Dict[str, Any]:
    user_query = request.query.strip()
    mode = request.mode

    if not user_query:
        raise HTTPException(status_code=400, detail="query is required")

    if not (KB_DIRECTORY / "chroma.sqlite3").exists():
        raise HTTPException(
            status_code=400,
            detail="Knowledge base embeddings not found. Run 'make embeddings' first."
        )

    start = time.time()
    wf = _get_workflow()
    final_state = wf.process_query(user_query, interaction_mode="ask")

    summary = wf.get_workflow_summary(final_state)
    summary["execution_time"] = f"{time.time() - start:.2f} seconds"
    response = state_summary_to_query_response(summary)
    response["status"] = "Success" if summary.get("status") in ("workflow_completed", "metadata_completed", "query_validation_completed") else summary.get("status")
    return response


async def _check_for_cancellation(websocket: WebSocket, timeout: float = 0.01) -> bool:
    """Check for cancellation message from client (non-blocking)."""
    try:
        import asyncio
        message = await asyncio.wait_for(websocket.receive_text(), timeout=timeout)
        data = json.loads(message)
        if data.get("type") == "cancel":
            print("🛑 Received cancellation request from client")
            return True
    except:
        pass
    return False


async def _send_state_update(websocket: WebSocket, state: AgentState):
    """Send workflow state update to client."""
    workflow_state = create_workflow_state_from_agent_state(state)
    message = {"type": "state_update", "state": workflow_state}
    await websocket.send_text(json.dumps(message))


async def _send_cancellation_message(websocket: WebSocket, message: str = "Workflow cancelled by user"):
    """Send cancellation confirmation to client."""
    await websocket.send_text(json.dumps({"type": "cancelled", "message": message}))


async def _apply_hitl_feedback(state: AgentState, feedback: dict):
    """Apply human feedback to the workflow state."""
    review_type = (feedback.get("review_type") or "").strip()
    action = (feedback.get("action") or "").strip().lower()
    approved_items = feedback.get("approved_items") or []
    feedback_text = feedback.get("feedback_text")

    if review_type not in ("databases", "tables"):
        return

    approvals = dict(getattr(state, 'human_approvals', {}) or {})
    approvals[review_type] = (action == 'approve')
    state.human_approvals = approvals
    state.human_feedback = feedback_text

    if approved_items:
        setattr(state, f"relevant_{review_type}", approved_items)


async def _handle_hitl_checkpoint(websocket: WebSocket, state: AgentState, pending: dict, wf: Text2QueryWorkflow):
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
            "items": pending.get("items", [])
        }
    }
    await websocket.send_text(json.dumps(request_msg))

    # Wait for user feedback
    while True:
        feedback_text = await websocket.receive_text()
        feedback = json.loads(feedback_text)
        
        # Check for cancellation during HITL
        if feedback.get("type") == "cancel":
            print("🛑 Received cancellation during HITL review")
            await _send_cancellation_message(websocket, "Workflow cancelled by user during review")
            return True, None
        
        # Ignore non-feedback messages
        if feedback.get("type") != "hitl_feedback":
            continue
            
        # Ignore feedback for other checkpoints
        fb = feedback.get("payload", feedback)
        if fb.get("checkpointId") != checkpoint_id:
            continue

        # Apply feedback and resume workflow
        await _apply_hitl_feedback(state, fb)
        state.pending_review = None

        # Send acknowledgement
        await websocket.send_text(json.dumps({
            "type": "hitl_feedback_ack",
            "checkpointId": checkpoint_id
        }))

        # Resume workflow from updated state
        new_stream = wf.resume_from_state(state)
        return False, new_stream


async def _send_final_result(websocket: WebSocket, final_state: AgentState, wf: Text2QueryWorkflow, start_time: float):
    """Send final workflow result to client."""
    try:
        summary = wf.get_workflow_summary(final_state)
        summary["execution_time"] = f"{time.time() - start_time:.2f} seconds"
        response = state_summary_to_query_response(summary)
        response["status"] = "Success" if summary.get("status") in (
            "workflow_completed", "metadata_completed", "query_validation_completed"
        ) else summary.get("status")
        
        final_message = {"type": "final_result", "result": response}
        await websocket.send_text(json.dumps(final_message))
        print("📤 Sent final result")
    except Exception as e:
        print(f"❌ Error sending final result: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Error sending final result: {str(e)}"
        }))


async def _process_workflow_stream(websocket: WebSocket, wf: Text2QueryWorkflow, user_query: str, 
                                   interaction_mode: str, start_time: float):
    """
    Process workflow stream with support for cancellation and HITL checkpoints.
    
    Returns:
        tuple: (cancelled: bool, final_state: AgentState or None, update_count: int)
    """
    stream = wf.process_query(user_query, interaction_mode=interaction_mode, streaming=True)
    final_state = None
    update_count = 0
    cancelled = False

    while True:
        # Check for cancellation before processing next state
        if await _check_for_cancellation(websocket):
            print("⛔ Workflow cancelled by user")
            await _send_cancellation_message(websocket)
            cancelled = True
            break

        # Get next state from workflow
        try:
            state = next(stream)
        except StopIteration:
            break

        final_state = state
        update_count += 1
        print(f"📊 Received state update #{update_count}: {state.current_step}")

        # Send state update to client
        try:
            await _send_state_update(websocket, state)
        except Exception as e:
            print(f"❌ Error sending state update #{update_count}: {e}")
            break

        # Handle HITL checkpoint if present
        if interaction_mode == "interactive":
            pending = getattr(state, "pending_review", None)
            if pending and isinstance(pending, dict) and pending.get("items") is not None:
                cancelled, new_stream = await _handle_hitl_checkpoint(websocket, state, pending, wf)
                
                if cancelled:
                    break
                    
                if new_stream:
                    stream = new_stream
                    continue

    return cancelled, final_state, update_count


@router.websocket("/ws/query")
async def websocket_query(websocket: WebSocket):
    """WebSocket endpoint for streaming query processing with HITL support."""
    await websocket.accept()
    
    try:
        # Receive and parse initial query request
        data = await websocket.receive_text()
        query_data = json.loads(data)
        
        msg_type = query_data.get("type", "start")
        payload = query_data if msg_type == "start" else query_data.get("payload", {})
        
        user_query = (payload.get("query") or query_data.get("query") or "").strip()
        mode = (payload.get("mode") or query_data.get("mode") or "normal")
        
        # Validate query
        if not user_query:
            await websocket.send_text(json.dumps({"type": "error", "message": "query is required"}))
            return

        # Validate knowledge base
        if not (KB_DIRECTORY / "chroma.sqlite3").exists():
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Knowledge base embeddings not found. Run 'make embeddings' first."
            }))
            return

        # Get workflow instance and send connection confirmation
        wf = _get_workflow()
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "WebSocket connected, starting query processing..."
        }))
        
        # Process workflow with streaming
        start_time = time.time()
        interaction_mode = "interactive" if mode == "interactive" else "ask"
        
        print(f"🔄 Starting workflow streaming for query: {user_query[:50]}...")
        
        cancelled, final_state, update_count = await _process_workflow_stream(
            websocket, wf, user_query, interaction_mode, start_time
        )

        # Send final result or cancellation message
        if cancelled:
            print(f"⛔ Workflow cancelled after {update_count} updates")
        elif final_state:
            print(f"✅ Workflow streaming completed. Total updates: {update_count}")
            await _send_final_result(websocket, final_state, wf, start_time)
        
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Processing error: {str(e)}"
            }))
        except Exception as send_error:
            print(f"Error sending error message: {send_error}")
    finally:
        try:
            if websocket.client_state.name != "CLOSED":
                await websocket.close()
                print("🔌 WebSocket closed gracefully")
        except Exception as close_error:
            print(f"Error closing WebSocket: {close_error}")