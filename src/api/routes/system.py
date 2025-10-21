from typing import List, Dict
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/workflow/steps")
def workflow_steps() -> List[Dict[str, str]]:
    steps = [
        {"name": "Router", "description": "Analyzing query type", "emoji": "🎯"},
        {"name": "Metadata Agent", "description": "Processing metadata queries", "emoji": "📊"},
        {"name": "Database Identifier", "description": "Finding relevant databases", "emoji": "🗄️"},
        {"name": "Table Identifier", "description": "Identifying relevant tables", "emoji": "📋"},
        {"name": "Column Identifier", "description": "Finding relevant columns", "emoji": "🔍"},
        {"name": "Query Planner", "description": "Creating query plan", "emoji": "🧠"},
        {"name": "Query Generator", "description": "Generating SQL query", "emoji": "⚡"},
        {"name": "Query Validator", "description": "Validating generated query", "emoji": "✅"},
    ]
    return steps