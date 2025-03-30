import logging
import json
import re
from GlobalVariables import global_vars as gv
from FieldUnifier import generate_final_fields, DF_TO_DB_FIELDS, DB_TO_DF_FIELDS, CONVERSION_TABLE_2DF, COMPONENTS
from MongoDB.DatabaseManager import DatabaseManager

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
    if column.lower() == 'name':
        # If querying 'Fusion', match 'Deck A' and 'Deck B' instead of 'Name'
        fields = ['myDecks.name'] if collection_name == 'Fusion' else ['name']
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
        'Fusion': generate_final_fields('Detail', 'Stats', 'Fusion', rename_fields_to=rename_fields_to),
    }

    return default_projections.get(collection_name, [])

def build_aggregation_pipeline(  filter_query, projection_fields, rename_mapping=None, conversion_table=None, expanded_field=None, expanded_field_keys=None ):
    """
    Constructs the MongoDB aggregation pipeline with field projections, renaming,
    dictionary expansion, and optional field conversions.

    Args:
        filter_query (dict): MongoDB filter query.
        projection_fields (list): List of fields to include in the projection.
        rename_mapping (dict, optional): Mapping of field names to rename.
        conversion_table (dict, optional): Conversion mapping for computed fields.
        expanded_field (str, optional): Name of the dictionary field to expand into separate fields.
        expanded_field_keys (list, optional): List of expected keys inside the expanded field.

    Returns:
        list: Aggregation pipeline for MongoDB query.
    """
    pipeline = [{"$match": filter_query}]

    # Step 1: Expand the dictionary field into separate fields (if it exists)
    if expanded_field:
        pipeline.extend([
            { "$addFields": { "expanded_fields": { "$objectToArray": f"${expanded_field}" } } },
            { "$addFields": {
                "merged_fields": {
                    "$mergeObjects": ["$$ROOT", { "$arrayToObject": "$expanded_fields" }]
                }
            }},
            { "$replaceRoot": { "newRoot": "$merged_fields" } },
            { "$unset": [expanded_field, "expanded_fields"] }
        ])

    # Step 2: Apply field transformations from `conversion_table`
    projection_stage = {"_id": 1}  # Always include document ID

    if conversion_table:
        for field_path, new_field in conversion_table.items():
            mongo_expression = convert_field_path(field_path)
            pipeline.append({"$addFields": {new_field: mongo_expression}})
            projection_stage[new_field] = 1  # Ensure inclusion in projection

    # Step 3: Convert and truncate date fields
    pipeline.append({
        "$addFields": {
            "pExpiry": {
                "$cond": {
                    "if": { "$eq": [{ "$type": "$pExpiry" }, "string"] },  # Check if it's a string
                    "then": {
                        "$dateFromString": {
                            "dateString": "$pExpiry",
                            "onError": None  # Avoids errors if conversion fails
                        }
                    },
                    "else": "$pExpiry"  # Keep it unchanged if it's already a date
                }
            }
        }
    })

    pipeline.append({
        "$addFields": {
            "pExpiry": {
                "$dateToString": {
                    "format": "%Y-%m-%d",
                    "date": "$pExpiry",
                    "onNull": None  # Avoids errors if the date is missing
                }
            }
        }
    })

    # Step 4: Ensure all requested projection fields are included
    for field in projection_fields:
        projection_stage[field] = 1

    # Step 5: Include all predefined expanded fields explicitly
    if expanded_field_keys:
        for key in expanded_field_keys:
            projection_stage[key] = 1

    # Step 6: **Apply renaming without removing existing fields**
    if rename_mapping:
        renamed_projection_stage = {}
        for old_field, new_field in rename_mapping.items():
            if old_field in projection_stage:
                renamed_projection_stage[new_field] = f"${old_field}"  # Rename the field
            else:
                renamed_projection_stage[new_field] = {"$ifNull": [f"${old_field}", None]}  # Ensure it still exists

        projection_stage.update(renamed_projection_stage)  # Merge renamed fields while keeping all others
    # Step 7: Construct the projection stage
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

def convert_field_path(field_path):
    """
    Converts a string-based field path (e.g., "myDecks[0].forgeborn.faction") 
    into a MongoDB aggregation expression.

    Args:
        field_path (str): The field path, potentially containing array indices 
                          (e.g., "myDecks[0].forgeborn.faction").

    Returns:
        dict or str: MongoDB-compatible field access expression.
    """
    # Split the path into segments (handling both dot notation & array indices)
    path_segments = re.split(r'\.|\[|\]', field_path)
    path_segments = [seg for seg in path_segments if seg]  # Remove empty entries

    # Base case: Single segment (no arrays involved)
    if len(path_segments) == 1:
        return f"${path_segments[0]}"

    # Process segments recursively
    expression = f"${path_segments[0]}"  # Start with the base field

    for i in range(1, len(path_segments)):
        segment = path_segments[i]
        if segment.isdigit():  # If segment is a number, it's an array index
            expression = {"$arrayElemAt": [expression, int(segment)]}
        else:  # Otherwise, it's a nested field
            expression = {"$getField": {"field": segment, "input": expression}}

    return expression

