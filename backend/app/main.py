import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.logging import setup_colored_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan hook: configure colored logging on startup.

    Args:
        app: The FastAPI application instance.
    """
    # Startup
    setup_colored_logging()
    yield
    # Shutdown
    pass


def create_app() -> FastAPI:
    """Build and configure the Text2Query FastAPI application.

    Returns:
        The configured FastAPI app, with CORS middleware and all routers registered.
    """
    # Load environment from .env at project root if present
    load_dotenv()

    app = FastAPI(
        title="Text2Query API",
        description="API for converting natural language to SQL queries",
        version="1.0.0",
        lifespan=lifespan,
    )

    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from api.routes.routes import query_router, system_router

    app.include_router(system_router)
    app.include_router(query_router)

    return app


def main() -> None:
    """CLI entrypoint: build the app and serve it with uvicorn using API_HOST/API_PORT."""
    import uvicorn

    app = create_app()
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
