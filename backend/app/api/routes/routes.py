"""Route registration for the Text2Query API.

Each sibling module defines one FastAPI `APIRouter` for a related set of
endpoints. `create_app()` registers them via this module rather than
importing `api.routes.query` / `api.routes.system` directly.
"""

from api.routes.query import router as query_router
from api.routes.system import router as system_router

__all__ = ["query_router", "system_router"]
