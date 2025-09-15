"""
Database Identifier Agent for the Lang2Query system.

Selects relevant databases for a user query. Minimal implementation uses
available databases discovered from docs/ via ChunksLoader.
"""

import logging
from typing import List

from lang2query.config import DOCS_DIR
from lang2query.utils.chunks_loader import ChunksLoader

from .base_agent import BaseAgent
from .models import AgentResult, AgentState, AgentType

logger = logging.getLogger(__name__)


class DatabaseIdentifierAgent(BaseAgent):
    """Agent responsible for selecting relevant databases for the query."""

    def __init__(self, model_wrapper):
        super().__init__(AgentType.DATABASE_IDENTIFIER, model_wrapper)
        loader = ChunksLoader(str(DOCS_DIR))
        loader.load()
        self._chunks_loader = loader

    def process(self, state: AgentState) -> AgentResult:
        """Identify relevant databases. Minimal strategy: select all available."""
        logger.info(f"🗄️ {self.name}: Identifying relevant databases for the query")
        try:
            available_dbs: List[str] = self._chunks_loader.database_names()
            selected = available_dbs[:5]  # cap to 5 for brevity

            if not selected:
                return AgentResult(
                    success=False,
                    message="No databases available in docs/",
                )

            updates = {
                "relevant_databases": selected,
                "db_retrieved": True,
                "current_step": "databases_identified",
            }
            logger.info(f"🗄️ Selected databases: {', '.join(selected)}")
            return AgentResult(
                success=True, message="Databases identified", state_updates=updates
            )
        except Exception as e:
            logger.error(f"❌ Database identification failed: {e}")
            return AgentResult(
                success=False, message=f"Database identification failed: {str(e)}"
            )
