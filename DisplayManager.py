import logging
import os
import pickle
import pandas as pd
from ipywidgets import widgets
from IPython.display import display
from GlobalVariables import global_vars as gv
import qgridnext as qgrid

# Initialize count_display widget
count_display = widgets.VBox(children=[])

def get_count_display_widget():
    """Provides access to the count_display widget."""
    return count_display

def update_display_data(update_collection=True, update_dataframe=True, central_df=None):
    """
    Updates the `display_data` dictionary with the latest metadata for Collection and DataFrame.
    Includes timestamps for DataFrame generation, collection, cached, and stored data.
    """
    username = os.getenv('SFF_USERNAME')

    # Initialize variables for metadata
    generated_df_timestamp = None
    cached_df_timestamp = None
    stored_df_timestamp = None
    stored_collection_timestamp = None

    # Retrieve database manager
    if gv.myDB:
        db_manager = gv.myDB
        username = db_manager.get_current_db_name()

        # Retrieve file record from GridFS
        file_record = db_manager.find_one('fs.files', {'filename': f"central_df_{username}"})
        if file_record and 'metadata' in file_record:
            metadata = file_record['metadata']
            stored_df_timestamp = metadata.get('DataFrame_Timestamp', None)
            stored_collection_timestamp = metadata.get('Collection_Timestamp', None)

    # Update Collection metadata
    if update_collection:
        update_collection_metadata(stored_collection_timestamp)

    # Update DataFrame metadata
    if update_dataframe:
        central_df = load_or_generate_dataframe(central_df, file_record, username)
        update_dataframe_metadata(central_df, stored_df_timestamp, cached_df_timestamp, username)


def update_collection_metadata(stored_collection_timestamp):
    """Updates metadata related to the collection."""
    if gv.myDB:
        deck_count = gv.myDB.count_documents('Deck', {})
        fusion_count = gv.myDB.count_documents('Fusion', {})
        gv.display_data['Collection'] = {
            'Timestamp': stored_collection_timestamp,
            'Decks': deck_count,
            'Fusions': fusion_count,
        }
    else:
        logging.warning("No database manager found. Collection data cannot be updated.")


def load_or_generate_dataframe(central_df, file_record, username):
    """Loads a DataFrame from cache or GridFS, or uses the provided DataFrame."""
    if central_df is not None:
        return central_df

    # Load from cache
    cached_data = gv.user_dataframes.get(username, {})
    cached_df = cached_data.get('data', None)
    if cached_df is not None:
        return cached_df

    # Load from GridFS
    if file_record and gv.fs:
        with gv.fs.get(file_record['_id']) as file:
            central_df = pickle.load(file)
            gv.user_dataframes[username] = {'data': central_df, 'metadata': file_record['metadata']}
            logging.info("Loaded DataFrame from GridFS.")
        return central_df

    logging.warning("No cached or stored DataFrame found. Returning None.")
    return None


def update_dataframe_metadata(central_df, stored_df_timestamp, cached_df_timestamp, username):
    """Updates the DataFrame metadata in `display_data`."""
    if central_df is not None:
        generated_df_timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        metadata = extract_dataframe_metadata(central_df, generated_df_timestamp)

        gv.display_data['DataFrame'] = {
            "Generated": metadata,
            "Cached": {
                'Timestamp': cached_df_timestamp,
                'Decks': gv.user_dataframes.get(username, {}).get('metadata', {}).get('Decks', ''),
                'Fusions': gv.user_dataframes.get(username, {}).get('metadata', {}).get('Fusions', ''),
            },
            "Stored": {
                'Timestamp': stored_df_timestamp,
                'Decks': gv.user_dataframes.get(username, {}).get('metadata', {}).get('Decks', ''),
                'Fusions': gv.user_dataframes.get(username, {}).get('metadata', {}).get('Fusions', ''),
            },
        }

        # Update the UI
        update_count_display()
        update_central_frame_tab(central_df)


def extract_dataframe_metadata(dataframe, timestamp=None):
    """Extracts metadata from a DataFrame."""
    if dataframe is not None:
        decks_count = len(dataframe[dataframe['type'] == 'Deck'])
        fusions_count = len(dataframe[dataframe['type'] == 'Fusion'])
    else:
        decks_count = 0
        fusions_count = 0

    return {
        'Timestamp': timestamp or "Not available",
        'Decks': decks_count,
        'Fusions': fusions_count,
    }

def update_count_display():
    """Updates the count display widget."""
    rows = []
    for info_type, value in sorted(gv.display_data.items()):
        if value:
            if info_type == "DataFrame":
                for sub_key, sub_value in sorted(value.items()):
                    row = {"Source": sub_key, "Info Type": info_type, **sub_value}
                    rows.append(row)
            else:
                row = {"Source": "Database", "Info Type": info_type, **value}
                rows.append(row)

    # Create or update the display DataFrame
    new_output = widgets.Output()
    if rows:
        df_display = pd.DataFrame(rows).fillna("")
        df_display.set_index(['Info Type', 'Source'], inplace=True)
        new_output.append_display_data(df_display)
    else:
        with new_output:
            print("No data to display.")

    count_display.children = [new_output]

def update_sheet_stats():
    """
    Updates the timestamp, title, and tags of the Google Sheet only when this function is called.
    This avoids frequent and unnecessary connections to Google Sheets.
    """
    #global display_data

    # Ensure the CMManager is already initialized in GlobalVariables
    if gv.cm_manager:
        # Get the current timestamp and title from the CMManager
        current_timestamp = gv.cm_manager.timestamp  # Direct access
        current_title = gv.cm_manager.title  # Direct access

        # Store the latest sheet information in display_data
        gv.display_data['CM Sheet'] = {
            'Title': current_title,
            'Timestamp': current_timestamp
        }

        # Call helper function to update the display
        update_count_display()

    else:
        print("CMManager not initialized.")

def update_central_frame_tab(central_df):
    """Updates the central DataFrame tab in the UI."""
    gv.central_frame_output.clear_output()
    with gv.central_frame_output:
        grid = qgrid.show_grid(central_df, grid_options={'forceFitColumns': False}, column_definitions=gv.all_column_definitions)
        grid.add_class(gv.rotate_suffix)
        display(grid)