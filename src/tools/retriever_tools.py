"""
Retriever tools for the Text2Query system.

This module provides LangChain tools that wrap the SQL Knowledge Base retriever
functionality, allowing the LLM to intelligently retrieve schema information.
"""

import json
import logging
from typing import List, Dict, Any
from langchain_core.tools import tool
from config import KB_DIRECTORY, COLLECTION_NAME

logger = logging.getLogger(__name__)


@tool
def semantic_search(query: str, n_results: int = 5) -> str:
    """
    Perform semantic search across ALL database schema information (databases, tables, columns).

    This is the most general search tool - use it when you don't know which specific database/table
    to look in, or when you want to explore broadly. It searches by semantic meaning, not exact matches.

    Args:
        query: Natural language search query (e.g., "user authentication tables", "payment related columns")
        n_results: Number of results to return (default: 5, max recommended: 10)

    Returns:
        JSON with search results including:
        - documents: Schema descriptions/snippets
        - metadatas: Database, table, and chunk type information
        - distances: Semantic similarity scores (lower = more relevant)

    Use when:
    - User asks broad questions like "find tables related to payments"
    - You need to explore unknown databases/tables
    - Looking for schema patterns or relationships
    - Initial exploration phase

    Note: Returns mixed chunk types (database/table/column) - may need follow-up with specific tools.
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        results = retriever.semantic_search(query, n_results)

        documents = results.get('documents', [])
        metadatas = results.get('metadatas', [])
        distances = results.get('distances', [])

        # Format results as JSON for LLM consumption
        formatted_results = {
            "success": True,
            "query": query,
            "n_results": n_results,
            "total_found": len(documents[0]) if documents and len(documents) > 0 else 0,
            "documents": documents[0] if documents and len(documents) > 0 else [],
            "metadatas": metadatas[0] if metadatas and len(metadatas) > 0 else [],
            "distances": distances[0] if distances and len(distances) > 0 else []
        }

        return json.dumps(formatted_results, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in semantic_search: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "query": query
        })


@tool
def search_by_database(query: str, database_name: str, n_results: int = 5) -> str:
    """
    Search for schema information within a SPECIFIC database only.

    Use this when you know the exact database name and want to find relevant tables, columns,
    or schema information within that database. It filters out results from other databases.

    Args:
        query: Natural language search query scoped to the database (e.g., "user tables", "payment columns")
        database_name: Exact name of the database to search in (must exist)
        n_results: Number of results to return (default: 5)

    Returns:
        JSON with database-filtered search results including:
        - documents: Schema descriptions from the specified database
        - metadatas: Table and column information (all from specified database)
        - distances: Semantic similarity scores

    Use when:
    - You know the specific database (e.g., from get_all_databases())
    - User specifies a database: "find user tables in the auth database"
    - Need to avoid results from other databases
    - Want comprehensive results from one database

    Note: Returns mixed content types (tables/columns) from the specified database.
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        results = retriever.search_by_database(query, database_name, n_results)

        documents = results.get('documents', [])
        metadatas = results.get('metadatas', [])
        distances = results.get('distances', [])

        formatted_results = {
            "success": True,
            "query": query,
            "database": database_name,
            "n_results": n_results,
            "total_found": len(documents[0]) if documents and len(documents) > 0 else 0,
            "documents": documents[0] if documents and len(documents) > 0 else [],
            "metadatas": metadatas[0] if metadatas and len(metadatas) > 0 else [],
            "distances": distances[0] if distances and len(distances) > 0 else []
        }

        return json.dumps(formatted_results, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in search_by_database: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "query": query,
            "database": database_name
        })


