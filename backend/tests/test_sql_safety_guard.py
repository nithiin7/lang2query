"""Tests for the deterministic SQL safety guard (src/agents/sql_safety_guard.py).

These test the AST-based read-only check directly, without touching the LLM
or the rest of the workflow, since the check is deliberately independent of
both.
"""

import pytest

from modules.query.agents.sql_safety_guard import check_sql_is_read_only, SQLSafetyGuardAgent
from models.models import AgentState, Query


def test_valid_select_is_safe():
    is_safe, reason = check_sql_is_read_only("SELECT id, name FROM users WHERE active = 1")
    assert is_safe is True
    assert "SELECT" in reason.upper() or "read-only" in reason


def test_drop_table_is_rejected():
    is_safe, reason = check_sql_is_read_only("DROP TABLE users")
    assert is_safe is False
    assert "Drop" in reason


def test_semicolon_stacked_select_then_drop_is_rejected():
    is_safe, reason = check_sql_is_read_only("SELECT * FROM users; DROP TABLE users")
    assert is_safe is False
    assert "multiple" in reason.lower() or "statement" in reason.lower()


def test_select_with_comment_hiding_a_second_statement_is_still_treated_as_one_safe_select():
    """A real parser treats `-- ; DROP TABLE users` as an inert comment, not a
    second statement. This is the exact case a regex/keyword blacklist gets
    wrong: it would either (a) false-positive reject this safe query because
    the word DROP appears in the text, or worse (b) be the kind of naive
    text-scanning check that's trivially bypassed in the opposite direction.
    Parsing to an AST and checking the single resulting statement's real type
    sidesteps both failure modes.
    """
    is_safe, reason = check_sql_is_read_only(
        "SELECT * FROM users -- ; DROP TABLE users"
    )
    assert is_safe is True


@pytest.mark.parametrize("sql", [
    "DELETE FROM users",
    "UPDATE users SET name = 'x'",
    "INSERT INTO users (name) VALUES ('x')",
    "ALTER TABLE users ADD COLUMN age INT",
    "TRUNCATE TABLE users",
])
def test_write_and_ddl_statements_are_rejected(sql):
    is_safe, _ = check_sql_is_read_only(sql)
    assert is_safe is False


def test_string_literal_containing_a_write_keyword_is_not_flagged():
    """A keyword blacklist would false-positive on this; the AST-based check
    correctly sees a single SELECT with a string literal as its argument."""
    is_safe, _ = check_sql_is_read_only(
        "SELECT * FROM audit_log WHERE action = 'DELETE'"
    )
    assert is_safe is True


def test_union_of_selects_is_safe():
    is_safe, _ = check_sql_is_read_only("SELECT id FROM users UNION SELECT id FROM archived_users")
    assert is_safe is True


def test_cte_wrapped_select_is_safe():
    is_safe, _ = check_sql_is_read_only(
        "WITH active AS (SELECT * FROM users WHERE active = 1) SELECT * FROM active"
    )
    assert is_safe is True


def test_empty_query_is_rejected():
    is_safe, reason = check_sql_is_read_only("")
    assert is_safe is False
    assert "No SQL" in reason


def test_unparseable_sql_is_rejected():
    is_safe, reason = check_sql_is_read_only("SELECT * FROM users WHERE (")
    assert is_safe is False
    assert "parse" in reason.lower()


def test_unknown_dialect_falls_back_instead_of_crashing():
    # state.dialect can be a loose string like "sql" (see RoutingInfo) which
    # is not a real sqlglot dialect name; this must not raise.
    is_safe, _ = check_sql_is_read_only("SELECT * FROM users", dialect="sql")
    assert is_safe is True


class _StubModelWrapper:
    """Minimal stand-in; the safety guard never calls the model."""

    def generate(self, *args, **kwargs):
        raise AssertionError("SQLSafetyGuardAgent must not call the LLM")


def _state_with_query(sql: str) -> AgentState:
    return AgentState(
        natural_language_query="irrelevant",
        generated_query=Query(query=sql, database="db", tables_used=[], columns_used=[]),
    )


def test_agent_marks_safe_query_and_does_not_touch_the_llm():
    agent = SQLSafetyGuardAgent(_StubModelWrapper())
    result = agent.process(_state_with_query("SELECT * FROM users"))

    assert result.success is True
    assert result.state_updates["is_sql_safe"] is True
    assert result.state_updates["sql_safety_violation"] is None
    assert result.state_updates["current_step"] == "sql_safety_check_passed"


def test_agent_marks_unsafe_query_as_hard_failure_not_llm_retry():
    agent = SQLSafetyGuardAgent(_StubModelWrapper())
    result = agent.process(_state_with_query("DROP TABLE users"))

    assert result.success is True  # the *check* ran successfully...
    assert result.state_updates["is_sql_safe"] is False  # ...and it says: unsafe
    assert result.state_updates["sql_safety_violation"]
    assert result.state_updates["current_step"] == "sql_safety_check_failed"


def test_agent_errors_cleanly_when_no_query_was_generated():
    agent = SQLSafetyGuardAgent(_StubModelWrapper())
    result = agent.process(AgentState(natural_language_query="irrelevant"))

    assert result.success is False
