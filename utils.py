import logging
import pandas as pd 
import qgridnext as qgrid
from datetime import datetime
from IPython.display import display
from GlobalVariables import GLOBAL_COLUMN_ORDER, global_vars as gv 

def get_totals_row(df, rotated_column_definitions):
    """
    Helper method to generate the totals row from the current DataFrame.
    For numeric columns, sum values; for non-numeric columns, return an empty string or appropriate label.
    """
    numeric_df = df.copy()
    numeric_cols = [col for col in df.columns if col in rotated_column_definitions]

    for col in numeric_cols:
        numeric_df[col] = pd.to_numeric(numeric_df[col], errors='coerce')

    totals = numeric_df[numeric_cols].sum(numeric_only=True)

    totals_row = pd.DataFrame(totals).T
    totals_row['DeckName'] = 'Totals'

    for col in df.columns:
        if col not in totals_row.columns:
            totals_row[col] = ''

    totals_row = totals_row[df.columns]
    return totals_row

from dateutil import parser
import pytz

def compare_times(time_str1, time_str2, default_timezone=pytz.UTC):
    """
    Compares two time strings that may be in different formats and timezones.
    
    Parameters:
    - time_str1: The first time string.
    - time_str2: The second time string.
    - default_timezone: The timezone to assume if a time string has no timezone info (default is UTC).
    
    Returns:
    - -1 if time_str1 is earlier than time_str2.
    -  0 if time_str1 is equal to time_str2.
    -  1 if time_str1 is later than time_str2.
    - None if there is an error parsing the time strings.
    """
    try:
        # Parse the first time string
        dt1 = parser.parse(time_str1)
        # Parse the second time string
        dt2 = parser.parse(time_str2)
    except (ValueError, TypeError) as e:
        print(f"Error parsing time strings: {e}")
        return None
    
    # Ensure both datetime objects are timezone-aware
    # If timezone is missing, assign the default timezone
    if dt1.tzinfo is None:
        dt1 = default_timezone.localize(dt1)
    else:
        dt1 = dt1.astimezone(default_timezone)
        
    if dt2.tzinfo is None:
        dt2 = default_timezone.localize(dt2)
    else:
        dt2 = dt2.astimezone(default_timezone)
    
    # Compare the datetime objects
    if dt1 < dt2:
        return -1  # time_str1 is earlier
    elif dt1 > dt2:
        return 1   # time_str1 is later
    else:
        return 0   # times are equal
    
def get_min_time(time_strings, default_timezone=pytz.UTC, output_format='%Y-%m-%d %H:%M:%S%z'):
    """
    Returns the earliest time from a list of time strings.

    Parameters:
    - time_strings: A list of time strings.
    - default_timezone: The timezone to assume if a time string has no timezone info (default is UTC).
    - output_format: The format string to output the time (default includes timezone offset).

    Returns:
    - The earliest time as a formatted string.
    - None if there is an error parsing the time strings or if the list is empty.
    """
    if not time_strings:
        return None

    min_dt = None

    for time_str in time_strings:
        if not time_str:
            continue  # Skip empty strings
        try:
            # Parse the time string
            dt = parser.parse(time_str)
        except (ValueError, TypeError) as e:
            print(f"Error parsing time string '{time_str}': {e}")
            continue  # Skip invalid time strings

        # Ensure datetime object is timezone-aware
        if dt.tzinfo is None:
            dt = default_timezone.localize(dt)
        else:
            dt = dt.astimezone(default_timezone)

        # Update min_dt if this datetime is earlier
        if (min_dt is None) or (dt < min_dt):
            min_dt = dt

    if min_dt is not None:
        # Return the earliest time as a formatted string
        #print(f"Returning min time: {min_dt}")
        return min_dt.strftime(output_format)
    else:
        # All time strings were invalid
        return None
    
    
