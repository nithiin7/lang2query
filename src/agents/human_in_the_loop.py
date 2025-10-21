"""
Human-in-the-loop agent for confirmation workflows.

This agent presents identified items (databases, tables, columns, etc.) to the user
and gets their feedback before proceeding with the query generation pipeline.
"""

import logging
from typing import Dict, Any, Callable, Union, List, Optional
from .base_agent import BaseAgent
from models.models import AgentState, AgentResult, HumanFeedback, AgentType
from tools.retriever_tool import validate_database_exists, validate_table_exists, search_similar_tables, get_all_databases

logger = logging.getLogger(__name__)


class HumanInTheLoopAgent(BaseAgent):
    """Generic agent for human-in-the-loop confirmation workflows."""

    def __init__(self, model_wrapper, confirmation_type: str = "databases",
                 data_source: Union[str, Callable] = None,
                 display_formatter: Callable = None,
                 retriever=None):
        """
        Initialize the human-in-the-loop agent.

        Args:
            model_wrapper: Model wrapper for LLM operations
            confirmation_type: Type of confirmation ("databases", "tables", "columns", etc.)
            data_source: How to get data from state (attribute name or callable)
            display_formatter: Function to format data for display
            retriever: Retriever instance for validating suggested items
        """
        super().__init__(AgentType.HUMAN_IN_THE_LOOP, model_wrapper)
        self.confirmation_type = confirmation_type
        self.data_source = data_source or f"relevant_{confirmation_type}"
        self.display_formatter = display_formatter or self._default_display_formatter
        self._retriever = retriever
        self.name = f"Human-in-the-Loop Agent ({confirmation_type.title()})"


    def process(self, state: AgentState) -> AgentResult:
        """
        Present identified items to user and get their approval/feedback.

        Args:
            state: Current agent state with identified items

        Returns:
            AgentResult with user feedback processing results
        """
        try:
            # Get the data to confirm
            items_data = self._get_items_data(state)

            if not items_data:
                logger.warning(f"No {self.confirmation_type} identified for human review")
                return AgentResult(
                    success=True,
                    message=f"No {self.confirmation_type} to review, proceeding",
                    state_updates={
                        "human_approvals": {self.confirmation_type: True},
                        "human_feedback": "no_items"
                    }
                )

            # If feedback is already present (resume), process it; else return awaiting checkpoint
            pre_supplied = getattr(state, 'human_feedback', None)
            approvals = getattr(state, 'human_approvals', {}) or {}

            if pre_supplied:
                # Process existing feedback using LLM
                feedback_result = self._process_feedback_with_llm(state, pre_supplied, items_data)
                return AgentResult(success=True, message="Human feedback applied (resume)", state_updates=feedback_result)

            # Otherwise, signal awaiting approval and stop
            return AgentResult(
                success=True,
                message=f"Awaiting human approval for {self.confirmation_type}",
                state_updates={
                    "pending_review": {
                        "type": self.confirmation_type,
                        "items": items_data if isinstance(items_data, list) else list(items_data) if items_data else [],
                    },
                    "human_approvals": {**approvals, self.confirmation_type: False},
                    "human_feedback": None,
                },
            )

        except Exception as e:
            logger.error(f"Human-in-the-loop processing failed: {e}")
            return AgentResult(
                success=False,
                message=f"Failed to process human feedback: {str(e)}",
                state_updates=None
            )

    def _get_items_data(self, state: AgentState) -> Any:
        """Get the items data from the state using the configured data source."""
        if callable(self.data_source):
            return self.data_source(state)
        else:
            return getattr(state, self.data_source, [])


    def _validate_feedback_suggestions(self, feedback: HumanFeedback, state: AgentState) -> HumanFeedback:
        """
        Validate suggested items using retriever directly.

        Args:
            feedback: HumanFeedback object with suggested values from user
            state: Current agent state for context

        Returns:
            HumanFeedback object with validation results populated
        """
        if not feedback.suggested_values:
            feedback.valid_suggestions = []
            feedback.invalid_suggestions = []
            return feedback

        valid_suggestions = []
        invalid_suggestions = []

        # Validate each suggested item using retriever
        for item in feedback.suggested_values:
            is_valid = self._validate_item_with_retriever(item, state)
            if is_valid:
                valid_suggestions.append(item)
                logger.info(f"✅ Validated {self.confirmation_type} suggestion: {item}")
            else:
                invalid_suggestions.append(item)
                logger.warning(f"⚠️ Invalid {self.confirmation_type} suggestion: {item}")

        feedback.valid_suggestions = valid_suggestions
        feedback.invalid_suggestions = invalid_suggestions

        return feedback


    def _validate_item_with_retriever(self, item: str, state: AgentState) -> bool:
        """
        Validate a single item using retriever.

        Args:
            item: Item to validate (database name or table name)
            state: Current agent state for context

        Returns:
            True if item exists in knowledge base, False otherwise
        """
        if not self._retriever:
            logger.warning("⚠️ No retriever available, accepting suggestion without validation")
            return True

        try:
            if self.confirmation_type == "databases":
                # Validate database exists
                all_dbs = self._retriever.get_all_databases()
                return item in all_dbs
            
            elif self.confirmation_type == "tables":
                # For tables, need to handle both "db.table" and just "table" formats
                if '.' in item:
                    # Already has database name
                    db_name, table_name = item.rsplit('.', 1)
                    return self._check_table_exists(table_name, db_name)
                else:
                    # No database name provided, search in relevant databases
                    relevant_dbs = getattr(state, 'relevant_databases', [])
                    if not relevant_dbs:
                        logger.warning(f"⚠️ No relevant databases to search for table: {item}")
                        return False
                    
                    # Check if table exists in any of the relevant databases
                    for db in relevant_dbs:
                        if self._check_table_exists(item, db):
                            logger.info(f"✅ Found table {item} in database {db}")
                            return True
                    
                    return False
            
            return False
        
        except Exception as e:
            logger.error(f"❌ Error validating item {item}: {e}")
            return False

    def _check_table_exists(self, table_name: str, database_name: str) -> bool:
        """
        Check if a table exists in a database using retriever.

        Args:
            table_name: Table name to check
            database_name: Database name to check in

        Returns:
            True if table exists, False otherwise
        """
        try:
            tables = self._retriever.get_tables_in_database(database_name)
            # Check if any table matches the name
            for table_info in tables:
                if isinstance(table_info, dict):
                    # parse_table_chunk returns 'table' as key, not 'table_name'
                    if table_info.get('table') == table_name:
                        return True
                elif hasattr(table_info, 'table'):
                    if table_info.table == table_name:
                        return True
            return False
        except Exception as e:
            logger.error(f"❌ Error checking table {table_name} in {database_name}: {e}")
            return False

    def _default_display_formatter(self, items_data: Any, confirmation_type: str) -> str:
        """Default display formatter for list-type data."""
        if isinstance(items_data, list):
            if not items_data:
                return f"No {confirmation_type} identified"
            return "\n".join(f"  • {item}" for item in items_data)
        elif isinstance(items_data, dict):
            if not items_data:
                return f"No {confirmation_type} identified"
            lines = []
            for key, values in items_data.items():
                lines.append(f"  📊 {key}:")
                if isinstance(values, list):
                    for value in values:
                        lines.append(f"    • {value}")
                else:
                    lines.append(f"    • {values}")
            return "\n".join(lines)
        else:
            return str(items_data)


    def _process_feedback_with_llm(self, state: AgentState, user_feedback: str, items_data: Any) -> Dict[str, Any]:
        """
        Process user feedback using LLM with validation tools to generate structured response.

        Args:
            state: Current agent state
            user_feedback: Raw user feedback string
            items_data: The current items being reviewed

        Returns:
            Dictionary of state updates
        """
        system_message = self._create_feedback_analysis_system_prompt(items_data)
        human_message = f"User feedback: {user_feedback}"

        # Create validation tools for the LLM to use
        validation_tools = [validate_database_exists, validate_table_exists, search_similar_tables, get_all_databases]

        # Generate structured feedback analysis with tools
        feedback_analysis = self.generate_with_llm(
            schema_class=HumanFeedback,
            system_message=system_message,
            human_message=human_message,
            tools=validation_tools,
            temperature=0.1
        )

        # Validate suggestions using retriever directly
        feedback_analysis = self._validate_feedback_suggestions(feedback_analysis, state)

        # Process the structured response into state updates
        return self._convert_feedback_to_state_updates(state, feedback_analysis)

    def _create_feedback_analysis_system_prompt(self, items_data: Any) -> str:
        """Create system prompt for feedback analysis."""
        # Format current items for the prompt
        items_display = self.display_formatter(items_data, self.confirmation_type)

        return f"""You are an expert feedback analyzer for database and table selections with access to validation tools. Your task is to analyze user feedback and use validation tools to ensure all suggestions are valid before making decisions.

**CURRENT SELECTION:**
{items_display}

**AVAILABLE TOOLS:**
You have access to validation tools to check if databases and tables exist:
- **validate_database_exists(database_name)**: Check if a database exists
- **validate_table_exists(table_name, database_name)**: Check if a table exists in a database
- **search_similar_tables(query, database_names, limit)**: Find relevant tables for a query
- **get_all_databases()**: List all available databases

**YOUR TASK:**
1. **Analyze user feedback** and extract any suggested databases/tables
2. **Use validation tools** to verify all suggestions exist before including them
3. **Determine final decisions** based on validation results:
   - selected_values: Items from current selection to keep (must exist in current selection)
   - suggested_values: NEW items to add (must be validated as existing first)
   - approval_status: APPROVE, MODIFY, or REJECT based on validation results
   - modification_type: How to modify the selection
   - feedback_summary: Clear summary of changes made

**VALIDATION REQUIREMENTS:**
- **ALWAYS validate suggested items** before including them in suggested_values
- **Only include validated items** that return "VALID" from tools
- **If validation fails**, either exclude the item or use search_similar_tables to find alternatives
- **Be transparent** about validation results in feedback_summary

**GUIDELINES:**
- **selected_values**: Items from current selection to keep. Empty means replace all.
- **suggested_values**: ONLY validated items that exist in knowledge base
- **approval_status**: APPROVE (valid suggestions), MODIFY (some changes needed), REJECT (validation failed)
- **modification_type**: 'approve', 'replace', 'add', 'remove', 'modify'
- **Call tools proactively** to validate before making decisions

**RESPONSE FORMAT:**
Return ONLY the JSON structure matching the required schema. Do not include explanations outside the structured fields.

**EXAMPLES:**

For "use wallet.user table as well":
1. Call: validate_table_exists("wallet.user")
2. If VALID: include "wallet.user" in suggested_values

**CRITICAL:**
- **Always call validation tools** before including items in suggested_values
- **Only validated items** should appear in suggested_values
- **Clear feedback** about validation results in feedback_summary
- **Use search_similar_tables** if user suggests invalid items to find alternatives"""

    def _convert_feedback_to_state_updates(self, state: AgentState, feedback: HumanFeedback) -> Dict[str, Any]:
        """
        Convert structured feedback analysis into state updates.

        Args:
            state: Current agent state
            feedback: Structured feedback from LLM

        Returns:
            Dictionary of state updates
        """
        updates = {}

        # Set human feedback and approvals
        updates['human_feedback'] = feedback.feedback_summary

        # Determine approval status based on feedback
        approvals = dict(getattr(state, 'human_approvals', {}) or {})

        if feedback.approval_status == 'APPROVE':
            approvals[self.confirmation_type] = True
            updates['feedback_processed'] = False  # No modifications made
            updates['last_modification_type'] = 'approve'
            updates['human_feedback'] = None  # Clear feedback after approval
            logger.info(f"✅ User approved {self.confirmation_type} selection")
        else:
            approvals[self.confirmation_type] = False
            if feedback.approval_status == 'REJECT':
                updates['feedback_processed'] = False  # Will re-identify
                updates['last_modification_type'] = 'reject'
                updates['human_feedback'] = None  # Clear feedback to prevent re-processing
                logger.info(f"🔄 User rejected {self.confirmation_type} selection - needs complete restart")
            else:  # MODIFY
                # Will determine if modifications were actually made below
                # Don't set feedback_processed yet - will be set based on actual changes
                updates['last_modification_type'] = feedback.modification_type
                logger.info(f"🔄 User requested {self.confirmation_type} modifications (type: {feedback.modification_type})")

        updates['human_approvals'] = approvals

        # Handle item modifications based on feedback
        changes_made = False  # Track if actual changes were made
        
        if self.confirmation_type in ['databases', 'tables']:
            current_items = list(getattr(state, f'relevant_{self.confirmation_type}', []) or [])
            original_items = current_items.copy()

            if feedback.modification_type == 'replace':
                # Replace current items with selected_values
                if feedback.selected_values:
                    updates[f'relevant_{self.confirmation_type}'] = feedback.selected_values
                    changes_made = (feedback.selected_values != original_items)
                    logger.info(f"🔄 Replaced {self.confirmation_type} with: {feedback.selected_values}")
                else:
                    # Clear items if no selection provided
                    updates[f'relevant_{self.confirmation_type}'] = []
                    changes_made = len(original_items) > 0
                    logger.info(f"🔄 Cleared {self.confirmation_type} selection")

            elif feedback.modification_type == 'add':
                # Normalize items (add database name to tables if missing)
                items_to_add = self._normalize_items(feedback.valid_suggestions, state)
                
                if items_to_add:
                    added_count = 0
                    for item in items_to_add:
                        if item not in current_items:
                            current_items.append(item)
                            added_count += 1
                    
                    if added_count > 0:
                        updates[f'relevant_{self.confirmation_type}'] = current_items
                        changes_made = True
                        logger.info(f"➕ Added {added_count} to {self.confirmation_type}: {items_to_add}")
                    else:
                        logger.info(f"ℹ️  No new items to add (all already present)")

                # Log invalid suggestions that couldn't be added
                if feedback.invalid_suggestions:
                    logger.warning(f"⚠️ Could not add invalid {self.confirmation_type}: {feedback.invalid_suggestions}")
                    # Add invalid suggestions to feedback summary for user notification
                    current_feedback = updates.get('human_feedback', feedback.feedback_summary)
                    invalid_list = ", ".join(f'"{item}"' for item in feedback.invalid_suggestions)
                    updates['human_feedback'] = f"{current_feedback} (Note: {invalid_list} not found in knowledge base)"

            elif feedback.modification_type == 'remove':
                # Remove items from current selection (handle both with and without db prefix for tables)
                items_to_remove = set(feedback.suggested_values) if feedback.suggested_values else set()
                
                # For tables, normalize removal items to match format in current_items
                if self.confirmation_type == 'tables':
                    normalized_removals = set()
                    for item in items_to_remove:
                        # Check both with and without database prefix
                        normalized_removals.add(item)
                        if '.' not in item:
                            # Add all possible fully-qualified versions
                            for current_item in current_items:
                                if current_item.endswith('.' + item):
                                    normalized_removals.add(current_item)
                    items_to_remove = normalized_removals
                
                # Keep items that are not in the removal set
                filtered_items = [item for item in current_items if item not in items_to_remove]
                changes_made = (len(filtered_items) != len(original_items))
                updates[f'relevant_{self.confirmation_type}'] = filtered_items
                
                if changes_made:
                    logger.info(f"➖ Removed from {self.confirmation_type}: {items_to_remove}")
                    logger.info(f"📋 Remaining {self.confirmation_type}: {filtered_items}")
                else:
                    logger.info(f"ℹ️  No items removed (none matched)")

        # Only set feedback_processed and clear feedback if actual changes were made
        if feedback.approval_status == 'MODIFY':
            if changes_made:
                updates['feedback_processed'] = True
                updates['human_feedback'] = None  # Clear feedback after successful modifications
                logger.info(f"✅ Modifications applied, will show updated list to user")
            else:
                # No actual changes made - treat as approval to move forward
                updates['feedback_processed'] = False
                updates['human_feedback'] = None  # Clear feedback to prevent loop
                approvals[self.confirmation_type] = True  # Auto-approve since no valid changes
                updates['human_approvals'] = approvals
                logger.info(f"ℹ️  No valid modifications made, auto-approving current selection")

        return updates

    def _normalize_items(self, items: List[str], state: AgentState) -> List[str]:
        """
        Normalize items to include database names for tables.

        Args:
            items: List of items to normalize
            state: Current agent state for context

        Returns:
            List of normalized items
        """
        if not items:
            return []

        if self.confirmation_type == 'databases':
            # Databases don't need normalization
            return items

        if self.confirmation_type == 'tables':
            # Add database names to tables if missing
            normalized = []
            relevant_dbs = getattr(state, 'relevant_databases', [])
            
            for item in items:
                if '.' in item:
                    # Already has database name
                    normalized.append(item)
                else:
                    # Need to find database name
                    found_db = self._find_database_for_table(item, relevant_dbs)
                    if found_db:
                        normalized.append(f"{found_db}.{item}")
                        logger.info(f"📍 Normalized table {item} -> {found_db}.{item}")
                    else:
                        # Couldn't find database, keep as-is and log warning
                        logger.warning(f"⚠️ Could not find database for table: {item}")
                        normalized.append(item)
            
            return normalized

        return items

    def _find_database_for_table(self, table_name: str, relevant_dbs: List[str]) -> Optional[str]:
        """
        Find which database contains a table.

        Args:
            table_name: Table name to search for
            relevant_dbs: List of databases to search in

        Returns:
            Database name if found, None otherwise
        """
        if not self._retriever or not relevant_dbs:
            return None

        try:
            for db in relevant_dbs:
                if self._check_table_exists(table_name, db):
                    return db
            return None
        except Exception as e:
            logger.error(f"❌ Error finding database for table {table_name}: {e}")
            return None