@tool
def search_by_table(query: str, database_name: str, table_name: str, n_results: int = 5) -> str:
    """
    Search for detailed information within a SPECIFIC table in a SPECIFIC database.

    Use this for deep dives into a particular table's structure, columns, or content.
    This is the most precise search tool - results are filtered to one table only.

    Args:
        query: Natural language query about the table (e.g., "column details", "primary keys", "user fields")
        database_name: Exact name of the database containing the table
        table_name: Exact name of the table to search within
        n_results: Number of results to return (default: 5)

    Returns:
        JSON with table-specific search results including:
        - documents: Detailed column and table structure information
        - metadatas: Precise table and column metadata
        - distances: Semantic similarity scores

    Use when:
    - You need detailed column information for a specific table
    - User asks about a particular table: "show me the users table structure"
    - Looking for specific column details or constraints
    - Verifying table existence or structure

    Note: Best for focused questions about table internals. For general column info, use get_columns_by_table instead.
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        results = retriever.search_by_table(query, database_name, table_name, n_results)

        documents = results.get('documents', [])
        metadatas = results.get('metadatas', [])
        distances = results.get('distances', [])

        formatted_results = {
            "success": True,
            "query": query,
            "database": database_name,
            "table": table_name,
            "n_results": n_results,
            "total_found": len(documents[0]) if documents and len(documents) > 0 else 0,
            "documents": documents[0] if documents and len(documents) > 0 else [],
            "metadatas": metadatas[0] if metadatas and len(metadatas) > 0 else [],
            "distances": distances[0] if distances and len(distances) > 0 else []
        }

        return json.dumps(formatted_results, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in search_by_table: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "query": query,
            "database": database_name,
            "table": table_name
        })


@tool
def get_all_databases() -> str:
    """
    Get a complete list of ALL databases available in the knowledge base.

    This is your starting point for exploration - use this to discover what databases exist
    before using more specific search tools. Returns structured database information.

    Returns:
        JSON with complete database inventory including:
        - total_databases: Count of available databases
        - databases: Array of database objects with names, descriptions, and metadata

    Use when:
    - User asks "what databases exist?" or "show me available databases"
    - You need to discover database names for other tools
    - Initial assessment of the database landscape
    - User wants to see all database options

    Note: This returns structured data, not search results. Use search_by_database() for content searches within specific databases.
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        databases = retriever.get_all_databases()

        formatted_results = {
            "success": True,
            "total_databases": len(databases),
            "databases": databases
        }

        return json.dumps(formatted_results, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in get_all_databases: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def count_databases() -> str:
    """
    Get the TOTAL COUNT of databases available in the knowledge base (efficient count-only).

    Use this for questions like "how many databases are there?" or "what's the total database count?"
    This is much more efficient than get_all_databases() when you only need the count.

    Returns:
        JSON with database count:
        - total_databases: Number of databases

    Use when:
    - User asks "how many databases?" or "database count"
    - You need just the number, not the full list
    - Performance is important (no data retrieval/parsing)

    Note: Only returns count, not database details. Use get_all_databases() if you need database names.
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        count = retriever.count_databases()

        return json.dumps({
            "success": True,
            "total_databases": count
        }, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in count_databases: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def get_tables_in_database(database_name: str) -> str:
    """
    Get a complete list of ALL tables in a specific database.

    Use this after you've identified a database of interest (from get_all_databases())
    to see what tables are available within it. Returns structured table information.

    Args:
        database_name: Exact name of the database (must exist in knowledge base)

    Returns:
        JSON with complete table inventory for the database including:
        - database: The database name
        - total_tables: Count of tables in this database
        - tables: Array of table objects with names, descriptions, and metadata

    Use when:
    - User asks "what tables are in database X?" or "list tables in database Y"
    - You need to discover table names within a known database
    - Planning queries that need specific table knowledge
    - User wants to see all table options in a database

    Note: This returns structured data, not search results. Use search_by_table() for detailed column searches within specific tables.
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        tables = retriever.get_tables_in_database(database_name)

        formatted_results = {
            "success": True,
            "database": database_name,
            "total_tables": len(tables),
            "tables": tables
        }

        return json.dumps(formatted_results, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in get_tables_in_database: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "database": database_name
        })


