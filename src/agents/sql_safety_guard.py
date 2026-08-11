"""
SQL Safety Guard

A deterministic, non-LLM check that runs after query generation and before
semantic validation. It parses the generated SQL with sqlglot and rejects
anything whose root statement isn't a read-only SELECT (including
UNION/INTERSECT/EXCEPT and CTE-wrapped selects), and anything that contains
more than one statement (semicolon-stacked injection).

This is deliberately not keyword/regex based: a blacklist of words like
"drop" or "delete" is trivially defeated by casing, comments, or string
literals that merely contain those words. Parsing the SQL into an AST and
checking the statement's real type closes that gap.

A failure here is a hard stop, not a candidate for the semantic
retry-and-regenerate loop (see workflow.py) — see CLAUDE.md and the PR
description for why safety and semantic failures are routed differently.
"""

import logging
from typing import Optional, Tuple

import sqlglot
from sqlglot import exp
from sqlglot.dialects.dialect import Dialect

from .base_agent import BaseAgent
from .agent_utils import AgentUtils
from models.models import AgentState, AgentResult, AgentType

logger = logging.getLogger(__name__)


def check_sql_is_read_only(sql: str, dialect: Optional[str] = None) -> Tuple[bool, str]:
    """Deterministically check that `sql` is a single, read-only SELECT statement.

    Returns (is_safe, reason). `reason` is a human-readable explanation in both
    the safe and unsafe case.
    """
    if not sql or not sql.strip():
        return False, "No SQL provided"

    parse_dialect = dialect if dialect in Dialect.classes else None

    try:
        statements = sqlglot.parse(sql, read=parse_dialect)
    except Exception as e:
        return False, f"SQL failed to parse: {e}"

    statements = [s for s in statements if s is not None]

    if len(statements) == 0:
        return False, "No valid SQL statement found"

    if len(statements) > 1:
        return False, (
            f"Multiple SQL statements detected ({len(statements)}); "
            "only a single read-only SELECT is allowed"
        )

    statement = statements[0]

    if not isinstance(statement, exp.Query):
        return False, (
            f"Statement type '{type(statement).__name__}' is not a read-only "
            "SELECT (writes/DDL are not permitted)"
        )

    return True, "Query is a single, read-only SELECT statement"


class SQLSafetyGuardAgent(BaseAgent):
    """Deterministic guardrail rejecting any non-read-only generated SQL."""

    def __init__(self, model_wrapper):
        super().__init__(AgentType.SQL_SAFETY_GUARD, model_wrapper)

    def process(self, state: AgentState) -> AgentResult:
        """Check the generated query is read-only. No LLM call is made."""
        logger.info("Running deterministic SQL safety check")

        if not state.generated_query or not state.generated_query.query:
            return AgentUtils.create_error_result("No query generated; cannot run safety check")

        is_safe, reason = check_sql_is_read_only(state.generated_query.query, dialect=state.dialect)

        if is_safe:
            logger.info("SQL safety check passed")
        else:
            logger.error(f"SQL safety check failed: {reason}")

        return AgentResult(
            success=True,
            message=reason,
            state_updates={
                "is_sql_safe": is_safe,
                "sql_safety_violation": None if is_safe else reason,
                "current_step": "sql_safety_check_passed" if is_safe else "sql_safety_check_failed",
            }
        )
