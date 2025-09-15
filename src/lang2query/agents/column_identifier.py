"""
Column Identifier Agent for the refined text2query system.

Identifies relevant columns from the previously identified tables. Mirrors
the output style of TableIdentifier and provides data for downstream agents.
"""

import json
import logging
import re
from typing import Any, Dict, List

from lang2query.config import DOCS_DIR
from lang2query.utils.chunks_loader import ChunksLoader
from lang2query.utils.logging import (
    log_ai_response,
    log_error,
    log_success,
    log_warning,
)

from .base_agent import BaseAgent
from .models import AgentResult, AgentState, AgentType

logger = logging.getLogger(__name__)


class ColumnIdentifier(BaseAgent):
    """Agent responsible for identifying relevant columns for the query."""

    def __init__(self, model_wrapper):
        super().__init__(AgentType.COLUMN_IDENTIFIER, model_wrapper)
        # Load chunks for column information
        loader = ChunksLoader(str(DOCS_DIR))
        loader.load()
        self._chunks_loader = loader

    def process(self, state: AgentState) -> AgentResult:
        """
        Identify relevant columns from previously identified tables.

        Returns the column identification text similar in style to
        the table_identifier's `relevant_tables` content.
        """
        logger.info(f"🧩 {self.name}: Identifying relevant columns from tables")

        try:
            if not state.relevant_tables:
                logger.error("❌ No tables identified for column identification")
                return AgentResult(
                    success=False,
                    message="No tables identified for column identification",
                )

            # Get column details for the selected tables
            table_columns = self._chunks_loader.get_table_columns(
                state.relevant_tables, state.relevant_databases
            )
            logger.info(f"🧩 Table columns: {table_columns}")
            logger.info(f"🧩 Retrieved column details for {len(table_columns)} tables")

            prompt = self._create_column_identification_prompt(
                state=state,
                tables_text=(
                    ", ".join(state.relevant_tables) if state.relevant_tables else ""
                ),
                table_columns=table_columns,
            )

            columns_text = self.generate_with_llm(
                prompt, max_new_tokens=128, do_sample=False
            )
            log_ai_response(logger, "Column Identifier", columns_text)

            # Parse selected columns from the LLM response
            selected_columns: List[str] = []
            try:
                text = (columns_text or "").strip()

                # Try to parse JSON format first (what the LLM is actually generating)
                try:
                    # Extract JSON from the response (look for {...} pattern)
                    json_match = re.search(r"\{.*\}", text, re.DOTALL)
                    if json_match:
                        json_text = json_match.group(0)
                        data = json.loads(json_text)

                        # Handle the new format with "columns" key
                        if "columns" in data and isinstance(data["columns"], dict):
                            for table_name, table_columns in data["columns"].items():
                                if isinstance(table_columns, dict):
                                    for col_name in table_columns.keys():
                                        if col_name:
                                            selected_columns.append(col_name)
                        else:
                            # Handle the old format (direct table mapping)
                            for table_name, table_columns in data.items():
                                if isinstance(table_columns, dict):
                                    for col_name in table_columns.keys():
                                        # Remove leading "-" if present
                                        col_name = col_name.lstrip("-").strip()
                                        if col_name:
                                            selected_columns.append(col_name)

                        log_success(
                            logger,
                            f"Successfully parsed {len(selected_columns)} columns from JSON format",
                        )
                    else:
                        raise ValueError("No JSON found in response")

                except (json.JSONDecodeError, ValueError):
                    # Fallback to the original format parsing
                    if text and "Columns:" in text:
                        # Find the columns section
                        columns_section = text.split("Columns:")[1].strip()
                        lines = columns_section.split("\n")

                        for line in lines:
                            line = line.strip()
                            if line.startswith("- "):
                                # Extract column name (format: "- column_name: reason")
                                column_part = line[2:].split(":")[0].strip()
                                if column_part:
                                    selected_columns.append(column_part)

                        log_success(
                            logger,
                            f"Successfully parsed {len(selected_columns)} columns from text format",
                        )
                    else:
                        log_warning(
                            logger,
                            "LLM response missing expected format (JSON or 'Columns:' section)",
                        )
            except Exception as e:
                log_error(
                    logger, f"Failed to parse column names from LLM response: {e}"
                )
                log_error(logger, f"Raw response: {columns_text}")
                selected_columns = []

            state_updates = {
                "relevant_columns": selected_columns,
                "columns_retrieved": True,
                "current_step": "columns_identified",
            }

            logger.info("✅ Column identifier completed successfully")
            logger.info(
                f"🧩 Selected columns: {', '.join(selected_columns) if selected_columns else 'None'}"
            )
            logger.info(
                f"🧩 Retrieved columns info length: {len(columns_text)} characters"
            )

            return AgentResult(
                success=True,
                message="Columns identified successfully",
                state_updates=state_updates,
            )

        except Exception as e:
            logger.error(f"❌ Column identifier failed: {e}")
            return AgentResult(
                success=False, message=f"Column identifier failed: {str(e)}"
            )

    def _create_column_identification_prompt(
        self,
        state: AgentState,
        tables_text: str,
        table_columns: Dict[str, List[Dict[str, Any]]],
    ) -> str:
        """Create prompt to choose relevant columns from the given tables.

        If available, includes prior validation feedback (rejection reason) to guide retries.
        """
        query = state.natural_language_query

        # Format column details for each table
        columns_details = []
        for table_name, columns in table_columns.items():
            if columns:
                col_list = []
                for col in columns:
                    col_info = f"{col['name']} ({col['data_type']})"
                    if col["is_primary_key"]:
                        col_info += " [PRIMARY KEY]"
                    if col["is_unique"]:
                        col_info += " [UNIQUE]"
                    if col["is_indexed"]:
                        col_info += " [INDEXED]"
                    col_list.append(col_info)
                columns_details.append(f"  {table_name}: {', '.join(col_list)}")
            else:
                columns_details.append(
                    f"  {table_name}: No column information available"
                )

        columns_section = (
            "\n".join(columns_details)
            if columns_details
            else "No column details available"
        )

        # Optional prior feedback context from validator
        feedback = state.query_validation_feedback or {}
        prior_feedback_section = ""
        if not feedback.get("overall_valid", True):
            reason = feedback.get("reason") or feedback.get("llm_judgment")
            if reason:
                prior_feedback_section = f"""
        \nContext From Previous Validation (use to improve selection):\n
        The last generated query was judged INVALID because: "{reason}".\n
        The database and tables are selected by the previous agent with considering this reason.\n
        Choose columns to address this issue fully in the next attempt.\n
        """

        return f"""
        You are a precise schema specialist. Given the user's question and the previously selected tables with their column details,
        choose the specific columns that are necessary to answer the question.

        User Query:
        "{query}"

        {prior_feedback_section}

        Tables selected from Databases by previous agent:
        {tables_text}

        Available Columns for Selected Tables:
        {columns_section}

        Output your response as a JSON object with this exact format:
        {{
          "reasoning": "Brief explanation of why these columns are needed",
          "columns": {{
            "table_name": {{
              "column_name": "reason why this column is needed",
              "column_name": "reason why this column is needed"
            }}
          }}
        }}

        Only include columns that actually exist in the tables above. Do not invent new tables or columns.
        """