@tool
def count_tables_in_database(database_name: str) -> str:
    """
    Get the TOTAL COUNT of tables in a specific database (efficient count-only).

    Use this for questions like "how many tables are in the wallet database?" or "table count in auth db".
    This is much more efficient than get_tables_in_database() when you only need the count.

    Args:
        database_name: Exact name of the database (must exist in knowledge base)

    Returns:
        JSON with table count:
        - database: The database name
        - total_tables: Number of tables in this database

    Use when:
    - User asks "how many tables in X database?" or "table count in Y db"
    - You need just the number, not the full table list
    - Performance is important (no data retrieval/parsing)

    Note: Only returns count, not table details. Use get_tables_in_database() if you need table names.
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        count = retriever.count_tables_in_database(database_name)

        return json.dumps({
            "success": True,
            "database": database_name,
            "total_tables": count
        }, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in count_tables_in_database: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "database": database_name
        })


@tool
def search_tables_in_databases(query: str, database_names: List[str], n_results: int = 5) -> str:
    """
    Search for TABLE SUMMARIES across MULTIPLE specific databases simultaneously.

    Use this when you want to find related tables across several databases at once,
    but only need table-level information (not column details). Perfect for cross-database
    table discovery and comparison.

    Args:
        query: Natural language search for table content (e.g., "user management tables", "payment tables")
        database_names: List of exact database names to search across (e.g., ["auth", "billing", "profile"])
        n_results: Number of results to return (default: 5)

    Returns:
        JSON with table-focused search results across specified databases including:
        - databases: List of databases searched
        - documents: Table summary descriptions from the specified databases
        - metadatas: Table metadata (database, table name, chunk_type="table")
        - distances: Semantic similarity scores

    Use when:
    - User wants tables from multiple databases: "find user tables in auth and profile databases"
    - Need to compare similar tables across databases
    - Looking for table patterns across database boundaries
    - Want table summaries, not detailed column information

    Note: Only returns table chunks (not columns or database-level info). Use get_columns_by_table() for detailed column info.
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        results = retriever.search_tables_in_databases(query, database_names, n_results)

        documents = results.get('documents', [])
        metadatas = results.get('metadatas', [])
        distances = results.get('distances', [])

        formatted_results = {
            "success": True,
            "query": query,
            "databases": database_names,
            "n_results": n_results,
            "total_found": len(documents[0]) if documents and len(documents) > 0 else 0,
            "documents": documents[0] if documents and len(documents) > 0 else [],
            "metadatas": metadatas[0] if metadatas and len(metadatas) > 0 else [],
            "distances": distances[0] if distances and len(distances) > 0 else []
        }

        return json.dumps(formatted_results, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in search_tables_in_databases: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "query": query,
            "databases": database_names
        })


