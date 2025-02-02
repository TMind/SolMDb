import logging
import json
import re
from GlobalVariables import global_vars as gv
from FieldUnifier import generate_final_fields, DF_TO_DB_FIELDS, DB_TO_DF_FIELDS

def determine_filter_config(column, value, collection_name):
    """
    Determines the filtering configuration for a given column and value.

    Args:
        column (str): The column to be filtered.
        value (str): The filter value entered by the user.
        collection_name (str): The name of the collection being queried (e.g., 'Deck', 'Fusion').

    Returns:
        dict: Configuration containing the fields to search, substrings to match, and the logical operator.
    """
    # Define valid logical operators
    operators = {
        'AND': {':', '&', '+'},  # AND operators
        'OR': {'|', '-', ';'}     # OR operators
    }

    # Determine if the value contains an OR operator; otherwise, default to AND
    operator = 'OR' if any(op in value for op in operators['OR']) else 'AND'
    
    # Split the input value into substrings using detected operators
    substrings = re.split(rf"\s*[{re.escape(''.join(operators[operator]))}]\s*", value)

    # Define field mappings based on the collection type
    if column == 'Name':
        # If querying 'Fusion', match 'Deck A' and 'Deck B' instead of 'Name'
        fields = ['Deck A', 'Deck B'] if collection_name == 'Fusion' else ['Name']
    elif column == 'Forgeborn Ability':
        # Match across multiple Forgeborn ability columns using OR
        fields, operator = ['FB2', 'FB3', 'FB4'], 'OR'
    else:
        # Default to 'CardTitles' if the column doesn't match special cases
        fields = ['CardTitles']

    return {
        'fields': fields,
        'substrings': substrings,
        'operator': operator
    }

def build_query(config):
    """ Constructs MongoDB query syntax from filter configuration. """
    field_queries = [
        {field: {"$regex": re.escape(substr), "$options": "i"}}
        for field in config['fields'] for substr in config['substrings']
    ]
    return {"$and" if config['operator'] == 'AND' else "$or": field_queries}

def process_filter_row(filter_row, collection_name):
    """ Processes a single filter row and generates a MongoDB query. """
    query = {}
    mandatory_fields = filter_row.get('Mandatory Fields', '').split(', ')
    and_conditions, or_conditions = [], []

    for column, value in filter_row.items():
        if column in ['Type', 'Mandatory Fields', 'Active'] or not isinstance(value, str) or not value.strip():
            continue
        config = determine_filter_config(column, value, collection_name)
        query_part = build_query(config)

        if column in mandatory_fields:
            and_conditions.append(query_part)
        else:
            or_conditions.append(query_part)

    if and_conditions:
        query["$and"] = and_conditions
    if or_conditions:
        query["$or"] = or_conditions
    
    return query

def generate_mongo_query(filter_df, collection_name):
    """ Converts a filter DataFrame into a MongoDB query. """
    if filter_df is None or filter_df.empty:
        return {}  # Return an empty query if no filters are provided

    filter_conditions = [process_filter_row(row, collection_name) for _, row in filter_df.iterrows()]
    return {"$or": filter_conditions} if filter_conditions else {}

def get_projection_fields(collection_name, rename_fields_to=None):
    """
    Returns projection fields and field renaming for MongoDB queries.
    """
    default_projections = {
        'Deck': generate_final_fields('Detail', 'Stats', 'Deck', rename_fields_to=rename_fields_to),
        'Fusion': generate_final_fields('Detail', 'Stats', 'Fusion', rename_fields_to=rename_fields_to)
    }

    return default_projections.get(collection_name, [])

def build_aggregation_pipeline0(filter_query, projection_fields, rename_mapping):
    """
    Constructs the MongoDB aggregation pipeline.
    """
    return [
        {"$match": filter_query},
        {"$addFields": {
            "CardTitles": {
                "$reduce": {
                    "input": "$CardTitles",
                    "initialValue": "",
                    "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", "; "]}, "$$this"]}
                }
            },
            **{new_field: f"${old_field}" for old_field, new_field in rename_mapping.items()}
        }},
        {"$unset": list(rename_mapping.keys())},
        {"$project": {**{field: 1 for field in projection_fields if field not in rename_mapping}, **{new_field: 1 for _, new_field in rename_mapping.items()}}}
    ]
    
def build_aggregation_pipeline(filter_query, projection_fields, rename_mapping=None):
    """
    Constructs the MongoDB aggregation pipeline with field projections and renaming.

    Args:
        filter_query (dict): MongoDB filter query.
        projection_fields (list): List of fields to include in the projection.
        rename_mapping (dict, optional): Mapping of field names to rename.

    Returns:
        list: Aggregation pipeline for MongoDB query.
    """
    pipeline = [{"$match": filter_query}]

    # Apply renaming and projection
    projection_stage = {}

    # Step 1: Apply field renaming
    if rename_mapping:
        for old_field, new_field in rename_mapping.items():
            projection_stage[new_field] = f"${old_field}"

    # Step 2: Ensure all requested projection fields are included
    for field in projection_fields:
        if field not in rename_mapping:  # If it's not a renamed field, include it directly
            projection_stage[field] = 1

    # Step 3: Construct the projection stage
    if projection_stage:
        pipeline.append({"$project": projection_stage})

    return pipeline

def query_to_mongo_format(query):
    """
    Converts a MongoDB query dictionary or JSON string to a MongoDB-compatible string.
    
    Args:
        query (dict or str): The MongoDB query dictionary or JSON string.
        
    Returns:
        str: The properly formatted MongoDB query string.
    """
    # If the query is a dictionary, first convert it to a JSON string
    if isinstance(query, dict):
        json_query = json.dumps(query, indent=4)
    else:
        json_query = query

    # Replace JSON-style operator keys ("$key") with MongoDB format ($key)
    mongo_query = re.sub(r'"\$(\w+)"\s*:', r'$\1:', json_query)

    return mongo_query


def fetch_filtered_documents(collection_name, filter_df=None, projection_fields=None):
    """
    Fetch documents from a MongoDB collection using an aggregation pipeline.

    Args:
        collection_name (str): The MongoDB collection to query (e.g., 'Deck', 'Fusion').
        filter_df (pd.DataFrame, optional): DataFrame containing filter conditions.
        projection_fields (list, optional): List of fields to include.

    Returns:
        list: List of matching documents.
    """
    if gv.myDB is None:
        logging.error("No active database connection.")
        return []

    # Step 1: Generate MongoDB query from filter_df (if provided)
    query = generate_mongo_query(filter_df, collection_name) if filter_df is not None else {}
    
    if query:
        myQuery = query_to_mongo_format(query)
    #    print(f"Final query: {myQuery}")

    # Step 2: Use default projection fields if none provided
    projection_fields = get_projection_fields(collection_name, rename_fields_to='db') if projection_fields is None else projection_fields

    # Step 3: Build aggregation pipeline
    pipeline = build_aggregation_pipeline(query, projection_fields, DB_TO_DF_FIELDS)

    # Step 4: Execute the query and track missing fields
    missing_fields = set(projection_fields)  # Assume all fields are missing initially
    results = []

    # Step 5: Execute database query
    try:
        collection = gv.myDB.get_collection(collection_name)
        for document in collection.aggregate(pipeline):
            results.append(document)

            # Remove found fields from the missing list
            missing_fields -= set(document.keys())

    except Exception as e:
        logging.error(f"Error fetching documents from {collection_name}: {e}")
        return []
    
    # Step 6: Log missing fields
    if missing_fields:
        logging.warning(f"Missing fields in the query results: {missing_fields}")
        
    return results