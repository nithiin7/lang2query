from typing import Dict, List

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/workflow/steps")
def workflow_steps() -> List[Dict[str, str]]:
    steps = [
        {"name": "Router", "description": "Analyzing query type"},
        {"name": "Metadata Agent", "description": "Processing metadata queries"},
        {"name": "Database Identifier", "description": "Finding relevant databases"},
        {"name": "Table Identifier", "description": "Identifying relevant tables"},
        {"name": "Column Identifier", "description": "Finding relevant columns"},
        {"name": "Query Planner", "description": "Creating query plan"},
        {"name": "Query Generator", "description": "Generating SQL query"},
        {"name": "Query Validator", "description": "Validating generated query"},
    ]
    return steps