@tool
def complex_filter_search(query: str, filters: Dict[str, Any], n_results: int = 5) -> str:
    """
    Perform ADVANCED filtered search with precise ChromaDB query conditions.

    Use this for complex, multi-criteria searches that other tools can't handle.
    Supports AND/OR logic, exact field matching, and any combination of metadata filters.

    Args:
        query: Natural language search query (semantic matching)
        filters: ChromaDB filter dictionary with advanced conditions, examples:
            - {"chunk_type": "table"} - Only table chunks
            - {"database_name": "auth"} - Only from auth database
            - {"chunk_type": "column", "table_name": "users"} - User table columns only
            - {"$or": [{"database_name": "auth"}, {"database_name": "billing"}]} - Multiple databases
            - {"$and": [{"chunk_type": "table"}, {"database_name": "auth"}]} - Complex AND conditions
        n_results: Number of results to return (default: 5)

    Returns:
        JSON with precisely filtered search results including:
        - filters: The filter conditions used
        - documents: Schema content matching all criteria
        - metadatas: Metadata matching the filter conditions
        - distances: Semantic similarity scores

    Use when:
    - Need precise filtering: "find all table chunks in the auth database"
    - Complex logic: "columns from users table OR profiles table"
    - Multiple conditions: "table summaries from auth database with 'user' in name"
    - Other tools don't provide the exact filtering you need

    Note: Most powerful but requires knowledge of metadata fields. Use simpler tools first when possible.
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        results = retriever.complex_filter_search(query, filters, n_results)

        documents = results.get('documents', [])
        metadatas = results.get('metadatas', [])
        distances = results.get('distances', [])

        formatted_results = {
            "success": True,
            "query": query,
            "filters": filters,
            "n_results": n_results,
            "total_found": len(documents[0]) if documents and len(documents) > 0 else 0,
            "documents": documents[0] if documents and len(documents) > 0 else [],
            "metadatas": metadatas[0] if metadatas and len(metadatas) > 0 else [],
            "distances": distances[0] if distances and len(distances) > 0 else []
        }

        return json.dumps(formatted_results, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in complex_filter_search: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "query": query,
            "filters": filters
        })


@tool
def get_columns_by_table(database_name: str, table_names: List[str]) -> str:
    """
    Get DETAILED column information for specific tables in a database.

    This is your go-to tool for complete column metadata including data types, keys,
    constraints, and relationships. Use this when you need the full schema details
    for SQL query generation or understanding table structures.

    Args:
        database_name: Exact name of the database containing the tables
        table_names: List of exact table names to get column details for (e.g., ["users", "orders"])

    Returns:
        JSON with comprehensive column information including:
        - database: The database name
        - tables: List of tables requested
        - results: Dictionary mapping table_name -> array of column objects with:
            * column_name, data_type, nullable, key_type (PRI/UNI/MUL), default_value, extra

    Use when:
    - User asks for column details: "show me all columns in users table"
    - Need complete schema for SQL generation: "what are the column types in orders?"
    - Require key information: "what are the primary keys in the users table?"
    - Building queries that need exact column knowledge

    Note: This provides the most detailed column information available. Use search_by_table() for semantic searches within table content.
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        table_columns = retriever.get_columns_by_table(database_name, table_names)

        formatted_results = {
            "success": True,
            "database": database_name,
            "tables": table_names,
            "results": table_columns
        }

        return json.dumps(formatted_results, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in get_columns_by_table: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "database": database_name,
            "tables": table_names
        })


@tool
def validate_database_exists(database_name: str) -> str:
    """
    VALIDATION TOOL: Check if a specific database exists in the knowledge base.

    Use this to validate database names before including them in queries or selections.
    This is essential for ensuring only valid databases are referenced.

    Args:
        database_name: Name of the database to validate

    Returns:
        "VALID: Database 'name' exists in knowledge base" if found,
        "INVALID: Database 'name' not found in knowledge base" if not found,
        or error message if validation fails

    Use when:
    - Validating user-suggested databases
    - Checking if a database exists before referencing it
    - Ensuring database names are correct
    - Human-in-the-loop validation workflows
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        all_databases = retriever.get_all_databases()
        existing_db_names = {db['database'] for db in all_databases}

        if database_name in existing_db_names:
            return f"VALID: Database '{database_name}' exists in knowledge base"
        else:
            return f"INVALID: Database '{database_name}' not found in knowledge base"
    except Exception as e:
        logger.error(f"Error in validate_database_exists: {e}")
        return f"ERROR: Failed to validate database '{database_name}': {str(e)}"


@tool
def validate_table_exists(table_name: str, database_name: str = None) -> str:
    """
    VALIDATION TOOL: Check if a specific table exists in the given database or available databases.

    Use this to validate table names before including them in queries. This ensures
    only valid tables are referenced in SQL generation.

    Args:
        table_name: Name of the table to validate (can be 'table' or 'database.table')
        database_name: Optional specific database to check in (if not provided, checks all available)

    Returns:
        "VALID: Table 'database.table' exists in knowledge base" if found,
        "INVALID: Table 'name' not found in available databases" if not found,
        or error message if validation fails

    Use when:
    - Validating user-suggested tables
    - Checking table existence before query generation
    - Ensuring table names are correct
    - Human-in-the-loop validation workflows
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )

        # Parse table name format
        if '.' in table_name:
            db_name, tbl_name = table_name.split('.', 1)
            search_databases = [db_name]
        else:
            tbl_name = table_name
            if database_name:
                search_databases = [database_name]
            else:
                # If no specific database, check all available databases
                all_databases = retriever.get_all_databases()
                search_databases = [db['database'] for db in all_databases]

        if not search_databases:
            return f"ERROR: No databases available to search for table '{table_name}'"

        # Search for table in databases
        for db in search_databases:
            try:
                tables_in_db = retriever.get_tables_in_database(db)
                table_names = {t['table'] for t in tables_in_db}
                if tbl_name in table_names:
                    full_table_name = f"{db}.{tbl_name}"
                    return f"VALID: Table '{full_table_name}' exists in knowledge base"
            except Exception as e:
                logger.warning(f"Error searching tables in database {db}: {e}")
                continue

        return f"INVALID: Table '{table_name}' not found in available databases: {search_databases}"
    except Exception as e:
        logger.error(f"Error in validate_table_exists: {e}")
        return f"ERROR: Failed to validate table '{table_name}': {str(e)}"


