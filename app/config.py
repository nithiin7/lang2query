"""
Configuration file for the Lang2Query system.
This file contains settings that can be easily modified to support different query languages and databases.
"""

# Database Configuration
DATABASE_CONFIG = {
    "mysql": {
        "connection_string": "mysql+mysqlconnector://root:Indianarmy@localhost/txt2sql",
        "dialect": "mysql",
        "driver": "mysqlconnector",
    },
    "postgresql": {
        "connection_string": "postgresql://user:password@localhost/dbname",
        "dialect": "postgresql",
        "driver": "psycopg2",
    },
    "sqlite": {
        "connection_string": "sqlite:///./database.db",
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
        "provider": "anthropic",  # "anthropic", "groq", "openai"
        "model": "claude-3-5-sonnet-20240620",
        "temperature": 0.4,
    },
    "query_generation": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20240620",
        "temperature": 0.1,
    },
    "validation": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20240620",
        "temperature": 0.0,
    },
}

# Fuzzy Matching Configuration
FUZZY_MATCHING_CONFIG = {
    "scorer": "token_set_ratio",  # "ratio", "partial_ratio", "token_sort_ratio", "token_set_ratio"
    "min_confidence": 70,
    "max_candidates": 5,
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "lang2query.log",
}

# Performance Configuration
PERFORMANCE_CONFIG = {
    "max_concurrent_agents": 3,
    "timeout_seconds": 30,
    "retry_attempts": 3,
    "cache_results": True,
}

# Current active configuration
ACTIVE_DATABASE = "mysql"
ACTIVE_QUERY_LANGUAGE = "sql"
ACTIVE_DOMAIN = "ecommerce"


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