def normalize_time_string(time_string, target_format="%Y-%m-%d %H:%M:%S", cutoff="none"):
    """
    Normalize a time string to a consistent format with options to truncate components.

    Parameters:
        time_string (str): The input time string to be normalized.
        target_format (str): The target format for the normalized time string (default: "%Y-%m-%d %H:%M:%S").
        cutoff (str): The granularity to truncate. Options:
                      - "milliseconds": Remove milliseconds.
                      - "seconds": Remove seconds and milliseconds.
                      - "minutes": Remove minutes, seconds, and milliseconds.
                      - "hours": Remove hours, minutes, seconds, and milliseconds.
                      - "none": No truncation (default).

    Returns:
        str: The normalized and truncated time string.
    """
    # Skip if time_string is empty
    if not time_string:
        return time_string
    try:
        # Parse ISO 8601 format with or without timezone information
        dt = datetime.fromisoformat(time_string.replace("Z", "+00:00"))

        # Truncate the format string based on the cutoff level
        if cutoff == "milliseconds":
            target_format = "%Y-%m-%d %H:%M:%S"
        elif cutoff == "seconds":
            target_format = "%Y-%m-%d %H:%M"
        elif cutoff == "minutes":
            target_format = "%Y-%m-%d %H"
        elif cutoff == "hours":
            target_format = "%Y-%m-%d"

        # Format the datetime object to the desired format
        finalized_time_string = dt.strftime(target_format)
        #print(f"Normalized original time string: {time_string} -> {finalized_time_string}")
        return finalized_time_string
    
    except ValueError as e:
        raise ValueError(f"Invalid time string format: {time_string}") from e
    
# Functions to work with dataframes and MongoDB
    
def fetch_data_from_db(collection_name, filter_df=None, projection=None):
    """
    Fetches data from the specified collection in the database.

    Args:
        collection_name (str): Name of the collection to query ('Deck' or 'Fusion').
        filter_df (pd.DataFrame, optional): DataFrame containing names to filter.
                                            If None, fetches all documents from the collection.
        projection (dict, optional): A dictionary specifying the fields to include or exclude
                                     in the result. Defaults to None (all fields).

    Returns:
        list: A list of documents fetched from the database.
    """
    query = {}
    if filter_df is not None:
        item_names = filter_df.index.tolist()        
        query = {'name': {'$in': item_names}}

    if gv.myDB:
        # Pass the projection parameter to the find method
        items = list(gv.myDB.find(collection_name, query, projection))
        if not items:
            logging.warning(f"No {collection_name.lower()}s found.")
        return items
    else:
        logging.error("Database connection is not initialized.")
        return []

def enforce_column_order(df, column_order):
    """
    Ensure the DataFrame has the columns in the specified order, 
    but only includes columns that are present in the DataFrame.
    """
    existing_columns = [col for col in column_order if col in df.columns]
    extra_columns = [col for col in df.columns if col not in column_order]
    if extra_columns:
        logging.info(f"Columns not in order: {extra_columns}")
    return df.reindex(columns=existing_columns)

def merge_by_adding_columns(df1, df2):
    """
    Merges two DataFrames by adding new columns from df2 to df1. 
    Assumes the indices are the same and there are no new rows to add.
    
    Parameters:
    - df1: First DataFrame.
    - df2: Second DataFrame.
    
    Returns:
    - A DataFrame that contains all columns from both df1 and df2, aligned by index.
    """
    # Ensure both DataFrames have the same index
    if not df1.index.equals(df2.index):
        raise ValueError("The indices of both DataFrames must be the same to merge by adding columns.")

    # Merge DataFrames by concatenating columns
    merged_df = pd.concat([df1, df2], axis=1)
    
    return merged_df

def merge_and_concat(df1, df2):
    """
    Efficiently merges two DataFrames by handling overlapping columns and concatenating them row-wise,
    ensuring all columns, including 'deckScore', are preserved.
    """
    # Concatenate both DataFrames row-wise without dropping any columns
    combined_df = pd.concat([df1, df2], axis=0, sort=False)
    
    # If needed, you can fill missing values with NaN (or other strategies)
    #combined_df = combined_df.fillna(value=np.nan)
    
    return combined_df