def fetch_filtered_documents(collection_name, filter_df=None, filter_query=None, 
                             projection_fields=None, final_format=None, 
                             expanded_field=None, match_titles=False):
    """
    Fetch documents from a MongoDB collection using either a filter DataFrame or a direct query.

    Args:
        collection_name (str): The MongoDB collection to query (e.g., 'Deck', 'Fusion').
        filter_df (pd.DataFrame, optional): DataFrame containing filter conditions.
        filter_query (dict, optional): Direct MongoDB query.
        projection_fields (list, optional): List of fields to include.
        info_level (str, optional): Level of detail for information logging. Defaults to 'Basic'.
        data_set (str, optional): Data set designation for the query. Defaults to 'Stats'.

    Returns:
        list: List of matching documents.
    """
    dbmgr = gv.myDB or DatabaseManager(gv.username)
    if dbmgr is None:
        logging.error("No active database connection.")
        return []

    conversion_table = CONVERSION_TABLE_2DF if collection_name == 'Fusion' else None

    # Step 1: Determine query source
    if filter_query:
        query = filter_query  # Use provided direct MongoDB query
    elif filter_df is not None:
        query = generate_mongo_query(filter_df, collection_name)  # Generate query from DataFrame
    else:
        query = {}  # Default empty query (fetch all)

    if query:        
        myQuery = query_to_mongo_format(query)
        #logging.debug(f"Final query: {myQuery}")

    # Step 2: Use dynamically determined projection fields based on `info_level` and `data_set`
    projection_fields = get_projection_fields(collection_name, rename_fields_to=final_format) if projection_fields is None else projection_fields

    # Step 3: Build aggregation pipeline
    query_format = None
    if final_format: 
        if final_format.lower() == "df":
          query_format = DB_TO_DF_FIELDS  
        elif final_format.lower() == "db":
          query_format = DF_TO_DB_FIELDS  
        else:
            logging.error(f"Unknown format for query : {final_format}")
    
    
    expanded_field_keys = COMPONENTS['Graph'] if expanded_field else None
    
    pipeline = build_aggregation_pipeline(query, projection_fields, query_format, conversion_table= conversion_table, expanded_field=expanded_field, expanded_field_keys=expanded_field_keys)
    

    # DEBUG: Print the full aggregation pipeline before executing
    #logging.debug("Executing MongoDB Aggregation Pipeline:")
    #logging.debug(json.dumps(pipeline, indent=4))

    # Step 4: Execute the query and track missing fields
    missing_fields = set(projection_fields)  # Assume all fields are missing initially
    results = []

    matched_titles_set = set()
    
    # Step 5: Execute database query
    try:
        # Convert list fields to semicolon-separated strings                        
        convert_list_fields = {'Fusion': ['Set', 'Digital']}  # Define collection-specific fields
        
        collection = dbmgr.get_collection(collection_name)
        for document in collection.aggregate(pipeline):
            
            # Set Type to collection_name if needed 
            if 'Type' in projection_fields:
                document['Type'] = collection_name
            elif 'type' in projection_fields:
                document['type'] = collection_name
            
            # Convert list fields to strings only for the correct collection
            if collection_name in convert_list_fields:
                for field in convert_list_fields[collection_name]:  # Loop through fields
                    if field in document:
                        if isinstance(document[field], list):
                            document[field] = ";".join(map(str, document[field]))
                        else:
                            logging.warning(f"Expected list for field '{field}', but got {type(document[field])}. Skipping conversion.")

            # Match card titles if requested
            if match_titles:
                # Collect matched card titles
                card_titles = document.get("CardTitles", "")
                card_names = [name.strip() for name in card_titles.split(";") if name.strip()]
                
                # Match user-defined substrings (from query config)
                for column, value in filter_df.iloc[0].items():
                    if column in ['Modifier', 'Creature', 'Spell'] and isinstance(value, str):
                        substrings = re.split(r'\s*[|:;,+&-]\s*', value)  # Split on logical operators
                        for substring in substrings:
                            matched_titles_set.update(
                                [title for title in card_names if re.search(rf'\b{re.escape(substring)}\b', title, re.IGNORECASE)]
                            )

            # if results:
            #     logging.debug("Sample MongoDB Output:")
            #     logging.debug(json.dumps(results[:2], indent=4))

            results.append(document)

            # Determine missing fields for this document individually
            missing_fields = set(projection_fields) - set(document.keys())

            # Log missing fields only if there are any for this document
            if missing_fields:
                logging.warning(f"Missing fields in document {document.get('_id', 'unknown')}: {missing_fields}")

    except Exception as e:
        logging.error(f"Error fetching documents from {collection_name}: {e}")
        return []
    
    if matched_titles_set:
        logging.debug(f"Matched titles: {matched_titles_set}")
            
        return {
            "documents": results,
            "matched_titles": sorted(matched_titles_set)
        }
        
    return results