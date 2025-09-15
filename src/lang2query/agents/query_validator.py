"""
Query Validator Agent

A minimal LLM-backed validator that checks whether the generated query
matches the user's intent by asking the model for a simple YES/NO
assessment with a short reason. The agent then updates the workflow
state accordingly.
"""

import logging

from lang2query.utils.logging import log_ai_response

from .base_agent import BaseAgent
from .models import AgentResult, AgentState, AgentType

logger = logging.getLogger(__name__)


class QueryValidatorAgent(BaseAgent):
    """Lightweight validator that compares user query vs generated query."""

    def __init__(self, model_wrapper):
        super().__init__(AgentType.QUERY_VALIDATOR, model_wrapper)

    def process(self, state: AgentState) -> AgentResult:
        """
        Validate whether the generated query matches the user's request.

        Strategy: Use the LLM for a concise YES/NO + reason judgment.
        """
        logger.info("🔍 Performing simple LLM-based query validation")

        if not state.generated_query or not state.generated_query.query:
            logger.error("❌ No generated query available to validate")
            return AgentResult(
                success=False,
                message="Generated query missing; cannot validate",
            )

        user_request = state.natural_language_query
        generated_query_text = state.generated_query.query

        # Build concise schema context selected by previous agents
        schema_info = self._build_selected_schema_info(state)

        prompt = self._build_validation_prompt(state, generated_query_text, schema_info)

        try:
            llm_response = self.generate_with_llm(
                prompt, max_new_tokens=64, do_sample=False
            ).strip()

            log_ai_response(logger, "Query Validator", llm_response)

            is_valid, reason, reason_code = self._parse_llm_judgment(llm_response)

            # Use model-provided code if present; otherwise fallback classification
            issue_type = reason_code
            if not is_valid and not issue_type:
                text = ((reason or "") + " " + llm_response).lower()
                if any(
                    k in text
                    for k in [
                        "missing table",
                        "unknown table",
                        "no table",
                        "table not found",
                        "missing column",
                        "unknown column",
                        "column not found",
                        "schema",
                        "join key",
                        "relationship missing",
                    ]
                ):
                    issue_type = "schema_missing"
                elif any(
                    k in text
                    for k in [
                        "syntax",
                        "invalid sql",
                        "parse",
                        "generation",
                        "ambiguous",
                        "incorrect query",
                        "wrong sql",
                    ]
                ):
                    issue_type = "sql_generation_issue"
                elif any(
                    k in text
                    for k in [
                        "insufficient data",
                        "not enough information",
                        "unclear",
                        "need more details",
                        "cannot determine",
                    ]
                ):
                    issue_type = "insufficient_data"
                else:
                    issue_type = "unknown"

            state_updates = {
                "is_query_valid": is_valid,
                "query_validation_feedback": {
                    "overall_valid": is_valid,
                    "total_issues": 0 if is_valid else 1,
                    "suggestions": (
                        [] if is_valid else ["Regenerate query based on user intent"]
                    ),
                    "llm_judgment": llm_response,
                    "reason": reason,
                    "issue_type": issue_type,
                    "reason_code": issue_type,
                },
                "last_error_type": None if is_valid else issue_type,
                "current_step": "query_validated",
            }

            status_text = "valid" if is_valid else "invalid"
            logger.info(f"✅ Validation completed: {status_text}")

            return AgentResult(
                success=True,
                message=f"Validation result: {status_text}",
                state_updates=state_updates,
            )

        except Exception as e:
            logger.error(f"❌ Query validation failed: {e}")
            return AgentResult(
                success=False,
                message=f"Query validation failed: {str(e)}",
            )

    def _build_validation_prompt(
        self, state: AgentState, generated_query_text: str, schema_info: str
    ) -> str:
        """Create a structured validation prompt with a reason code for routing and selected schema context."""
        return f"""
        You are an evaluator. Decide if the GENERATED QUERY correctly and sufficiently answers the USER REQUEST. Do not be too strict. The query is still valid if it is close to the user request.

        Respond ONLY as a single JSON object with the following schema:
        {{
          "verdict": "YES" | "NO",
          "reason": "reason that can be passed as feedback to the next agent to rectify the issues",
          "reason_code": "one of: schema_missing | sql_generation_issue | insufficient_data | unknown"
        }}

        Semantics of reason_code:
        - schema_missing: Missing/unknown tables, columns, or relationships prevent answering the question.
        - sql_generation_issue: Schema is sufficient but the SQL is syntactically/semantically wrong for the intent.
        - insufficient_data: The user's request lacks necessary details to select schema or create a correct query.
        - unknown: Cannot classify; use as last resort.

        USER REQUEST:
        {state.natural_language_query}

        GENERATED QUERY:
        {generated_query_text}

        SELECTED SCHEMA CONTEXT (from previous agents):
        Databases: {", ".join(state.relevant_databases or [])}
        Tables: {", ".join(state.relevant_tables or [])}
        Columns: {", ".join(state.relevant_columns or [])}

        Detailed Schema (subset for selected tables/columns):
        ```sql
        {schema_info}
        ```
        """

    def _build_selected_schema_info(self, state: AgentState) -> str:
        """Construct a concise schema snippet for the selected databases/tables/columns."""
        try:
            from lang2query.config import DOCS_DIR
            from lang2query.utils.chunks_loader import ChunksLoader

            loader = ChunksLoader(str(DOCS_DIR))
            loader.load()
            return self._build_detailed_schema(
                loader,
                database_names=state.relevant_databases or [],
                table_names=state.relevant_tables or [],
                column_names=state.relevant_columns or [],
            )
        except Exception:
            # Fall back to a minimal description if loader not available
            lines = []
            if state.relevant_databases:
                lines.append("-- Databases: " + ", ".join(state.relevant_databases))
            if state.relevant_tables:
                lines.append("-- Tables: " + ", ".join(state.relevant_tables))
            if state.relevant_columns:
                lines.append("-- Columns: " + ", ".join(state.relevant_columns))
            return "\n".join(lines) or "-- No schema context available"

    def _build_detailed_schema(
        self, loader, database_names, table_names, column_names=None
    ) -> str:
        """Replicate the concise detailed schema builder used by other agents, limited to selections."""
        import logging

        logger = logging.getLogger(__name__)
        schema_lines = []
        if not table_names:
            return "-- No tables selected for schema"
        for db_name in database_names:
            db = loader.databases.get(db_name)
            if not db:
                continue
            relevant_tables = [t for t in db.tables.values() if t.name in table_names]
            if not relevant_tables:
                continue
            schema_lines.append(f"-- Database: {db_name}")
            if getattr(db, "purpose", None):
                schema_lines.append(f"-- Purpose: {db.purpose}")
            schema_lines.append("")
            for table in relevant_tables:
                schema_lines.append(f"CREATE TABLE {table.name} (")
                if getattr(table, "columns", None):
                    column_defs = []
                    for col in table.columns:
                        if column_names and col.name not in column_names:
                            continue
                        col_def = f"    {col.name}"
                        if getattr(col, "data_type", None):
                            col_def += f" {col.data_type}"
                        if getattr(col, "is_primary_key", False):
                            col_def += " PRIMARY KEY"
                        if getattr(col, "is_unique", False):
                            col_def += " UNIQUE"
                        column_defs.append(col_def)
                    if column_defs:
                        schema_lines.append(",\n".join(column_defs))
                    else:
                        schema_lines.append("    -- No relevant columns found")
                else:
                    schema_lines.append("    -- No column information available")
                schema_lines.append(");")
                if getattr(table, "purpose", None):
                    schema_lines.append(f"-- Purpose: {table.purpose}")
                schema_lines.append("")
        if not schema_lines:
            logger.warning("⚠️ No schema information available for selected tables")
            return "-- No schema information available for selected tables"
        return "\n".join(schema_lines)

    def _parse_llm_judgment(self, llm_text: str) -> tuple[bool, str, str]:
        """
        Parse structured model output. Preferred format is JSON with keys:
        - verdict: YES|NO
        - reason: string
        - reason_code: schema_missing|sql_generation_issue|insufficient_data|unknown
        Returns (is_valid, reason, reason_code)
        Fallback to loose parsing if JSON not present.
        """
        text = llm_text.strip()
        # Try JSON first
        try:
            import json
            import re

            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                payload = json.loads(json_match.group(0))
                verdict_raw = str(payload.get("verdict", "")).strip().upper()
                is_valid = verdict_raw == "YES"
                reason = str(payload.get("reason", "")).strip()
                reason_code = str(payload.get("reason_code", "")).strip()
                # sanitize reason_code
                allowed = {
                    "schema_missing",
                    "sql_generation_issue",
                    "insufficient_data",
                    "unknown",
                }
                if reason_code not in allowed:
                    reason_code = "unknown"
                return is_valid, reason, reason_code
        except Exception:
            pass

        # Fallback: simple YES/NO: reason
        normalized = text.lower()
        is_yes = normalized.startswith("yes")
        is_no = normalized.startswith("no")
        reason = text.split(":", 1)[1].strip() if ":" in text else text
        if is_yes:
            return True, reason, "unknown"
        if is_no:
            return False, reason, "unknown"
        return False, text, "unknown"
