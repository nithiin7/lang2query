from typing import Any, Dict


def state_summary_to_query_response(summary: Dict[str, Any]) -> Dict[str, Any]:
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