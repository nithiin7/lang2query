"""
Beautiful colored logging utilities for the text2query system.

Provides colorized logging with emojis and structured formatting.
"""

import logging
import sys


class Colors:
    """ANSI color codes for terminal output."""

    # Basic colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors and emojis to log messages."""

    # Level-specific formatting
    LEVEL_COLORS = {
        logging.DEBUG: Colors.BRIGHT_BLACK,
        logging.INFO: Colors.BRIGHT_CYAN,
        logging.WARNING: Colors.BRIGHT_YELLOW,
        logging.ERROR: Colors.BRIGHT_RED,
        logging.CRITICAL: Colors.BOLD + Colors.BRIGHT_RED + Colors.BG_RED,
    }

    LEVEL_EMOJIS = {
        logging.DEBUG: "🔍",
        logging.INFO: "ℹ️ ",
        logging.WARNING: "⚠️ ",
        logging.ERROR: "❌",
        logging.CRITICAL: "🚨",
    }

    def __init__(self, fmt=None, datefmt=None, style="%"):
        super().__init__(fmt, datefmt, style)

    def format(self, record):
        # Get color and emoji for level
        level_color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
        level_emoji = self.LEVEL_EMOJIS.get(record.levelno, "📝")

        # Color the level name
        colored_level = f"{level_color}{record.levelname:<8}{Colors.RESET}"

        # Color the logger name
        logger_color = Colors.BRIGHT_BLUE if "workflow" in record.name else Colors.CYAN
        colored_logger = f"{logger_color}{record.name}{Colors.RESET}"

        # Format timestamp
        timestamp = self.formatTime(record, self.datefmt)
        timestamp_colored = f"{Colors.DIM}{timestamp}{Colors.RESET}"

        # Format the message with appropriate colors
        message = self._colorize_message(record.getMessage(), record.levelno)

        # Combine everything
        formatted = f"{timestamp_colored} {level_emoji} {colored_level} {colored_logger} - {message}"

        return formatted

    def _colorize_message(self, message: str, level: int) -> str:
        """Add colors to specific parts of the message based on content."""

        # Agent-specific coloring
        if "Query Breakdown" in message:
            message = message.replace(
                "Query Breakdown",
                f"{Colors.BRIGHT_MAGENTA}Query Breakdown{Colors.RESET}",
            )
        elif "Database Selector" in message or "Db Selector" in message:
            message = message.replace(
                "Database Selector",
                f"{Colors.BRIGHT_BLUE}Database Selector{Colors.RESET}",
            )
            message = message.replace(
                "Db Selector", f"{Colors.BRIGHT_BLUE}Db Selector{Colors.RESET}"
            )
        elif "Table Selector" in message:
            message = message.replace(
                "Table Selector", f"{Colors.BRIGHT_GREEN}Table Selector{Colors.RESET}"
            )
        elif "Column Selector" in message:
            message = message.replace(
                "Column Selector",
                f"{Colors.BRIGHT_YELLOW}Column Selector{Colors.RESET}",
            )
        elif "Query Combiner" in message:
            message = message.replace(
                "Query Combiner", f"{Colors.BRIGHT_CYAN}Query Combiner{Colors.RESET}"
            )
        elif "Query Generator" in message:
            message = message.replace(
                "Query Generator",
                f"{Colors.BRIGHT_MAGENTA}Query Generator{Colors.RESET}",
            )
        elif "Query Validator" in message:
            message = message.replace(
                "Query Validator", f"{Colors.BRIGHT_RED}Query Validator{Colors.RESET}"
            )

        # Step coloring
        if "Step" in message and ":" in message:
            import re

            step_match = re.search(r"(Step \d+)", message)
            if step_match:
                step = step_match.group(1)
                message = message.replace(
                    step, f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{step}{Colors.RESET}"
                )

        # Status coloring
        if "✅" in message:
            # Success messages
            message = message.replace("✅", f"{Colors.BRIGHT_GREEN}✅{Colors.RESET}")
        elif "❌" in message:
            # Error messages
            message = message.replace("❌", f"{Colors.BRIGHT_RED}❌{Colors.RESET}")
        elif "⚠️" in message:
            # Warning messages
            message = message.replace("⚠️", f"{Colors.BRIGHT_YELLOW}⚠️{Colors.RESET}")
        elif "🔄" in message:
            # Processing messages
            message = message.replace("🔄", f"{Colors.BRIGHT_BLUE}🔄{Colors.RESET}")

        # Highlight important values
        if "confidence" in message.lower():
            import re

            confidence_match = re.search(r"(\d+\.\d+)", message)
            if confidence_match:
                confidence = confidence_match.group(1)
                color = (
                    Colors.BRIGHT_GREEN
                    if float(confidence) > 0.7
                    else (
                        Colors.BRIGHT_YELLOW
                        if float(confidence) > 0.4
                        else Colors.BRIGHT_RED
                    )
                )
                message = message.replace(
                    confidence, f"{color}{confidence}{Colors.RESET}"
                )

        # Highlight query-related content (SQL, GraphQL, REST, etc.)
        if "SELECT" in message or "FROM" in message or "WHERE" in message:
            message = message.replace(
                "SELECT", f"{Colors.BOLD}{Colors.BRIGHT_BLUE}SELECT{Colors.RESET}"
            )
            message = message.replace(
                "FROM", f"{Colors.BOLD}{Colors.BRIGHT_GREEN}FROM{Colors.RESET}"
            )
            message = message.replace(
                "WHERE", f"{Colors.BOLD}{Colors.BRIGHT_YELLOW}WHERE{Colors.RESET}"
            )
            message = message.replace(
                "JOIN", f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}JOIN{Colors.RESET}"
            )

        # Highlight GraphQL content
        if "query" in message.lower() and "{" in message:
            message = message.replace(
                "query", f"{Colors.BOLD}{Colors.BRIGHT_CYAN}query{Colors.RESET}"
            )
            message = message.replace(
                "mutation", f"{Colors.BOLD}{Colors.BRIGHT_CYAN}mutation{Colors.RESET}"
            )

        # Highlight REST API content
        if any(
            method in message.upper()
            for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]
        ):
            for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                message = message.replace(
                    method, f"{Colors.BOLD}{Colors.BRIGHT_GREEN}{method}{Colors.RESET}"
                )

        return message