def clean_columns(df, exclude_columns=None):
    """
    Cleans both numeric and non-numeric columns of a DataFrame.

    Args:
        df (pd.DataFrame): DataFrame to clean.
        exclude_columns (list, optional): List of columns to exclude from cleaning.

    Returns:
        pd.DataFrame: Cleaned DataFrame.
    """
    if exclude_columns is None:
        exclude_columns = []

    df = df.copy()
    numeric_cols = df.select_dtypes(include='number').columns.difference(exclude_columns)
    numeric_df = df[numeric_cols].fillna(0.0).astype(str).replace('0.0', '')
    df[numeric_cols] = numeric_df

     # Clean non-numeric columns
    non_numeric_cols = df.select_dtypes(exclude='number').columns
    df[non_numeric_cols] = (
        df[non_numeric_cols]
        .fillna('')
        .apply(lambda col: col.map(lambda x: '' if x == '0' else x))
    )

    return df

def validate_dataframe_attributes(df, identifier=None, expected_index_name=None, disallow_columns=None):
    """
    Validate the attributes of a DataFrame.

    Parameters:
    - df (pd.DataFrame): The DataFrame to validate.
    - identifier (str, optional): An identifier for the DataFrame being checked.
    - expected_index_name (str, optional): The expected name of the index.
    - disallow_columns (list, optional): A list of column names that should not be present in the DataFrame.

    Returns:
    - dict: A dictionary containing validation results.
    """
    validation_results = {
        'index_name_correct': True,
        'unwanted_columns_present': False,
        'unwanted_columns': [],
        'messages': []
    }
    
    # Check if the index name matches the expected index name
    if expected_index_name is not None:
        if df.index.name != expected_index_name:
            validation_results['index_name_correct'] = False
            validation_results['messages'].append(f"[{identifier}] Index name '{df.index.name}' does not match the expected name '{expected_index_name}'.")

    # Check for unwanted columns
    if disallow_columns is not None:
        for col in disallow_columns:
            if col in df.columns:
                validation_results['unwanted_columns_present'] = True
                validation_results['unwanted_columns'].append(col)
                validation_results['messages'].append(f"[{identifier}] Column '{col}' should not be present in the DataFrame.")

    # Print summary of validation results
    if validation_results['messages']:
        for message in validation_results['messages']:
            print(message)
    else:
        print(f"[{identifier}] DataFrame validation passed.")

    print_dataframe(df, identifier)
    return validation_results

def sum_card_types(df):
    """
    Adds a 'Sum' column to the DataFrame, summing specific card type columns.
    """
    columns_to_sum = [col for col in df.columns if col in GLOBAL_COLUMN_ORDER]
    df[columns_to_sum] = df[columns_to_sum].apply(pd.to_numeric, errors='coerce')
    sum_column = df[columns_to_sum].sum(axis=1)
    return pd.concat([df, sum_column.rename('Sum')], axis=1)

def get_combos_for_graph(graph, name):
    """
    Generates combo data for a graph.

    Args:
        graph (MyGraph): The graph object.
        name (str): The name of the item.

    Returns:
        dict: Combo data dictionary.
    """
    combo_data = {'name': name}
    for combo_name, (input_count, output_count) in graph.combo_data.items():
        value = input_count * output_count
        if output_count == 0:
            value = -input_count
        combo_data[combo_name] = value
    return combo_data

def print_dataframe(df, name):
    print(f'DataFrame: {name}')
    print(f'Shape: {df.shape}')
    print(df.index)    
    display(qgrid.show_grid(df, grid_options={'forceFitColumns': False}, column_definitions=gv.all_column_definitions))    


import os
def running_in_browser():
    in_vscode = "VSCODE_PID" in os.environ  # VS Code Detection
    in_jupyter = False

    try:
        from IPython import get_ipython
        if get_ipython():
            in_jupyter = True
    except ImportError:
        pass

    return in_jupyter and not in_vscode