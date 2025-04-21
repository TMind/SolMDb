import os
from datetime import datetime
from typing import OrderedDict
import pandas as pd
from qgridnext import QgridWidget

try:      import qgridnext as qgrid
except ImportError:    import qgrid
import ipywidgets as widgets
from GlobalVariables import global_vars as gv
from GlobalVariables import rotate_suffix, DEFAULT_FILTER

from DataSelectionManager import DataSelectionManager
from MongoDB.DatabaseManager import DatabaseManager
from SortingManager import SortingManager
from CustomGrids import ActionToolbar

from IPython.display import display, Javascript

# module global variables 

# Create an Output widget for opening browser sites 
out = widgets.Output()
display(out)

class GridManager:
    EVENT_DF_STATUS_CHANGED = 'df_status_changed'

    def __init__(self, debug_output):

        self.grids = {}
        self.callbacks = {}
        self.qgrid_callbacks = {}
        self.relationships = {}
        self.debug_output = debug_output
        self.css_manager = gv.css_manager
        self.sorting_manager = SortingManager(gv.rotated_column_definitions)
        self.custom_css_class = self.css_manager.create_and_inject_css('filter_grids', rotate_suffix)
        #self.grid_initializer = GridInitializer(self.sorting_manager, self.css_manager, gv.rotated_column_definitions, self.custom_css_class, debug_output)


    def add_grid(self, identifier, df, options=None, grid_type='qgrid'):
        """Add or update a grid to the GridManager."""
        if identifier in self.grids:
            grid = self.grids[identifier]
            self.set_default_data(identifier, df)
            
        else:
            grid = QGrid(identifier, df, options) if grid_type == 'qgrid' else print("Not QGrid Type!")
            if grid:
                self.grids[identifier] = grid        
                self._setup_grid_events(identifier, grid)            
                
        self.update_dataframe(identifier, df)
        #self.css_manager.apply_conditional_class(grid.main_widget, rotate_suffix, self.custom_css_class)

        return grid
        
    def get_grid_df_version(self, identifier, version='default'):
        grid = self.grids.get(identifier)
        if grid:
            version_passed = False
            for v in ['changed', 'filtered', 'default']:
                df = grid.df_versions.get(v)
                if v == version:
                    version_passed = True
                if version_passed and df is not None and not df.empty:
                    return df
        return None

    def get_grid_df(self, identifier):
        grid = self.grids.get(identifier)
        if grid:
           return grid.main_widget.get_changed_df()
        return pd.DataFrame()


    def replace_grid(self, identifier, new_df):
        #print(f"GridManager::replace_grid() - Replacing grid {identifier} with new DataFrame")
        grid = self.grids.get(identifier)
        if grid:
            grid.update_main_widget(new_df)
            return grid.get_grid_box()
    
    def reset_dataframe(self, identifier):
        grid = self.grids.get(identifier)
        if grid:
            #print(f"GridManager::reset_dataframe() - Resetting DataFrame for {identifier}")
            grid.reset_dataframe()

    def set_default_data(self, identifier, new_data):
        grid = self.grids.get(identifier)
        if grid:
            grid.df_versions['default'] = new_data.copy()
            grid.update_main_widget(new_data)
            grid.toggle_widget.df = pd.DataFrame([True] * len(new_data.columns), index=new_data.columns, columns=['Visible']).T
            grid.df_status['current'] = 'default'
            grid.df_status['last_set']['default'] = datetime.now()
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid.df_status)

    def get_default_data(self, identifier):
        grid = self.grids.get(identifier)
        if grid:
            return grid.df_versions['default']
        return pd.DataFrame()

    def update_dataframe(self, identifier, new_df):
        
        grid = self.grids.get(identifier)
        if grid:            
            #self.update_visible_columns(None, grid.main_widget)
            summed_df = grid.update_sum_column(new_df)
            grid.update_main_widget(summed_df)
            
            self.css_manager.apply_conditional_class(grid.main_widget, rotate_suffix, self.custom_css_class)     
            #print(f"GridManager::update_dataframe() - Updated DataFrame for {identifier}")                   
            #self.update_toggle_df(grid.main_widget.df,identifier)

    def update_toggle_df(self, df, identifier):
        grid = self.grids.get(identifier)
        if grid:
            old_toggle_df = grid.toggle_widget.get_changed_df()
            for column in old_toggle_df.columns:
                if column in df.columns:
                    if (column in df.columns) != old_toggle_df.loc['Visible', column]:
                        grid.toggle_widget.edit_cell('Visible', column, df.loc['Visible', column])
                else:
                    grid.toggle_widget.df[column] = False
                    if False != grid.toggle_widget.get_changed_df().loc['Visible', column]:
                        grid.toggle_widget.edit_cell('Visible', column, False)

    def update_visible_columns(self, event, widget):
        current_df = widget.get_changed_df()
        zero_width_columns = [col for col in current_df.columns if not current_df[col].ne(0).any()]
        if zero_width_columns:
            for grid_id, grid_info in self.grids.items():
                if grid_info.main_widget == widget:
                    widget.df = current_df.drop(columns=zero_width_columns, errors='ignore')
                    self.update_toggle_df(current_df, grid_id)

    def _setup_grid_events(self, identifier, grid):
        def on_toggle_change(event, qgrid_widget):
            toggled_df = grid.toggle_widget.get_changed_df()
            if 'Visible' in toggled_df.index:
                visible_columns = [col for col in toggled_df.columns if toggled_df.loc['Visible', col]]
            df_versions = grid.df_versions
            grid.main_widget.df = df_versions['filtered'][visible_columns].copy() if not df_versions['filtered'].empty else df_versions['default'][visible_columns].copy()
            grid.df_status['current'] = 'filtered'
            grid.df_status['last_set']['filtered'] = datetime.now()
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid.df_status)

        def on_filter_change(event, qgrid_widget):
            changed_df = grid.main_widget.get_changed_df()
            grid.df_versions['changed'] = changed_df.copy()
            self.update_visible_columns(event, grid.main_widget)
            self.update_toggle_df(changed_df, identifier)
            #self.synchronize_widgets(identifier)
            grid.df_status['current'] = 'changed'
            grid.df_status['last_set']['changed'] = datetime.now()
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid.df_status)

        ###grid.toggle_widget.on('cell_edited', on_toggle_change)
        ###if isinstance(grid, QGrid):
            ###grid.main_widget.on('filter_changed', on_filter_change)

        self.reapply_callbacks(identifier)

    def register_callback(self, event_name, callback, identifier=None):
        if identifier is None:
            for grid_id in self.grids:
                self._register_callback_for_identifier(grid_id, event_name, callback)
        else:
            self._register_callback_for_identifier(identifier, event_name, callback)

    def _register_callback_for_identifier(self, identifier, event_name, callback):
        self.callbacks.setdefault(identifier, {}).setdefault(event_name, []).append(callback)

    def on(self, identifier, event_name, callback):
        grid = self.grids.get(identifier)
        if grid:
            # Check if Callback is already registered
            if callback not in self.qgrid_callbacks.get(identifier, {}).get(event_name, []):
                grid.main_widget.on(event_name, callback)
                self.qgrid_callbacks.setdefault(identifier, {}).setdefault(event_name, []).append(callback)

    def reapply_callbacks(self, identifier):
        grid = self.grids.get(identifier)
        if grid:
            if identifier in self.callbacks:
                for event_name, callbacks in self.callbacks[identifier].items():
                    for callback in callbacks:
                        grid.main_widget.on(event_name, callback)

            if identifier in self.qgrid_callbacks:
                for event_name, callbacks in self.qgrid_callbacks[identifier].items():
                    for callback in callbacks:
                        grid.main_widget.on(event_name, callback)

    def display_registered_events(self):
        with self.debug_output:
            print("Registered GridManager events:")
            for identifier, events in self.callbacks.items():
                for event_name, callbacks in events.items():                
                    print(f"Identifier: {identifier}, Event: {event_name}, Callbacks: {len(callbacks)}")
            
            print("\nRegistered QGrid events:")
            for identifier, events in self.qgrid_callbacks.items():
                for event_name, callbacks in events.items():
                    print(f"Identifier: {identifier}, Event: {event_name}, Callbacks: {len(callbacks)}")

    def trigger(self, event_name, *args, **kwargs):
        for identifier in self.callbacks:
            for callback in self.callbacks[identifier].get(event_name, []):
                callback(*args, **kwargs)

