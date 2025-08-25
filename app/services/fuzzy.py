import pandas as pd
from rapidfuzz import fuzz, process
from sqlalchemy import create_engine

from app.config import get_database_config, FUZZY_MATCHING_CONFIG

# Get database configuration
database_config = get_database_config()
database_engine = create_engine(database_config["connection_string"])


def find_best_fuzzy_match(input_value: str, available_choices: list[str]):
    """Find the best fuzzy match for an input value from available choices."""
    # Get fuzzy matching configuration
    scorer_name = FUZZY_MATCHING_CONFIG["scorer"]
    min_confidence = FUZZY_MATCHING_CONFIG["min_confidence"]
    max_candidates = FUZZY_MATCHING_CONFIG["max_candidates"]
    
    # Map scorer names to actual functions
    scorer_map = {
        "ratio": fuzz.ratio,
        "partial_ratio": fuzz.partial_ratio,
        "token_sort_ratio": fuzz.token_sort_ratio,
        "token_set_ratio": fuzz.token_set_ratio,
    }
    
    scorer = scorer_map.get(scorer_name, fuzz.token_set_ratio)
    
    best_match, confidence_score, _ = process.extractOne(
        input_value, available_choices, scorer=scorer
    )
    
    # Only return matches above minimum confidence
    if confidence_score >= min_confidence:
        return best_match, confidence_score
    else:
        return None, confidence_score


def get_distinct_column_values(table_name: str, column_name: str):
    """Get distinct values from a specific column in a table."""
    # SQL query to get distinct values
    query = f"SELECT DISTINCT {column_name} FROM {table_name}"

    # Execute query and load results into DataFrame
    df = pd.read_sql(query, con=database_engine)

    # Convert to list of unique values
    unique_values = df[column_name].dropna().tolist()
    return unique_values


def apply_fuzzy_matching_to_filters(filter_conditions: list):
    """Apply fuzzy matching to filter conditions for better accuracy."""
    matched_filters = []

    for filter_condition in filter_conditions[1:]:  # Skip header
        table_name = filter_condition[0]
        column_name = filter_condition[1]
        filter_values = [value.strip() for value in filter_condition[2].split(",")]

        # Get available values from the database
        available_values = get_distinct_column_values(table_name, column_name)
        available_values = [str(value) for value in available_values]

        # Apply fuzzy matching to each filter value
        for filter_value in filter_values:
            best_match, confidence_score = find_best_fuzzy_match(filter_value, available_values)
            
            if best_match:  # Only add if we found a good match
                matched_filters.append(
                    [
                        f"table_name:{table_name}",
                        f"column_name:{column_name}",
                        f"filter_value:{best_match}",
                        f"confidence:{confidence_score}",
                    ]
                )
            else:
                # Log low confidence matches for debugging
                print(f"Low confidence match for '{filter_value}' in {table_name}.{column_name}: {confidence_score}")

    return matched_filters
