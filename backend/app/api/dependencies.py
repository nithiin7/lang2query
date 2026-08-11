"""Shared FastAPI dependency providers for the query API routes."""

import os

from dotenv import load_dotenv

from ai.llm import ModelWrapper
from modules.query.workflow import Text2QueryWorkflow


def get_workflow() -> Text2QueryWorkflow:
    """Return the process-wide Text2QueryWorkflow instance, building it on first use."""
    if not hasattr(get_workflow, "_wf"):
        load_dotenv()

        provider = os.getenv("PROVIDER", "ollama").lower()
        model_name = os.getenv("MODEL")
        base_url = os.getenv("BASE_URL")

        if provider == "ollama":
            if not model_name:
                raise RuntimeError(
                    "MODEL is required for PROVIDER=ollama. Set MODEL in .env or environment"
                )
            mw = ModelWrapper(model=model_name, base_url=base_url)
        else:
            mw = ModelWrapper(use_quantization=True)

        setattr(get_workflow, "_wf", Text2QueryWorkflow(mw, docs_dir="docs"))

    return getattr(get_workflow, "_wf")