class BaseGrid:
    def __init__(self, identifier, df, options=None):
        #print(f"BaseGrid::__init__() - Creating BaseGrid with identifier {identifier} -> options = {options}")
        self.identifier = identifier
        self.df_versions = {
            'default': df.copy(),
            'filtered': pd.DataFrame(),
            'changed': pd.DataFrame()
        }
        self.df_status = {
            'current': 'default',
            'last_set': {
                'default': datetime.now(),
                'filtered': None,
                'changed': None
            }
        }
        #print(f"BaseGrid::__init__() - options = {options}")
        self.qgrid_options = options if options else {}
        self.main_widget = None
        #self.toolbar_widget = self.create_toolbar()
        self.toggle_widget = widgets.VBox([])  #self.create_toggle_widget(df)        
        self.create_main_widget(df)
        
         # Create a VBox to hold the toolbar, toggle widget, and main grid widget
        self.grid_layout = widgets.VBox([self.toggle_widget, self.main_widget])

    def create_main_widget(self, df):
        raise NotImplementedError("Subclasses should implement this method.")

    def create_toggle_widget(self, df):
        toggle_df = pd.DataFrame([True] * len(df.columns), index=df.columns, columns=['Visible']).T
        toggle_grid = qgrid.show_grid(toggle_df, show_toolbar=False, grid_options={'forceFitColumns': False, 'filterable': False, 'sortable': False})
        toggle_grid.layout = widgets.Layout(height='65px')
        return toggle_grid

    def get_grid_box(self):
        #return widgets.VBox([self.toggle_widget, self.main_widget])
        return self.grid_layout

    def update_main_widget(self, new_df):
        raise NotImplementedError("Subclasses should implement this method.")

    def update_sum_column(self, df):
        if gv.rotated_column_definitions:
            # Get the list of columns to sum, ensuring they exist in the DataFrame
            columns_to_sum = [col for col in gv.rotated_column_definitions.keys() if col in df.columns]
            if columns_to_sum:
                # Ensure the columns to sum are numeric; replace non-numeric with NaN
                numeric_df = df[columns_to_sum].apply(pd.to_numeric, errors='coerce')

                # Calculate the sum for each row across the rotated columns
                df['Sum'] = numeric_df.sum(axis=1)

                # Fill NaN values in the numeric 'Sum' column with 0 without using inplace
                df['Sum'] = df['Sum'].fillna(0)

                # If you need to fill NaN values in other columns, consider their data type:
                for col in df.columns:
                    if df[col].dtype == 'object':  # If the column is non-numeric
                        df[col] = df[col].fillna('')

                # Reorder columns based on GLOBAL_COLUMN_ORDER
                ordered_columns = [col for col in utils.GLOBAL_COLUMN_ORDER if col in df.columns]
                df = df[ordered_columns + [col for col in df.columns if col not in ordered_columns]]

        return df
        

    def set_dataframe_version(self, version, df):
        self.df_versions[version] = df
        self.df_status['current'] = 'filtered'
        self.df_status['last_set']['filtered'] = datetime.now()

    def reset_dataframe(self):
        self.df_versions['default'] = pd.DataFrame()
        self.update_main_widget(self.df_versions['default'])

from FilterManager import FilterManager
class QGrid(BaseGrid):
    
    def __init__(self, identifier, df, options=None):
        """
        Initialize the QGrid and attach a FilterManager.
        """
        super().__init__(identifier, df, options)
        self.filter_manager = FilterManager(self.main_widget)  # Attach a FilterManager
    
    def create_main_widget(self, df):
        """
        Create the main QGrid widget.
        """
        default_grid_options = {
            'forceFitColumns': False,
            'enableColumnReorder': True,
            'minVisibleRows': 10,
        }

        # Get user-provided grid options and update the defaults
        user_grid_options = self.qgrid_options.get('grid_options', {})
        default_grid_options.update(user_grid_options)

        # Create the QGrid widget
        self.main_widget = qgrid.show_grid(
            df,
            column_options=self.qgrid_options.get('column_options', {}),
            column_definitions=self.qgrid_options.get('column_definitions', {}),
            grid_options=default_grid_options,
            show_toolbar=False
        )
        
    def reset_sorting(self):
        """Resets sorting in QGrid to avoid missing column errors when columns change."""
        if hasattr(self.main_widget, "_sort_helper_columns"):
            self.main_widget._sort_helper_columns = {}  # Clear sorting settings
        self.main_widget._update_table(triggered_by="reset_sorting")  # Force update
        
    def update_main_widget(self, new_df):           
        print(f"Updating QGrid with new DataFrame: {new_df.shape}")

        if new_df.empty:
            print("Warning: new_df is empty. No data will be displayed!")

        # Ensure sorting columns match the new DataFrame
        if hasattr(self.main_widget, "_sort_helper_columns"):
            sort_columns = self.main_widget._sort_helper_columns
            missing_columns = [col for col in sort_columns.values() if col not in new_df.columns]

            if missing_columns:
                print(f"Resetting sorting because missing columns: {missing_columns}")
                self.reset_sorting()

        # Now update the DataFrame
        self.main_widget.df = new_df


        # sort_columns = getattr(self.main_widget, "_sort_helper_columns", {})
        # valid_sort_columns = {
        #     col: sort_col for col, sort_col in sort_columns.items()
        #     if sort_col in new_df.columns
        # }

        # if len(valid_sort_columns) < len(sort_columns):
        #     print(f"Skipping missing sort columns: {set(sort_columns) - set(valid_sort_columns)}")
        #     self.main_widget._sort_helper_columns = valid_sort_columns  

        # # ✅ Store current filters before clearing
        # stored_filters = self.filter_manager.get_active_filters().copy()

        # # ✅ Clear UI filters (but keep stored filters)
        # print("Temporarily disabling filters to check if data is displayed.")
        # self.filter_manager.clear_filters(clear_memory=False)

        # self.main_widget.df = new_df  
        # print(f"Updated grid with {len(new_df)} rows and {len(new_df.columns)} columns.")

        # # ✅ Ensure stored filters are valid before restoring
        # if stored_filters:
        #     print("Reapplying filters now...")
        #     self.filter_manager.set_active_filters(stored_filters)

        # self.main_widget._update_table(triggered_by="manual_update")

class PandasGrid(BaseGrid):
    def create_main_widget(self, df):
        self.update_main_widget(df)

    def update_main_widget(self, new_df):
        self.df_versions['default'] = new_df.copy()
        self.set_dataframe_version('filtered', new_df)


import utils  
import re

