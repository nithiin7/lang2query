"""
API request/response models for the text2query FastAPI routes.
"""

from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Request body for the /query endpoint."""
    query: str
    mode: str = "normal"
