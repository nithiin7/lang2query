"""
Configuration file for the Lang2Query system.
This file contains settings that can be easily modified to support different query languages and databases.
"""

import os

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DATABASE_CONFIG = {
    "mysql": {
        "connection_string": os.getenv(
            "MYSQL_CONNECTION_STRING", "mysql+mysqlconnector://root:password@localhost/database"
        ),
        "dialect": "mysql",
        "driver": "mysqlconnector",
    },
    "postgresql": {
        "connection_string": os.getenv(
            "POSTGRESQL_CONNECTION_STRING", "postgresql://user:password@localhost/dbname"
        ),
        "dialect": "postgresql",
        "driver": "psycopg2",
    },
    "sqlite": {
        "connection_string": os.getenv("SQLITE_CONNECTION_STRING", "sqlite:///./database.db"),
        "dialect": "sqlite",
        "driver": "sqlite3",
    },
}

# Query Language Configuration
QUERY_LANGUAGE_CONFIG = {
    "sql": {
        "name": "SQL",
        "extensions": [".sql"],
        "keywords": ["SELECT", "FROM", "WHERE", "JOIN", "GROUP BY", "ORDER BY"],
        "dialects": ["mysql", "postgresql", "sqlite", "oracle", "sqlserver"],
    },
    "mongodb": {
        "name": "MongoDB Query Language",
        "extensions": [".js", ".json"],
        "keywords": ["find", "aggregate", "match", "group", "sort"],
        "dialects": ["mongodb"],
    },
    "elasticsearch": {
        "name": "Elasticsearch Query DSL",
        "extensions": [".json"],
        "keywords": ["query", "filter", "aggs", "sort"],
        "dialects": ["elasticsearch"],
    },
    "cypher": {
        "name": "Cypher (Neo4j)",
        "extensions": [".cypher"],
        "keywords": ["MATCH", "RETURN", "WHERE", "WITH", "UNWIND"],
        "dialects": ["neo4j"],
    },
}

# Domain Configuration for Different Datasets
DOMAIN_CONFIGS = {
    "ecommerce": {
        "customer": ["customer", "sellers"],
        "orders": ["order_items", "order_payments", "order_reviews", "orders"],
        "product": ["products", "category_translation"],
    },
    "healthcare": {
        "patient": ["patients", "doctors"],
        "medical": ["appointments", "diagnoses", "treatments", "medications"],
        "billing": ["invoices", "payments", "insurance"],
    },
    "finance": {
        "customer": ["customers", "accounts"],
        "transactions": ["transactions", "payments", "loans"],
        "products": ["investment_products", "insurance_products"],
    },
}

# Model Configuration
MODEL_CONFIG = {
    "routing": {
        "provider": os.getenv("ROUTING_MODEL_PROVIDER", "anthropic"),
        "model": os.getenv("ROUTING_MODEL_NAME", "claude-3-5-sonnet-20240620"),
        "temperature": float(os.getenv("ROUTING_MODEL_TEMPERATURE", "0.4")),
    },
    "query_generation": {
        "provider": os.getenv("QUERY_GEN_MODEL_PROVIDER", "anthropic"),
        "model": os.getenv("QUERY_GEN_MODEL_NAME", "claude-3-5-sonnet-20240620"),
        "temperature": float(os.getenv("QUERY_GEN_MODEL_TEMPERATURE", "0.1")),
    },
    "validation": {
        "provider": os.getenv("VALIDATION_MODEL_PROVIDER", "anthropic"),
        "model": os.getenv("VALIDATION_MODEL_NAME", "claude-3-5-sonnet-20240620"),
        "temperature": float(os.getenv("VALIDATION_MODEL_TEMPERATURE", "0.0")),
    },
}

# API Keys and Authentication
API_KEYS = {
    "anthropic": os.getenv("ANTHROPIC_API_KEY"),
    "groq": os.getenv("GROQ_API_KEY"),
    "openai": os.getenv("OPENAI_API_KEY"),
    "cohere": os.getenv("COHERE_API_KEY"),
}

# Fuzzy Matching Configuration
FUZZY_MATCHING_CONFIG = {
    "scorer": os.getenv("FUZZY_SCORER", "token_set_ratio"),
    "min_confidence": int(os.getenv("FUZZY_MIN_CONFIDENCE", "70")),
    "max_candidates": int(os.getenv("FUZZY_MAX_CANDIDATES", "5")),
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
    "file": os.getenv("LOG_FILE", "lang2query.log"),
}

# Performance Configuration
PERFORMANCE_CONFIG = {
    "max_concurrent_agents": int(os.getenv("MAX_CONCURRENT_AGENTS", "3")),
    "timeout_seconds": int(os.getenv("TIMEOUT_SECONDS", "30")),
    "retry_attempts": int(os.getenv("RETRY_ATTEMPTS", "3")),
    "cache_results": os.getenv("CACHE_RESULTS", "true").lower() == "true",
}

# Current active configuration
ACTIVE_DATABASE = os.getenv("ACTIVE_DATABASE", "mysql")
ACTIVE_QUERY_LANGUAGE = os.getenv("ACTIVE_QUERY_LANGUAGE", "sql")
ACTIVE_DOMAIN = os.getenv("ACTIVE_DOMAIN", "ecommerce")

# Knowledge Base Configuration
KB_CONFIG = {
    "file_path": os.getenv("KB_FILE_PATH", "kb.pkl"),
    "auto_generate": os.getenv("KB_AUTO_GENERATE", "false").lower() == "true",
    "update_interval_hours": int(os.getenv("KB_UPDATE_INTERVAL_HOURS", "24")),
}

# Database Table Configuration
TABLE_CONFIG = {
    "customer_tables": os.getenv("CUSTOMER_TABLES", "customer,sellers").split(","),
    "orders_tables": os.getenv(
        "ORDERS_TABLES", "order_items,order_payments,order_reviews,orders"
    ).split(","),
    "product_tables": os.getenv("PRODUCT_TABLES", "products,category_translation").split(","),
}


def get_database_config():
    """Get the active database configuration."""
    return DATABASE_CONFIG[ACTIVE_DATABASE]


def get_query_language_config():
    """Get the active query language configuration."""
    return QUERY_LANGUAGE_CONFIG[ACTIVE_QUERY_LANGUAGE]


def get_domain_config():
    """Get the active domain configuration."""
    return DOMAIN_CONFIGS[ACTIVE_DOMAIN]


def get_model_config(component: str):
    """Get the model configuration for a specific component."""
    return MODEL_CONFIG.get(component, MODEL_CONFIG["routing"])


def get_api_key(provider: str):
    """Get API key for a specific provider."""
    return API_KEYS.get(provider)


def get_table_config():
    """Get the table configuration for the current domain."""
    return TABLE_CONFIG


def validate_config():
    """Validate that all required environment variables are set."""
    required_vars = [
        "ANTHROPIC_API_KEY",  # Required for default models
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    return True