def apply_filter_to_dataframe(df_to_filter, filter_df):
    def filter_by_substring(df, filter_row):
        def apply_filter(df, filter_step):
            # Extract information from filter step
            first_target = filter_step.get('first_target', [''])
            second_target = filter_step.get('second_target', [''])
            first_operator = filter_step.get('first_operator', 'OR')
            second_operator = filter_step.get('second_operator', 'OR')

            if first_target == [''] or second_target == ['']:
                return df

            # Initialize the mask based on the first operator
            mask = pd.Series([first_operator == 'AND'] * len(df), index=df.index)

            # Iterate over the first target (either fields or substrings)
            for first_item in first_target:
                item_mask = pd.Series([second_operator == 'AND'] * len(df), index=df.index)

                # Check if the field is in the DataFrame (if applicable)
                if filter_step['first_target_type'] == 'field' and first_item not in df.columns:
                    logging.warning(f"Field '{first_item}' not found in DataFrame")
                    logging.warning(f"DF Columns: {df.columns}")
                    continue

                # Iterate over the second target (either substrings or fields)
                for second_item in second_target:
                    if filter_step['first_target_type'] == 'field':
                        # First target is field, second is substring
                        string_item = second_item
                        field_item = first_item
                    else:
                        # First target is substring, second is field
                        string_item = first_item
                        field_item = second_item

                    string_item = re.sub(r',\s*', ' ', string_item)
                    regex = fr"(^|\W){re.escape(string_item)}($|\W)"
                    
                    # Apply the regex to the entire column using .apply() and combine based on the second operator
                    substring_mask = df[field_item].apply(lambda title: bool(re.search(regex, str(title), re.IGNORECASE)))

                    # Debugging information for each match
                    matched_indices = df[field_item][substring_mask].index.tolist()
                    #print(f"Substring '{string_item}' matched indices: {matched_indices} in field '{field_item}'")


                    # Combine the substring mask with the item mask based on the second operator
                    if second_operator == 'AND':
                        item_mask &= substring_mask
                    else:  # OR logic
                        item_mask |= substring_mask

                # Debugging information after applying item mask
                matched_indices_after_item = df[item_mask].index.tolist()
                #print(f"Item mask after combining substrings: {matched_indices_after_item} for first_item '{first_item}'")

                # Combine the item mask with the main mask based on the first operator
                if first_operator == 'AND':
                    mask &= item_mask
                else:  # OR logic
                    mask |= item_mask

            # Debugging information after applying the main mask
            matched_indices_after_main = df[mask].index.tolist()
            #print(f"Main mask after combining items: {matched_indices_after_main}")

            matched_count = mask.sum()
            logging.info(f"apply_filter: {matched_count} rows matched for first_target '{first_target}' and second_target '{second_target}' with first_operator '{first_operator}' and second_operator '{second_operator}'")
            return df[mask]

        def determine_filter_config(column, filter_row, string):
            # Determine operator and split substrings
            and_symbols = {':': r'\s*:\s*', '&': r'\s*&\s*', '+': r'\s*\+\s*'}
            or_symbols = {'|': r'\s*\|\s*', '-': r'\s*-\s*'}

            substring_operator = 'OR'
            substrings = re.split(r'\s*;\s*', string)
            for symbol, pattern in and_symbols.items():
                if symbol in string:
                    substring_operator = 'AND'
                    substrings = re.split(pattern, string)
                    break
            else:
                for symbol, pattern in or_symbols.items():
                    if symbol in string:
                        substring_operator = 'OR'
                        substrings = re.split(pattern, string)
                        break

            # Determine fields to filter on and field operator
            # Standard case (default) 
            first_operator = 'OR'
            second_operator = substring_operator
            first_target = ['CardTitles']
            second_target = substrings
            first_target_type = 'field'
            
            
            if column == 'Name':
                second_target = substrings
                if filter_row['Type'] == 'Fusion':
                    first_target = ['Deck A', 'Deck B']
                    first_operator = substring_operator
                    second_operator = 'OR'
                else:
                    first_target = ['Name']
            elif column == 'Forgeborn Ability':
                second_target = ['FB2', 'FB3', 'FB4']
                second_operator = 'OR'
                first_operator = substring_operator
                first_target = substrings
                first_target_type = 'substring'

            # Return the filter configuration
            return {
                'first_target': first_target,
                'second_target': second_target,
                'first_operator': first_operator,
                'second_operator': second_operator,
                'first_target_type': first_target_type 
            }

        # Beginning of the filter_by_substring function
        df_filtered = df

        # Apply Type filter first (always mandatory)
        if 'Type' in filter_row and isinstance(filter_row['Type'], str) and filter_row['Type']:
            type_substrings = filter_row['Type'].split(',')
            filter_step = {
                'first_target': ['type'],
                'second_target': type_substrings,
                'first_operator': 'OR',
                'second_operator': 'OR',
                'first_target_type': 'field'
            }
            df_filtered = apply_filter(df_filtered, filter_step)

        # Apply mandatory fields with mandatory_operator logic
        mandatory_fields = filter_row.get('Mandatory Fields', '')
        if isinstance(mandatory_fields, str):
            mandatory_fields = mandatory_fields.split(', ')
        else:
            mandatory_fields = []
        mandatory_fields = [column.strip() for column in mandatory_fields]

        # Apply mandatory fields (all must match)
        for column in mandatory_fields:
            filter_step = determine_filter_config(column, filter_row, filter_row[column])            
            df_filtered = apply_filter(df_filtered, filter_step) 
 
        # Apply optional fields (at least one must match)
        optional_results = []
        for column in filter_row.index:
            if column not in mandatory_fields and column not in ['Type', 'Mandatory Fields', 'Active', 'ID'] and isinstance(filter_row[column], str) and filter_row[column]:
                filter_step = determine_filter_config(column, filter_row, filter_row[column]) 
                current_filter_results = apply_filter(df_filtered, filter_step)
                optional_results.append(current_filter_results)  # Duplicates will be removed later 
                

        # Combine all optional results with OR logic
        if optional_results:
            combined_optional_results = pd.concat(optional_results).drop_duplicates()
            df_filtered = df_filtered[df_filtered.index.isin(combined_optional_results.index)]

        return df_filtered

    # Beginning of the apply_cardname_filter_to_dataframe function

    df_filtered = df_to_filter
    active_filters = filter_df[filter_df['Active'] == True]  # Get only the active filters

    for _, filter_row in active_filters.iterrows():
        df_filtered = filter_by_substring(df_filtered, filter_row)

    return df_filtered

def convert_to_dataframe(records, index_field='Name', columns=None):
    """
    Converts a list of database records into a pandas DataFrame.

    Args:
        records (list): List of dictionaries representing the database records.
        index_field (str): The field to set as the index of the DataFrame. Defaults to 'name'.
        columns (list): List of columns to include in the DataFrame. Defaults to None (include all columns).

    Returns:
        pd.DataFrame: A DataFrame containing the records.
    """
    if not records:
        print("No records found to convert into a DataFrame.")
        return pd.DataFrame()  # Return an empty DataFrame if no records

    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(records)
    
    # Filter the DataFrame to include only the specified columns
    if columns:
        df = df[columns]
        print(f"Filtered DataFrame to include columns: {columns}")

    # Set the specified field as the index if it exists
    if index_field in df.columns:
        df.set_index(index_field, inplace=True)
        print(f"Set '{index_field}' as the index of the DataFrame.")
    else:
        print(f"Index field '{index_field}' not found in the records. Using default numeric index.")

    # Return the resulting DataFrame
    return df

# Function to create a styled HTML widget with a background color
def create_styled_html(text, text_color, bg_color, border_color):
    html = widgets.HTML(
        value=f"<div style='padding:10px; color:{text_color}; background-color:{bg_color};"
            f" border:solid 2px {border_color}; border-radius:5px;'>"
            f"<strong>{text}</strong></div>"
    )
    return html

deck_filter_bar = create_styled_html(
    "Filter Selection: Set custom filters to your deck base.",
    text_color='white', bg_color='#2E86AB', border_color='#205E86'  # Darker blue for contrast
)

filter_grid_bar = create_styled_html(
    "Filter Grid: Apply your custom filter to the deck base.",
    text_color='white', bg_color='#FFA630', border_color='#CC7A00'  # A darker orange to complement the background
)

filter_results_bar = create_styled_html(
    "Filter Results: Displays the results of the filters applied to the deck base.",
    text_color='#2E2E2E', bg_color='#CFF27E', border_color='#B2D38A'  # A more muted green to blend with the background
)

deck_content_bar = create_styled_html(
    "Deck / Fusion Content: Displays the last selected item",
    text_color='white', bg_color='#AA4465', border_color='#4A4A4A'  
)


import webbrowser
import logging
import numpy as np
from functools import partial
from GraphVis import display_graph
from datetime import datetime

import FieldUnifier
from DataFrameGenerator import DataFrameGenerator
from DBQueryHelper import fetch_filtered_documents
from DataSelectionManager import Observable
from FilterGrid import FilterGrid
from MyWidgets import VBoxManager

from LogLevel import register_logger  # Import the registration function

# Create a logger for this module. Using __name__ helps give it a unique identifier.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the level as desired

# Register this logger in the central registry.
register_logger(__name__, logger)

# Prevent logs from propagating to the root logger (which is set at WARNING)
logger.propagate = False