def setup_colored_logging(level=logging.INFO):
    """Set up beautiful colored logging for the entire application."""

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler with colored formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Set up colored formatter
    formatter = ColoredFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(formatter)

    # Add handler to root logger
    root_logger.addHandler(console_handler)

    return root_logger


def log_section_header(logger, title: str, width: int = 80, char: str = "="):
    """Log a beautiful section header."""
    border = char * width
    logger.info(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{border}{Colors.RESET}")
    logger.info(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{title.center(width)}{Colors.RESET}")
    logger.info(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{border}{Colors.RESET}")


def log_workflow_step(logger, step_num: int, step_name: str, emoji: str = "🔄"):
    """Log a workflow step with beautiful formatting."""
    step_text = f"{emoji} Step {step_num}: {step_name}"
    logger.info(f"{Colors.BOLD}{Colors.BRIGHT_BLUE}{step_text}{Colors.RESET}")


def log_success(logger, message: str):
    """Log a success message with green coloring."""
    logger.info(f"{Colors.BRIGHT_GREEN}✅ {message}{Colors.RESET}")


def log_error(logger, message: str):
    """Log an error message with red coloring."""
    logger.error(f"{Colors.BRIGHT_RED}❌ {message}{Colors.RESET}")


def log_warning(logger, message: str):
    """Log a warning message with yellow coloring."""
    logger.warning(f"{Colors.BRIGHT_YELLOW}⚠️ {message}{Colors.RESET}")


def log_processing(logger, message: str):
    """Log a processing message with blue coloring."""
    logger.info(f"{Colors.BRIGHT_BLUE}🔄 {message}{Colors.RESET}")


def log_ai_response(logger, agent_name: str, response: str):
    """Log a full AI response with beautiful formatting and proper line handling."""
    logger.info(f"{Colors.BRIGHT_MAGENTA}🤖 {agent_name} AI Response:{Colors.RESET}")
    logger.info(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

    # Split response into lines and log each line individually
    lines = response.split("\n")
    for line in lines:
        if line.strip():  # Only log non-empty lines
            logger.info(f"{Colors.BRIGHT_WHITE}{line}{Colors.RESET}")
        else:
            logger.info("")  # Log empty lines to preserve formatting

    logger.info(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")


def log_query(logger, query: str, confidence: float = None):
    """Log a query with syntax highlighting."""
    logger.info(
        f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}🔍 Generated Query:{Colors.RESET}"
    )

    # Detect query type and apply appropriate highlighting
    query_type = _detect_query_type(query)
    highlighted_query = _highlight_query(query, query_type)

    # Indent and log each line
    for line in highlighted_query.split("\n"):
        if line.strip():
            logger.info(f"   {line}")

    if confidence is not None:
        color = (
            Colors.BRIGHT_GREEN
            if confidence > 0.7
            else Colors.BRIGHT_YELLOW
            if confidence > 0.4
            else Colors.BRIGHT_RED
        )
        logger.info(
            f"   {Colors.BOLD}Confidence: {color}{confidence:.2f}{Colors.RESET}"
        )


def _detect_query_type(query: str) -> str:
    """Detect the type of query for appropriate highlighting."""
    query_upper = query.upper().strip()

    if any(
        keyword in query_upper
        for keyword in ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP"]
    ):
        return "sql"
    elif (
        query.strip().startswith("{")
        or "query" in query_upper
        or "mutation" in query_upper
    ):
        return "graphql"
    elif any(
        method in query_upper for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]
    ) or query.startswith("http"):
        return "rest"
    else:
        return "generic"


def _highlight_query(query: str, query_type: str) -> str:
    """Apply syntax highlighting based on query type."""
    highlighted_query = query

    if query_type == "sql":
        sql_keywords = [
            "SELECT",
            "FROM",
            "WHERE",
            "JOIN",
            "LEFT JOIN",
            "RIGHT JOIN",
            "INNER JOIN",
            "GROUP BY",
            "ORDER BY",
            "HAVING",
            "LIMIT",
            "AND",
            "OR",
            "IN",
            "NOT",
            "NULL",
        ]
        for keyword in sql_keywords:
            highlighted_query = highlighted_query.replace(
                keyword, f"{Colors.BOLD}{Colors.BRIGHT_BLUE}{keyword}{Colors.RESET}"
            )
    elif query_type == "graphql":
        graphql_keywords = ["query", "mutation", "subscription", "fragment"]
        for keyword in graphql_keywords:
            highlighted_query = highlighted_query.replace(
                keyword, f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{keyword}{Colors.RESET}"
            )
    elif query_type == "rest":
        rest_keywords = ["GET", "POST", "PUT", "PATCH", "DELETE", "HTTP"]
        for keyword in rest_keywords:
            highlighted_query = highlighted_query.replace(
                keyword, f"{Colors.BOLD}{Colors.BRIGHT_GREEN}{keyword}{Colors.RESET}"
            )

    return highlighted_query