@tool
def search_similar_tables(query: str, database_names: List[str] = None, limit: int = 10) -> str:
    """
    VALIDATION TOOL: Search for tables similar to the query in specified databases.

    Use this when user suggests invalid table names to find similar/related tables
    that might be what they intended. This helps with typo correction and alternative suggestions.

    Args:
        query: Search query for finding relevant tables (e.g., "user", "payment", "transaction")
        database_names: List of databases to search in (optional, searches all if not specified)
        limit: Maximum number of results to return

    Returns:
        "FOUND: X relevant tables: table1, table2, ..." if results found,
        "NO_RESULTS: No tables found matching the query" if no matches,
        or error message if search fails

    Use when:
    - User suggests invalid table names and you want to suggest alternatives
    - Finding related tables for a concept
    - Typo correction for table names
    - Exploring what tables exist for a domain
    """
    try:
        from retriever.retrieve_sql_kb import SQLKnowledgeBaseRetriever

        retriever = SQLKnowledgeBaseRetriever(
            chroma_persist_dir=str(KB_DIRECTORY),
            collection_name=COLLECTION_NAME
        )

        if not database_names:
            # If no databases specified, search all available
            all_databases = retriever.get_all_databases()
            database_names = [db['database'] for db in all_databases]

        if not database_names:
            return "ERROR: No databases available for search"

        # Search for tables in databases
        results = retriever.search_tables_in_databases(query, database_names, n_results=limit)

        if results and results.get('metadatas') and results['metadatas'][0]:
            found_tables = []
            for meta in results['metadatas'][0][:limit]:
                if meta.get('database_name') and meta.get('table_name'):
                    found_tables.append(f"{meta['database_name']}.{meta['table_name']}")

            if found_tables:
                return f"FOUND: {len(found_tables)} relevant tables: {', '.join(found_tables)}"
            else:
                return "NO_RESULTS: No relevant tables found for the query"
        else:
            return "NO_RESULTS: No tables found matching the query"
    except Exception as e:
        logger.error(f"Error in search_similar_tables: {e}")
        return f"ERROR: Failed to search for tables: {str(e)}"
        

__all__ = [
    "semantic_search",
    "search_by_database",
    "search_by_table",
    "get_all_databases",
    "get_tables_in_database",
    "count_databases",
    "count_tables_in_database",
    "search_tables_in_databases",
    "complex_filter_search",
    "get_columns_by_table",
    "validate_database_exists",
    "validate_table_exists",
    "search_similar_tables"
]