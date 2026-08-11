import json
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from api.dependencies import get_workflow
from api.mapping import state_summary_to_query_response
from api.websocket_query import process_workflow_stream, send_final_result
from core.config import KB_DIRECTORY
from models.models import QueryRequest

router = APIRouter()


def _kb_ready() -> bool:
    return (KB_DIRECTORY / "chroma.sqlite3").exists()


@router.post("/query")
def query(request: QueryRequest) -> Dict[str, Any]:
    user_query = request.query.strip()

    if not user_query:
        raise HTTPException(status_code=400, detail="query is required")

    if not _kb_ready():
        raise HTTPException(
            status_code=400,
            detail="Knowledge base embeddings not found. Run 'make embeddings' first.",
        )

    start = time.time()
    wf = get_workflow()
    final_state = wf.process_query(user_query, interaction_mode="ask")

    summary = wf.get_workflow_summary(final_state)
    summary["execution_time"] = f"{time.time() - start:.2f} seconds"
    response = state_summary_to_query_response(summary)
    response["status"] = (
        "Success"
        if summary.get("status")
        in ("workflow_completed", "metadata_completed", "query_validation_completed")
        else summary.get("status")
    )
    return response


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
        mode = payload.get("mode") or query_data.get("mode") or "normal"

        # Validate query
        if not user_query:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "query is required"})
            )
            return

        # Validate knowledge base
        if not _kb_ready():
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Knowledge base embeddings not found. Run 'make embeddings' first.",
                    }
                )
            )
            return

        # Get workflow instance and send connection confirmation
        wf = get_workflow()
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connected",
                    "message": "WebSocket connected, starting query processing...",
                }
            )
        )

        # Process workflow with streaming
        start_time = time.time()
        interaction_mode = "interactive" if mode == "interactive" else "ask"

        print(f"Starting workflow streaming for query: {user_query[:50]}...")

        cancelled, final_state, update_count = await process_workflow_stream(
            websocket, wf, user_query, interaction_mode, start_time
        )

        # Send final result or cancellation message
        if cancelled:
            print(f"Workflow cancelled after {update_count} updates")
        elif final_state:
            print(f"Workflow streaming completed. Total updates: {update_count}")
            await send_final_result(websocket, final_state, wf, start_time)

    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "message": f"Processing error: {str(e)}"})
            )
        except Exception as send_error:
            print(f"Error sending error message: {send_error}")
    finally:
        try:
            if websocket.client_state.name != "CLOSED":
                await websocket.close()
                print("WebSocket closed gracefully")
        except Exception as close_error:
            print(f"Error closing WebSocket: {close_error}")