# Only add a handler if this logger does not already have one.
if not logger.handlers:
    #handler = logging.StreamHandler()
    handler = logging.FileHandler("app_gridmanager.log")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class DynamicGridManager:

    def __init__(self, qg_options, out_debug):
        self.out_debug = out_debug       
        self.qg_options = qg_options
        self.qm = GridManager(out_debug)
        self.DataFrameGenerator = DataFrameGenerator()
        
        self.filterGridObject = FilterGrid(self.refresh_gridbox)
        self.deck_content_Grid = self.create_deck_content_Grid()
        self.sorting_info = {}
        self.css_manager = gv.css_manager
        self.custom_css_class = self.css_manager.create_and_inject_css('deck_content', rotate_suffix)        
        
        # Central grid filter widget info 
        self.grid_widget_states = {}
        
        self.refresh_needed = False  # Flag to indicate whether refresh is needed
    
        # Toolbar         
        """
        Creates an ActionToolbar instance and assigns callbacks specific to the grid_id.
        """
        button_configs = {
            "Password": {"type": "text", "description": "Password", "value": ""},
            "Authenticate": {"type": "button", "description": "Login", "button_style": 'info'},
            "Generate": {"type": "button", "description": "Generate Table", "button_style": "success"},
            "Fuse": {"type": "button", "description": "Fuse Filtered", "button_style": "warning"},
        }
        action_toolbar = ActionToolbar(widget_configs=button_configs)
    
        password_widget = action_toolbar.get_widget('Password')
        # Define the authentication callback
        def authenticate_callback(button):
            password = password_widget.value  # Get the value of the Password widget
            self.authenticate(password)  # Pass the password to the authenticate method
    
        # Assign callbacks using partial to bind grid_id
        action_toolbar.assign_callback('Generate', self.handle_database_change, refresh_needed=True)
        action_toolbar.assign_callback('Authenticate', authenticate_callback)
        action_toolbar.assign_callback('Fuse', self.fuse_filtered)
    
        # GridBox 
        self.VBoxGrids = VBoxManager()
        
        # UI elements
        self.selectionGrid, self.filterGrid = self.filterGridObject.get_widgets()
        
        # Initialize the widget dictionary and wrap each group in a VBox
        self.ui_widget_dict = OrderedDict({      
            'Toolbar'   : widgets.VBox([action_toolbar.toolbar]),
            'Selection' : widgets.VBox([deck_filter_bar, self.selectionGrid]),
            'Filter' : widgets.VBox([filter_grid_bar, self.filterGrid]),
            'Grid' : widgets.VBox([filter_results_bar, self.VBoxGrids.get_main_vbox()]),
            'Content' : widgets.VBox([deck_content_bar, self.deck_content_Grid.main_widget])
        }) 
            
        self.ui = widgets.VBox([])      

    def set_refresh_needed(self, needed):
        """
        Set the flag indicating whether a refresh is needed.
        """
        self.refresh_needed = needed
        logging.info(f"Refresh needed set to {needed}")
    
    # Helper functions to manage the grid widget states
    def update_filter_state(self, grid_identifier, new_filter):
        # Update the central filter criteria for the given grid_identifier.
        self.grid_widget_states[grid_identifier]['filter_row'] = new_filter
        # Notify all observers (grids) about the update.
        self.filter_observable.notify_observers(grid_identifier, new_filter)

    def register_grid_as_observer(self, grid_identifier, callback):
        # Each grid provides a callback to update its UI when the filter changes.
        self.filter_observable.add_observer(callback)
        
    def apply_filters(self, widget_states):
        
        # Filter columns based on the filter_row
        info_level = widget_states['info_level']
        data_set = widget_states['data_set']
        filter_row = widget_states['filter_row']
        data_type = filter_row['Type']
        match_titles = True
        filtered_dict = fetch_filtered_documents(data_type,  filter_df=pd.DataFrame([filter_row]), final_format='DF', expanded_field='FrameData', match_titles=match_titles)
        if match_titles and 'documents' in filtered_dict:
            filtered_list = filtered_dict['documents']
        else:
            filtered_list = filtered_dict
        filtered_df = convert_to_dataframe(filtered_list)
        data_set_columms = FieldUnifier.generate_final_fields(info_level, data_set, data_type, rename_fields_to='df')
        #filtered_df = self.DataFrameGenerator.generate_statistics_dataframe(filtered_df, data_set_columms, data_type)

        return self.filter_by_columns(filtered_df, data_set_columms)
        
    def filter_by_columns(self, df, columns):
        if df.index.name:  # Check if there's a named index
            df.reset_index(inplace=True)  # Move index back to columns
        existing_columns = [col for col in columns if col in df.columns]
        filtered_df = df.loc[:, existing_columns]    
        
        #filtered_df.sort_index(axis=1, inplace=True)
        #filtered_df = utils.sum_card_types(filtered_df)
        filtered_df = utils.clean_columns(filtered_df)
        filtered_df = utils.enforce_column_order(filtered_df, utils.GLOBAL_COLUMN_ORDER)
    
        return filtered_df

    def check_combo_data_existence(self, collection_name, filter_criteria={}, df=None):
        """
        Checks if `graph.combo_data` and `FrameData` exist in the given MongoDB collection and DataFrame.

        Args:
            collection_name (str): The name of the database collection.
            filter_criteria (dict, optional): Query to filter the collection. Default is {} (no filter).
            df (pd.DataFrame, optional): A DataFrame to check for 'FrameData' existence.

        Returns:
            dict: A dictionary containing:
                - "combo_data": True if `graph.combo_data` exists and is not empty in the database, False otherwise.
                - "frame_data_db": True if `FrameData` exists in the database, False otherwise.
                - "frame_data_df": True if `FrameData` exists in the provided DataFrame, False otherwise.
                - "status": Overall status (True only if all required fields exist and are non-empty).
        """
        status = {
            "combo_data": False,
            "frame_data_db": False,
            "frame_data_df": False,
            "status": False  # Overall status
        }

        # Step 1: Check MongoDB for `graph.combo_data` and `FrameData`
        db_record = gv.myDB.find_one(collection_name, filter_criteria, projection={"graph.combo_data": 1, "FrameData": 1})

        # Check if `combo_data` exists and has elements
        if db_record and "graph" in db_record and "combo_data" in db_record["graph"] and db_record["graph"]["combo_data"]:
            status["combo_data"] = True

        # Check if `FrameData` exists in the database
        if db_record and "FrameData" in db_record:
            status["frame_data_db"] = True

        # Step 2: Check if `FrameData` exists in the provided DataFrame
        if df is not None and "FrameData" in df.columns:
            status["frame_data_df"] = True

        # Set the overall status to True only if both `combo_data` and `FrameData` exist
        status["status"] = status["combo_data"] and (status["frame_data_db"] or status["frame_data_df"])

        return status


    def handle_database_change(self, event, refresh_needed=False):
        """
        Handles updates required when the database changes, ensuring updates are only performed if flagged.
        """
        #if refresh_needed:   self.set_refresh_needed(True)
        
        #if not self.refresh_needed:
        #    logging.info("No refresh needed. Skipping database change handling.")
        #    return

        logging.info("Handling database change in DynamicGridManager.")

        # Step 1: Update the collection DataFrame
        # try:
        #     collection_df = self.DataFrameGenerator.manage_central_dataframe()
        #     #self.data_generate_functions['central_dataframe']()
        #     self.qm.add_grid('collection', collection_df, options=self.qg_options)
        #     logging.info(f"Collection DataFrame updated with {len(collection_df)} rows.")
        # except Exception as e:
        #     logging.error(f"Failed to update collection DataFrame: {e}")
        #     return

        self.filterGridObject.update_selection_content(event)

        # Step 2: Reset FilterGrid to default state        
        self.filterGridObject.qgrid_filter.df = DEFAULT_FILTER
        logging.info("FilterGrid reset to default state.")
        

        # Step 3: Rebuild active filters and refresh grids
        try:
            filter_df = self.filterGridObject.get_changed_df()
            active_filters_df = filter_df[filter_df['Active']]

            # Reset grid boxes
            self.VBoxGrids.reset()
            logging.info("Grid boxes reset.")

            # Refresh grids for active filters
            for row_index, filter_row in active_filters_df.iterrows():
                grid_identifier = f"filtered_grid_{row_index}"
                self.update_or_refresh_grid(grid_identifier, filter_row=filter_row)
            logging.info("Grids refreshed for active filters.")
        except Exception as e:
            logging.error(f"Error while refreshing grids: {e}")

        # Clear the refresh flag
        self.refresh_needed = False
        logging.info("Database change handling complete.")


    def refresh_gridbox(self, event=None, widget=None):
        """
        Refreshes the grid layout based on active filters and triggers updates for individual grids.

        Args:
            change (dict or None): The widget interaction event data.
        """
        try:
            logging.info(f"Refreshing gridbox in DynamicGridManager: event = {event}")
            # Retrieve or generate the collection DataFrame
            #collection_df = self._get_collection_dataframe(event)

            # Get active and inactive filter rows
            if widget: # If a widget is provided, use its filter row
                filter_df = widget.get_changed_df()
            else:
                filter_df = self.filterGridObject.get_changed_df()
            
            logging.info(f"DataFrame columns: {filter_df.columns}")
            logging.info(f"DataFrame index: {filter_df.index}")
            
            #print("DataFrame before filtering:")
            #print(filter_df)
            #print("Data types:")
            #print(filter_df.dtypes)

            #print("Unique values in 'Active' column:", filter_df["Active"].unique())
            
            #active_filters_df = filter_df[filter_df['Active']]
            #inactive_filters_df = filter_df[~filter_df['Active']]
            
            if 'Active' in filter_df.columns:
                #print("🚀 Before conversion:")  
                #print(filter_df[['Active']].to_string(index=False))  # Show 'Active' column before changes
                
                # Ensure boolean conversion works properly
                if filter_df['Active'].dtype == object:
                    filter_df['Active'] = filter_df['Active'].map(lambda x: str(x).strip().lower() == "true")

                # Fill missing values with False
                filter_df['Active'] = filter_df['Active'].fillna(False).astype(bool)

                #print("\n✅ After conversion:")  
                #print(filter_df[['Active']].to_string(index=False))  # Show 'Active' column after changes
                
                # Apply filtering
                active_filters_df = filter_df[filter_df['Active']]
                inactive_filters_df = filter_df[~filter_df['Active']]

                #print("\n🔥 Active filters:")
                #print(active_filters_df.to_string(index=False))  # Print active rows
            else:
                #print("⚠️ 'Active' column is missing!")
                active_filters_df = pd.DataFrame(columns=filter_df.columns)
                inactive_filters_df = pd.DataFrame(columns=filter_df.columns)

            # Handle case when no active or inactive filters are present
            if active_filters_df.empty and inactive_filters_df.empty:
                self.VBoxGrids.reset()
                logger.info("All grids reset; no active or inactive filters present.")
                return

            # Handle specific grid updates if event is provided
            if event:
                name = event.get('name', '')
                if name == 'row_added' or name == 'cell_edited': 
                    parameter_index = 'index'
                elif name == 'row_removed':
                    parameter_index = 'indices'
                else:
                    raise ValueError(f"Unexpected event name: {name}")
                
                specific_index = event.get(parameter_index)
                logger.info(f"Handling row-specific update from filter: {specific_index} with event: {name}")
                    
                if name == 'cell_edited' :
                    column = event['column']
                    if column == 'Active':
                        # Handle activation/deactivation of a filter row
                        if event['new'] is False:  # Row was deactivated
                            print(f"Deactivating grid with index '{specific_index}'.")
                            self.VBoxGrids.remove_widget(specific_index)
                            return
                        elif event['new'] is True:  # Row was activated
                            print(f"Reactivating grid with index '{specific_index}'.")
                            filter_row = filter_df.loc[specific_index]
                            grid_identifier = f"filtered_grid_{specific_index}"
                            self.update_or_refresh_grid(grid_identifier, filter_row)
                            return    
                
                # Handle case where specific_index is a DataFrame
                if isinstance(specific_index, pd.DataFrame):
                    logger.info("Specific index is a DataFrame. Extracting indices.")
                    specific_index = specific_index.index.tolist()

                # Check for empty or malformed selections
                if isinstance(specific_index, (list, pd.DataFrame)) and specific_index is None:
                    logger.info("Received empty selection; no grids to update.")
                    return

                self._handle_specific_update(specific_index, active_filters_df, inactive_filters_df)
                return
    

            # Default: Refresh all active grids and remove inactive grids
            logger.info("No specific change provided; refreshing all active grids and removing inactive grids.")
            self._refresh_all_grids(active_filters_df)
            self._remove_inactive_grids(inactive_filters_df)

            logger.info("Gridbox refresh completed.")

        except Exception as e:
            logger.error(f"Exception occurred in refresh_gridbox: {e}")

    # Additional helper function to remove inactive grids
    def _remove_inactive_grids(self, inactive_filters_df):
        """
        Removes widgets corresponding to inactive filter rows.

        Args:
            inactive_filters_df (DataFrame): DataFrame containing inactive filter rows.
        """
        try:
            if inactive_filters_df.empty:
                logger.info("No inactive grids to remove.")
                return

            for row_index in inactive_filters_df.index:
                logger.info(f"Removing widget for inactive grid at index {row_index}.")
                self.VBoxGrids.remove_widget(row_index)

        except Exception as e:
            logger.error(f"Error removing inactive grids: {e}")

    def _handle_specific_update(self, specific_index, active_filters_df, inactive_filters_df):
        """
        Handles updates for specific indices based on the change object.

        Args:
            specific_index (int, list, or unexpected type): Index or indices to update.
            active_filters_df (DataFrame): Active filter rows.
            inactive_filters_df (DataFrame): Inactive filter rows.
        """
        if isinstance(specific_index, (int, np.integer)):  # Single index
            self._process_single_index(specific_index, active_filters_df, inactive_filters_df)

        elif isinstance(specific_index, list):  # Multiple indices
            for grid_index in specific_index:
                self._process_single_index(grid_index, active_filters_df, inactive_filters_df)

        elif isinstance(specific_index, pd.DataFrame):  # Unexpected DataFrame case
            logger.warning(f"Received DataFrame instead of index: {specific_index}. Attempting to resolve.")
            # Attempt to resolve, e.g., by using the DataFrame's index or resetting the gridbox
            resolved_index = specific_index.index.tolist() if not specific_index.empty else None
            if resolved_index:
                self._handle_specific_update(resolved_index, active_filters_df, inactive_filters_df)
            else:
                logger.error("Cannot process DataFrame; no valid indices found.")
        
        else:  # Other unexpected types
            logger.warning(f"Invalid type for specific_index: {type(specific_index)}. Contents: {specific_index}")

    def _process_single_index(self, grid_index, active_filters_df, inactive_filters_df):
        """
        Process a single grid index for updating or removal.

        Args:
            grid_index (int): Index of the grid to process.
            active_filters_df (DataFrame): Active filter rows.
            inactive_filters_df (DataFrame): Inactive filter rows.            
        """
        if grid_index in active_filters_df.index:
            filter_row = active_filters_df.loc[grid_index]
            grid_identifier = f"filtered_grid_{grid_index}"
            self.update_or_refresh_grid(grid_identifier, filter_row)

        elif grid_index in inactive_filters_df.index:
            self.VBoxGrids.remove_widget(grid_index)
            logger.info(f"Removed inactive grid with index '{grid_index}'.")

        else:
            self.VBoxGrids.remove_widget(grid_index)
            logger.info(f"Removed grid with index '{grid_index}'.")
            #logger.warning(f"Grid index {grid_index} not found in any filter indices.")

    def _refresh_all_grids(self, active_filters_df):
        """
        Refreshes all active grids.

        Args:
            active_filters_df (DataFrame): Active filter rows.            
        """
        for row_index, filter_row in active_filters_df.iterrows():
            grid_identifier = f"filtered_grid_{row_index}"
            self.update_or_refresh_grid(grid_identifier, filter_row)

    def construct_grid_ui(self, grid_identifier, filter_row, grid):
        """
        Constructs the UI components for a specific grid.

        Args:
            grid_identifier (str): Identifier of the grid.
            filter_row (pd.Series): Filter row data.
            grid (object): Grid object to display.

        Returns:
            widgets.VBox: The constructed VBox containing the toolbar, filter row, and grid.
        """
        toolbar_widget = self.create_toolbar(grid_identifier)
        
        # Create a single-row DataFrame and set a custom index label
        filter_row_widget = qgrid.show_grid(
            pd.DataFrame([filter_row]), 
            show_toolbar=False,
            grid_options={'forceFitColumns': True, 'filterable': False, 'sortable': False, 'editable': True}
        )
        filter_row_widget.layout = widgets.Layout(height='70px')
               
        # Debug: Print the current DataFrame and its index before updating.
        logging.debug("Before assignment:")
        logging.debug("DataFrame:\n", filter_row_widget.df)
        logging.debug("Index:", filter_row_widget.df.index.tolist())
        
        # Capture the new grid's unique id.
        new_grid_id = id(filter_row_widget)
        logging.debug(f"Computed new_grid_id: {new_grid_id}")
        
        # Use the custom index (extracted from grid_identifier) to update the 'ID' column.
        row_index = int(grid_identifier.split('_')[-1])
        
        # Make a copy of the DataFrame and update the 'ID' column.
        df_copy = filter_row_widget.df.copy()
        if 'ID' not in df_copy.columns:
            df_copy['ID'] = ""  # Create the column if it doesn't exist.
        df_copy.at[row_index, 'ID'] = new_grid_id

        # Debug: Print the DataFrame after assignment.
        logging.debug("After assignment:")
        logging.debug("DataFrame:\n", df_copy)
        logging.debug("Index:", df_copy.index.tolist())
        
        # Set the updated DataFrame back into the widget.
        filter_row_widget.df = df_copy
        self.filterGridObject.update_filter_row_id(row_index, new_grid_id)
                
        result_detail_widget = self.create_summary_widget(grid.main_widget.get_changed_df(), filter_row)

        def make_on_filter_row_change(qgrid_widget):
            def on_filter_row_change(event, qg_widget = qgrid_widget):
                logger.debug(f"Event received: {event}")
                if event['new'] != event['old']:
                    try:
                        # Log detailed debugging info
                        logger.debug(f"Attempting to update row {event['index']} column {event['column']}")
                        logger.debug(f"DataFrame index before update: {qg_widget.df.index.tolist()}")
                        logger.debug(f"DataFrame columns: {qg_widget.df.columns.tolist()}")
                        
                        # Confirm the row exists
                        if event['index'] not in qg_widget.df.index:
                            logger.error(f"Row index {event['index']} not found. DataFrame index: {qg_widget.df.index.tolist()}")
                            return
                        
                        # Print the row before updating
                        logger.debug("Row before update: %s", qg_widget.df.loc[event['index']])
                        
                        # Use the event's index directly
                        qg_widget.df.at[event['index'], event['column']] = event['new']
                        # Create a completely new DataFrame to force re‑rendering
                        new_df = qg_widget.df.copy()
                        qg_widget.df = new_df
                        
                        # Optionally print the updated row
                        logger.debug("Row after update: %s", qg_widget.df.loc[event['index']])
                        
                        # Update central filter, tagging event appropriately
                        if not ('source' in event and event['source'] == 'central'):
                            event['source'] = 'local'
                            self.filterGridObject.grid_filter_on_cell_edit(event, self.filterGridObject.qgrid_filter)
                    except Exception as e:
                        logger.exception("Exception in on_filter_row_change:")
            return on_filter_row_change

        # Create the callback function for the filter row change
        on_filter_row_change = make_on_filter_row_change(filter_row_widget)

        # Register the new grid's callback as an observer
        logger.debug(f"New filter widget id: {id(filter_row_widget)}")
        self.filterGridObject.add_filter_observer(grid_identifier, on_filter_row_change)
        
        # Attach the event listener if not already attached.
        if not hasattr(filter_row_widget, '_event_listener_attached'):
            logger.debug(f"Attaching event listener to filter_row_widget {grid_identifier} with id {id(filter_row_widget)}.")
            filter_row_widget.on('cell_edited', on_filter_row_change)
            filter_row_widget._event_listener_attached = True

        return widgets.VBox([toolbar_widget, filter_row_widget, result_detail_widget, grid.get_grid_box()],
                            layout=widgets.Layout(border='2px solid black'))

    def _get_collection_dataframe(self, event):
        """
        Retrieves or generates the collection DataFrame based on the change parameter.
        """
        collection_df = self.qm.get_grid_df('collection')
        if collection_df.empty or (event and 'name' in event and event['name'] in {'username', 'generation'}):
            print(f"Generating new collection DataFrame for event: {event}")
            collection_df = self.DataFrameGenerator.manage_central_dataframe()
            self.qm.add_grid('collection', collection_df, options=self.qg_options)
        return collection_df    
    
    def _get_or_update_grid_state(self, grid_identifier, filter_row):
        """
        Retrieves or updates the grid state for a specific grid identifier.

        Args:
            grid_identifier (str): Identifier of the grid.
            filter_row (pd.Series): The filter row data.

        Returns:
            dict: The updated grid state.
        """
        grid_state = self.grid_widget_states.get(grid_identifier, {})
        grid_state.update({
            "info_level": grid_state.get("info_level", 'Basic'),
            "data_set": grid_state.get("data_set", 'Combos'),
            "filter_row": filter_row.to_dict(),
            "Selection": []
        })
        logging.info(f"Grid state updated for '{grid_identifier}': {grid_state}")
        self.grid_widget_states[grid_identifier] = grid_state
        return grid_state
    
    def update_or_refresh_grid(self, grid_identifier, filter_row=None):
        """
        Updates or refreshes the grid based on the rebuild parameter.

        Args:
            grid_identifier (str): Identifier of the grid to update or refresh.
            #collection_df (pd.DataFrame, optional): Collection DataFrame used for filtering.
            filter_row (pd.Series, optional): The filter row to apply for filtering.
            rebuild (bool): If True, recreate the grid; if False, just update it.
        """
        logging.info(f"Updating or refreshing grid '{grid_identifier}'")
        # Retrieve or update the grid state
        if filter_row is None:
            
            # Get index from grid_identifier
            index = grid_identifier.split('_')[-1]
            
            # Retrieve the filter row from the filter grid
            filter_row = self.filterGridObject.get_changed_df().loc[int(index)]

        # Grid Widget State -> Get actual filter row                    
        grid_state = self._get_or_update_grid_state(grid_identifier, filter_row)
        
        if not grid_state:
            logging.info(f"No state found for grid identifier: {grid_identifier}")
            return

        # Retrieve collection data only if it's not provided
        # if collection_df is None:
        #     collection_df = self.qm.get_grid_df('collection')
        #     logging.info(f"Default collection DataFrame retrieved with {len(collection_df)} rows and {len(collection_df.columns)} columns")

        # Apply filters
        filtered_df = self.apply_filters(grid_state)
        
        filtered_df_status = self.check_combo_data_existence(
            collection_name=filter_row['Type'],  # Use the Type field as the collection name
            filter_criteria={},  # Optional filter criteria, e.g., {'name': 'Example'}
            df=filtered_df
        )
        print(filtered_df_status)
    
        # Update or create the grid
        if grid_identifier not in self.qm.grids:
            logging.info(f"Rebuilding grid '{grid_identifier}'")
            grid = self.qm.add_grid(grid_identifier, filtered_df, options=self.qg_options)
            
            # Register the selection event callback for the grid
            logging.info(f"Registering selection event for grid '{grid_identifier}'")
            self.qm.on(grid_identifier, 'selection_changed', self.get_selected_grid_items)
            self.qm.on(grid_identifier, 'selection_changed', self.update_deck_content)   
                     
            logging.info(f"Registering filter change event for grid '{grid_identifier}'")
            self.qm.on(grid_identifier, 'filter_changed', self.get_selected_grid_items)
            self.qm.on(grid_identifier, 'filter_changed', self.update_deck_content)
            
            logging.info(f"Grid '{grid_identifier}' rebuilt with {len(filtered_df)} rows and {len(filtered_df.columns)} columns")            
            
        else:
            logging.info(f"Updating grid '{grid_identifier}' with filtered data")
            grid = self.qm.grids[grid_identifier]
            self.qm.update_dataframe(grid_identifier, filtered_df)
            logging.info(f"Grid '{grid_identifier} ({id(grid.main_widget)}) ' updated with {len(filtered_df)} rows and {len(filtered_df.columns)} columns")
        
        # Check if grid widget exists already in VBoxGrids
        index = int(grid_identifier.split('_')[-1])
        if not self.VBoxGrids.has_widget(index):
            
            # Construct the UI for this grid using the helper function            
            new_widget = self.construct_grid_ui(grid_identifier, filter_row, grid)
            self.VBoxGrids.add_widget(new_widget, index)
            logging.info(f"WidgetBox constructed for index '{index}' with grid '{grid_identifier}'")            
                  
    def create_action_toolbar(self, grid_id):
        """
        Creates an ActionToolbar instance and assigns callbacks specific to the grid_id.
        """
        action_toolbar = ActionToolbar()
        # Assign callbacks using partial to bind grid_id
        action_toolbar.assign_callback('Solbind', self.solbind_request, grid_id=grid_id)
        #action_toolbar.assign_callback('Rename', partial(self.rename_fusion, grid_id))
        action_toolbar.assign_callback('Export', partial(self.save_dataframes_to_csv, grid_id))
        action_toolbar.assign_callback('Open', self.open_deck, grid_id=grid_id)
        #action_toolbar.assign_callback('Open', partial(self.open_deck, grid_id))
        action_toolbar.assign_callback('Graph', self.show_graph, grid_id=grid_id)
        #action_toolbar.add_widget('Generate Fusions', 'button', description = 'Generate Fusion Data', button_style = 'info')
        # TODO - Add callback for 'Generate Fusions' button
        #action_toolbar.assign_callback('Generate Fusions', partial(self.generate_dataframe, grid_id, 'fusion_stats'))
                                       
        
        return action_toolbar.get_ui()

    def create_toolbar(self, grid_identifier):
        # Create and setup toolbar widgets with observer functions
        info_level_button = widgets.Dropdown(
            options=['Basic', 'Detail', 'Listing'],
            value='Basic',
            description='Info Level:',
            layout=widgets.Layout(width='15%', align_self='flex-start')
        )

        spacer = widgets.Box(layout=widgets.Layout(flex='1'))


        default_dataset = self.grid_widget_states.get(grid_identifier, {}).get("data_set", "Stats")

        data_set_dropdown = widgets.Dropdown(
            options=gv.data_selection_sets.keys(),
            value=default_dataset,  # 🔥 Ensure the initial value is correctly set
            description='Data Set:',
            layout=widgets.Layout(width='15%', align_self='flex-end')
        )
        
        def on_info_level_change(event):
            if event['type'] == 'change' and event['name'] == 'value':
                # Update state and refresh grid
                self.grid_widget_states[grid_identifier]['info_level'] = event['new']
                self.update_or_refresh_grid(grid_identifier)

        def on_data_set_change(event):
            if event['type'] == 'change' and event['name'] == 'value':
                # Update state and refresh grid
                self.grid_widget_states[grid_identifier]['data_set'] = event['new']
                logging.debug(f"Data set updated for {grid_identifier}: {event['new']}")
                self.update_or_refresh_grid(grid_identifier)

        info_level_button.observe(on_info_level_change, names='value')
        data_set_dropdown.observe(on_data_set_change, names='value')

        per_grid_controls = widgets.HBox([info_level_button, spacer, data_set_dropdown], layout=widgets.Layout(padding='5px 5px', align_items='center', width='100%'))

         # Create Action Toolbar
        action_toolbar_ui = self.create_action_toolbar(grid_identifier)

        # Combine Per-Grid Controls and Action Toolbar
        combined_toolbar = widgets.VBox([
            per_grid_controls,    # Per-grid controls
            action_toolbar_ui     # Action buttons
        ], layout=widgets.Layout(width='100%'))
        
        return combined_toolbar
        #return widgets.HBox([info_level_button, spacer, data_set_dropdown], layout=widgets.Layout(padding='5px 5px', align_items='center', width='100%'))
 
    def create_summary_widget(self, df, filter_row: pd.Series):
        summary_data: dict[str, any] = {
            'num_matches': len(df),
        }

        # Add one summary column per filter column (excluding metadata fields)
        for column in filter_row.index:
            if column in ['Type', 'Active', 'Mandatory Fields', 'ID']:
                continue

            value = filter_row[column]
            if isinstance(value, str) and value.strip():
                if column in df.columns:
                    unique_matches = sorted(df[column].dropna().astype(str).unique())
                    display_text = ', '.join(unique_matches[:5])
                    if len(unique_matches) > 5:
                        display_text += ' ...'
                    summary_data[f'{column}_matched'] = display_text

        summary_df = pd.DataFrame([summary_data])

        summary_widget = qgrid.show_grid(
            summary_df,
            show_toolbar=False,
            grid_options={
                'editable': False,
                'filterable': False,
                'sortable': False,
                'forceFitColumns': False,
                'defaultColumnWidth': 120,
                'minVisibleRows': 1,
                'maxVisibleRows': 1,
            },
            column_definitions={
                'index': {'width': 30},
                **{col: {'width': 200} for col in summary_df.columns if col != 'num_matches'}
            }
        )

        summary_widget.layout = widgets.Layout(height='65px', width='100%')
        return summary_widget
    
    def create_deck_content_Grid(self):
        # Define the default grid options
        default_options = {
            'minVisibleRows': 10,
            'maxVisibleRows': 20
        }

        # Ensure grid options exist in qg_options, or initialize them if not
        qgrid_options = self.qg_options.copy()
        qgrid_options['grid_options'] = qgrid_options.get('grid_options', {})
        
        # Merge the default options with user-provided options
        qgrid_options['grid_options'].update(default_options)
        
        # Ensure column_options and column_definitions are safely updated
        for name in ['column_options', 'column_definitions']:
            if name in self.qg_options:
                qgrid_options[name] = qgrid_options.get(name, {})
                qgrid_options[name].update(self.qg_options.get(name, {}))

        # Create the deck content qgrid with the merged options
        deck_content_grid = self.qm.add_grid(
            'deck_content',
            pd.DataFrame(),  # Start with an empty DataFrame
            options=qgrid_options
        )

        #print(f"DynamicGridManager::create_deck_content_Grid() - Deck content grid created with options: {qgrid_options}")

        return deck_content_grid
    
    def update_deck_content(self, event, widget):
        
        """Update the deck content DataFrame based on the selected item in the grid."""
        logging.info(f"DynamicGridManager::update_deck_content() - Updating deck content with event: {event}")
        if 'name' in event:
            if event['name'] == 'selection_changed':
                selected_indices = event['new']
            elif event['name'] == 'filter_changed':
                raise NotImplementedError("Filter change event not yet implemented.")
        elif 'new' in event:
            selected_indices = event['new']
        
        grid_df = widget.get_changed_df()            

        if grid_df is not None and selected_indices:
            selected_rows = grid_df.iloc[selected_indices]

            # Extract row names (handle both 'Name' and 'name')
            row_names = selected_rows.get('Name', selected_rows.get('name'))

            # Extract row types
            row_types = selected_rows['Type'].str.lower()

            # Process decks directly
            selected_deck_names = row_names[row_types == 'deck'].tolist()

            # Process fusions and extract 'Deck A' and 'Deck B'
            if 'Deck A' in selected_rows and 'Deck B' in selected_rows:
                fusion_deck_names = selected_rows.loc[row_types == 'fusion', ['Deck A', 'Deck B']].values.flatten()
                selected_deck_names.extend(fusion_deck_names[~pd.isna(fusion_deck_names)])

            logging.info(f"Selected deck names: {selected_deck_names}")

            # Remove any duplicates in the selected deck names
            #selected_deck_names = list(set(selected_deck_names))
                            
            # Generate the deck content DataFrame using the provided function
            deck_content_df = self.DataFrameGenerator.generate_deck_content_dataframe(selected_deck_names)
            #self.data_generate_functions['deck_content'](selected_deck_names)
            #print(deck_content_df)

            # Copy original DataFrame to preserve column order
            combined_df = deck_content_df.copy()                
            options = self.qg_options.copy()
            additional_options = {
                'minVisibleRows': 10,
                'maxVisibleRows': 20
            }
            options.update(additional_options)       
            self.qm.add_grid('deck_content', combined_df, options=options) 

            
    def update_widget(self, group_name, new_widget):
        """Update the second widget in the specified group."""
        # Check if the group exists
        if group_name in self.ui_widget_dict:
            vbox = self.ui_widget_dict[group_name]
            # Ensure the VBox has at least two children
            if len(vbox.children) > 1:
                # Replace the second widget
                new_children = list(vbox.children)
                new_children[1] = new_widget
                vbox.children = new_children
            else:
                raise IndexError(f"Group '{group_name}' does not have a second widget to update.")
        else:
            raise KeyError(f"Group name '{group_name}' not found.")

    def get_ui(self, group_name=None):
        # Return a specific VBox for a given group or a list of all VBoxes
        if group_name:
            return self.ui_widget_dict.get(group_name)

        # Return all VBoxes
        return list(self.ui_widget_dict.values())
    
    def get_active_deck_filters(self):
        """
        Retrieves all active filters that were used to select decks.
        """
        active_filters = []

        for grid_id, grid_state in self.grid_widget_states.items():
            filter_row = grid_state.get("filter_row", None)

            # Ensure it's a Deck filter
            if filter_row and filter_row["Type"] == "Deck":
                active_filters.append(filter_row)

        return active_filters
    
    def on_filter_change(self,updated_grid_id, new_filter):
        # This callback is triggered when the central filter state is updated.
        # Check if the update is relevant to the current grid.
        print(f"Grid {updated_grid_id} updated with new filter: {new_filter}")
        self.update_or_refresh_grid(updated_grid_id, pd.Series(new_filter))
    
    def get_selected_grid_items(self, event, widget):
        """
        Retrieves the currently selected 'Name' items from all main_qgrid_widgets within the GridspecLayout.
        
        Returns:
            dict: A dictionary where keys are grid_ids and values are lists of selected 'Name' items.
        """
        selected_items = {}
        logger.info("Retrieving selected items from all main_qgrid_widgets...")
        
        if widget and event:
            indices = event['new']
            df = widget.get_changed_df()
            grid_id = next((gid for gid, grid in self.qm.grids.items() if grid.main_widget is widget), None)

            if not grid_id:
                logger.warning("No grid_id found for the given widget.")
                return

            if df is not None and not df.empty:
                if 'Name' not in df.columns:
                    logger.error(f"'Name' column not found in DataFrame for grid_id '{grid_id}'.")
                    return

                try:
                    selected_rows = df.iloc[indices]
                except IndexError:
                    logger.error(f"Indices {indices} are out of bounds for DataFrame with shape {df.shape}.")
                    return

                selected_names = selected_rows['Name'].tolist()
                self.grid_widget_states[grid_id]['Selection'] = selected_names
                logger.info(f"Updated selection for grid_id '{grid_id}': {selected_names}")
                return 
                   
        # Iterate over all rows and columns in the grid_layout
        MainVBox = self.VBoxGrids.get_main_vbox()
        for index, cell in enumerate(MainVBox.children):          
            # Glide through all singular VBoxes until at least 3 children are found 
            while len(cell.children) < 3:
                cell = cell.children[0]    
            # Check if the cell is a VBox with at least 3 children
            if isinstance(cell, widgets.VBox) and len(cell.children) >= 3:
                # Extract inner_vbox which contains toggle and main_qgrid_widget
                inner_vbox = cell.children[2]
                
                # Verify inner_vbox structure
                if isinstance(inner_vbox, widgets.VBox) and len(inner_vbox.children) >= 2:
                    # Access the main_qgrid_widget
                    main_qgrid_widget = inner_vbox.children[1]
                    
                    # Ensure the main_qgrid_widget has the method to retrieve selected data
                    if hasattr(main_qgrid_widget, 'get_selected_df'):
                        selected_df = main_qgrid_widget.get_selected_df()
                        
                        # Identify the corresponding grid_id from GridManager
                        grid_id = next((gid for gid, grid in self.qm.grids.items() if grid.main_widget is main_qgrid_widget), None)
                        
                        if grid_id:
                            if not selected_df.empty and 'Name' in selected_df.columns:
                                selected_names = selected_df['Name'].tolist()
                                selected_items[grid_id] = selected_names
                                self.grid_widget_states[grid_id]['Selection'] = selected_names
                                logging.info(f"Selected names for grid_id '{grid_id}': {selected_names}")
                            else:
                                logging.warning(f"No selected items in grid_id '{grid_id}' or 'Name' column missing.")
                        else:
                            logging.warning(f"No matching grid_id found for main_qgrid_widget ID {id(main_qgrid_widget)}.")
                else:
                    logging.info(f"Skipping cell [{index}] as inner_vbox does not contain enough children.")
            else:
                logging.info(f"Skipping cell [{index}] as it does not contain a valid VBox with at least 3 children.")
        
        logging.info(f"\nFinal selected_items: {selected_items}")
        
        return selected_items

    def save_dataframes_to_csv(self, identifier=None, directory='dataframes'):
        def df_to_disk(widget):
            # Get the DataFrame of the current grid
            df = widget.get_changed_df()

            # If the DataFrame is not empty, save it as CSV
            if df is not None and not df.empty:
                csv_filename = os.path.join(directory, f"{identifier}.csv")
                df.to_csv(csv_filename, index=False)
                with self.out_debug:
                    logging.info(f"Saved DataFrame '{identifier}' to {csv_filename}")
            else:
                with self.out_debug:
                    print(f"No data available for grid '{identifier}', skipping...")
        
        """
        Saves the DataFrames of grids that are currently children of the GridSpecLayout as CSV files.

        Args:
            directory (str): The directory where CSV files will be saved. Defaults to 'dataframes'.
        """
        # Create the directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        if identifier:
            # Find the corresponding grid in the GridManager
            grid = self.qm.grids.get(identifier)
            if grid is not None:
                df_to_disk(grid.main_widget)
            else:
                with self.out_debug:
                    print(f"Grid '{identifier}' not found in GridManager, skipping...")
            return # Exit the function early if an identifier is provided

        # Iterate through the current children in GridSpecLayout
        for identifier, widget_box in self.VBoxGrids.vboxes.items():
        #for index, widget_box in enumerate(self.VBoxGrids.get_main_vbox().children):
            # Check if the widget is a VBox containing the grid
            if isinstance(widget_box, widgets.VBox) and len(widget_box.children) > 1:
                grid_widget_box = widget_box.children[1]  # The grid widget is typically the second child in the VBox
                grid_widget = grid_widget_box.children[1]  # Access the actual grid widget
                df_to_disk(grid_widget)                
        with self.out_debug:
            print(f"All applicable DataFrames saved to {directory}:")
      
    # TODO: Seperate these functions from the class 
        
    # Function to open the selected deck in the browser
    def open_deck(self, grid_id):
        
        # def window_open(self,url):
        #     IPython.display.display(IPython.display.Javascript('window.open("{url}");'.format(url=url)))
        #     return None
            
        if not grid_id in self.grid_widget_states or not 'Selection' in self.grid_widget_states[grid_id]: 
            logging.warning(f"No selection found for grid_id '{grid_id}', skipping...")
            return

        def open_website(item_link):
            # Use the output widget context to display the Javascript
            with out:
                out.clear_output()  # Clear previous output if desired
                display(Javascript(f"window.open('{item_link}', '_blank');"))
            return None
            
       # Get selected items and filter row
        selected_items_list = self.grid_widget_states[grid_id]['Selection']
        filter_row = self.grid_widget_states[grid_id]['filter_row']

        # Determine collection type
        collection_name = filter_row['Type']

        # Ensure correct URL path based on collection type
        collection_map = {'fusion': 'fused', 'deck': 'decks'}
        url_collection_name = collection_map.get(collection_name.lower(), collection_name)

        query = {'name': {'$in': selected_items_list}}

        # Fetch item IDs from the database
        item_documents = fetch_filtered_documents(collection_name, None, query, projection_fields=['id'])

        # Iterate over documents and open links
        for item_doc in item_documents:
            item_id = item_doc.get('id')  # Extract the 'id' field

            if item_id:  # Ensure item_id is valid
                item_link = f'https://solforgefusion.com/{url_collection_name}/{item_id}'

                if utils.running_in_browser():
                    open_website(item_link)
                else:
                    webbrowser.open(item_link)
            else:
                logging.warning(f"Missing 'id' field for item: {item_doc}")
                
        return None
    
    def show_graph(self, grid_id):
        selected_items_list = self.grid_widget_states[grid_id]['Selection']        
        display_graph(selected_items_list)    

    def authenticate(self, password):
        
        username = gv.myDB.get_current_db_name()
        net_api = gv.NetApi
        net_api.authenticate(username=username, password=password)
    
    # # Function for making a solbind request
    def solbind_request(self, grid_id=None):
        
        if not grid_id in self.grid_widget_states or not 'Selection' in self.grid_widget_states[grid_id]: 
            logging.warning(f"No selection found for grid_id '{grid_id}', skipping...")
            return
        selected_items_info = self.grid_widget_states[grid_id]['Selection']
        
        # Here, handle multiple selected items if needed
        if ',' in selected_items_info:
            print("Multiple items selected, please select only one deck.")
            return
        
        deck_name = selected_items_info[0]  # Assuming single selection
        deck_data = gv.myDB.find_one('Deck', {'name': deck_name})
        if deck_data:
            print(f"Deck data for '{deck_name}' = {deck_data}")
            deck_id = deck_data.get('id')
        else:
            print(f"Deck '{deck_name}' not found in the database.")
            return
        
        # Proceed with the solbind request using NetApi
        net_api = gv.NetApi
        net_api.post_solbind_request(deck_id)


    def generate_dataframe(self, grid_id, tasks=None) :
        
        # Get the dataframe belonging to the grid_id 
        grid_name = f'filtered_grid_{grid_id}'
        df = self.qm.get_grid_df(grid_name)
        grid_df = self.DataFrameGenerator.generate_central_dataframe(tasks=tasks, filter_df=df)
        if grid_df is None:
            print(f"Failed to generate DataFrame for tasks: {tasks}")
            return
        self.qm.add_grid(f'{grid_name}_generated', grid_df, options=self.qg_options)
        

    def fuse_filtered(self, **kwargs):
        from DeckLibrary import DeckLibrary
        # Get the filtered items from the grid
        # Get grid_ids from active filters
        print("Fuse filtered Kwargs:", kwargs) 
        active_filters_df = self.filterGridObject.get_changed_df()

        if 'Active' in active_filters_df.columns:
            active_filters_df['Active'] = active_filters_df['Active'].map(lambda x: str(x).strip().lower() == "true" if isinstance(x, str) else bool(x))
            active_filters_df['Active'] = active_filters_df['Active'].fillna(False).astype(bool)
            active_filters_df = active_filters_df[active_filters_df['Active']]
        else:
            logging.warning("No 'Active' column found in DataFrame. Skipping filtering step.")
        
        # Grid_id is the index of the active filter
        grid_ids = active_filters_df.index
        print(f"Grid IDs: {grid_ids}")
        # Get the items from the grid_ids 
        grid_items = {}
        for grid_id in grid_ids:
            grid_df = self.qm.get_grid_df(f'filtered_grid_{grid_id}')
            grid_items[grid_id] = grid_df['Name'].tolist()
            
        print(f"Grid items: {grid_items}")
        dl = DeckLibrary(None, None, '' )
        dl.make_fusions(deck_lists = list(grid_items.values()), ump=False)
        
        # Generate the merged filter row
        new_filter = self.filterGridObject.merge_active_filters()

        # Get the current DataFrame from the QGrid widget
        df = self.filterGridObject.qgrid_filter.get_changed_df()

        # Ensure new_filter has all the same columns as df
        new_filter_df = pd.DataFrame([new_filter], columns=df.columns)  # Align columns

        # Ensure new_filter has all necessary columns
        for col in df.columns:
            new_filter.setdefault(col, "")

        # Convert new_filter to a DataFrame and append it
        new_filter_df = pd.DataFrame([new_filter], columns=df.columns).fillna("")

        # Concatenate and update the QGrid widget
        self.filterGridObject.qgrid_filter.df = pd.concat([df, new_filter_df], ignore_index=True).fillna("")

        # Refresh the QGrid display if needed
        #self.refresh_gridbox(event, button)
        new_grid_id = max(grid_id for grid_id in grid_ids) + 1 if grid_ids else 0
        self.update_or_refresh_grid(f"filtered_grid_{new_grid_id}")
        

    # # Function for renaming a fusion
    # def rename_fusion(self, button):
    #     #username = gv.myDB.get_current_db_name()  
    #     selected_items_info = selected_items_label.value.split(': ')[1]  # Extract selected items from the label
    #     #password = text_box.value  # Get the password from the text box
        
    #     # Here, handle multiple selected items if needed
    #     if ',' in selected_items_info:
    #         print("Multiple items selected, please select only one fusion.")
    #         return
    #     fusion_name = selected_items_info.strip(" ")  # Assuming single selection
    #     fusion = gv.myDB.find_one('Fusion', {'name': fusion_name})
                
    #     # Prompt for new name
    #     new_name = text_box.value
        
    #     # Proceed with the rename request using NetApi
    #     net_api = NetApi(username, password)
    #     net_api.update_fused_deck(fusion, new_name)