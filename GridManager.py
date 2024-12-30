import os
from datetime import datetime
from typing import OrderedDict
import pandas as pd
from qgridnext import QgridWidget

try:      import qgridnext as qgrid
except ImportError:    import qgrid
import ipywidgets as widgets
from GlobalVariables import global_vars as gv
from GlobalVariables import rotate_suffix
from CustomCss import CSSManager
from CustomGrids import ActionToolbar

from DataSelectionManager import DataSelectionManager
from MongoDB.DatabaseManager import DatabaseManager
from SortingManager import SortingManager

# module global variables 

DEFAULT =  pd.DataFrame({
            'Type': ['Deck'],
            'Name': [''],
            'Modifier': [''],
            'Creature': [''],
            'Spell': [''],
            'Forgeborn Ability': [''],
            'Active': [True],
            'Mandatory Fields': ['Name, Forgeborn Ability']
        })

TESTING =  pd.DataFrame({
            'Type': ['Fusion'],
            'Name': [''],
            'Modifier': [''],
            'Creature': [''],
            'Spell': [''],
            'Forgeborn Ability': [''],
            'Active': [True],
            'Mandatory Fields': ['Name, Forgeborn Ability']
        })

DEFAULT_FILTER = DEFAULT


class GridManager:
    EVENT_DF_STATUS_CHANGED = 'df_status_changed'

    def __init__(self, debug_output):

        self.grids = {}
        self.callbacks = {}
        self.qgrid_callbacks = {}
        self.relationships = {}
        self.debug_output = debug_output
        self.css_manager = CSSManager()
        self.sorting_manager = SortingManager(gv.rotated_column_definitions)
        self.custom_css_class = self.css_manager.create_and_inject_css('filter_grids', rotate_suffix)
        self.grid_initializer = GridInitializer(self.sorting_manager, self.css_manager, gv.rotated_column_definitions, self.custom_css_class, debug_output)


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
                
        #self.update_dataframe(identifier, df)
        self.css_manager.apply_conditional_class(grid.main_widget, rotate_suffix, self.custom_css_class)

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
        self.toggle_widget = self.create_toggle_widget(df)        
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
        #df = self.main_widget.get_changed_df()
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

        return df
        

    def set_dataframe_version(self, version, df):
        self.df_versions[version] = df
        self.df_status['current'] = 'filtered'
        self.df_status['last_set']['filtered'] = datetime.now()

    def reset_dataframe(self):
        self.df_versions['default'] = pd.DataFrame()
        self.update_main_widget(self.df_versions['default'])

class QGrid(BaseGrid):
    def create_main_widget(self, df):
        # Define default grid options
        default_grid_options = {
            'forceFitColumns': False,
            'enableColumnReorder': True,
            'minVisibleRows': 10,
        }

        # Get user-provided grid options from self.qgrid_options and update the defaults
        user_grid_options = self.qgrid_options.get('grid_options', {})
        
        # Log the incoming options and the defaults
        #print(f"QGrid::create_main_widget() - Default grid options: {default_grid_options}")
        #print(f"QGrid::create_main_widget() - User-provided grid options: {user_grid_options}")
        
        # Update default options with user-provided options
        default_grid_options.update(user_grid_options)
        
        # Debugging: Check merged options
        #print(f"QGrid::create_main_widget() - Merged grid options (default + user): {default_grid_options}")

        # Create the QGrid widget with updated options
        self.main_widget = qgrid.show_grid(
            df,
            column_options=self.qgrid_options.get('column_options', {}),
            column_definitions=self.qgrid_options.get('column_definitions', {}),
            grid_options=default_grid_options,  # Use the updated default options
            show_toolbar=False
        )
        
        # Confirm creation of the main widget and options passed
        #print(f"QGrid::create_main_widget() - Final grid options passed to qgrid: {default_grid_options}")
        
    # def update_main_widget(self, new_df):        
    #     self.main_widget.df = new_df
    #     self.set_dataframe_version('filtered', new_df)
        
    def update_main_widget(self, new_df):
        # Log new DataFrame details
        #print(f"Updating main widget with DataFrame: Shape={new_df.shape}, Columns={list(new_df.columns)}")
        #print(new_df.head())

        # Update the widget's DataFrame        
        #logging.info(f"Sleeping for 0.75 seconds before updating the main widget")
        #time.sleep(0.75)
        #listeners = getattr(self.main_widget, '_event_listeners', None)
        #print(f"Event listeners attached to widget: {listeners}")
        self.main_widget.df = new_df                


class PandasGrid(BaseGrid):
    def create_main_widget(self, df):
        self.update_main_widget(df)

    def update_main_widget(self, new_df):
        self.df_versions['default'] = new_df.copy()
        self.set_dataframe_version('filtered', new_df)


import utils  
class GridInitializer:
    def __init__(self, sorting_manager, css_manager, rotated_column_definitions, custom_css_class, debug_output):
        self.sorting_manager = sorting_manager
        self.css_manager = css_manager
        self.rotated_column_definitions = rotated_column_definitions
        self.custom_css_class = custom_css_class
        self.out_debug = debug_output

    def initialize_grid_with_totals(self, df, grid_widget=None):
        """
        Helper function to create and initialize the qgrid widget with the given DataFrame.
        This function calculates the sum of numeric columns, inserts the totals row at the top,
        applies multi-column sorting based on sorting_info, and returns the qgrid widget.
        """
        with self.out_debug:
            # Remove any existing totals row from the DataFrame (if it's already present)
            data_rows = df[df['DeckName'] != 'Totals'].reset_index(drop=True)

            # Use the utility function to calculate the totals row
            totals_row = utils.get_totals_row(data_rows, self.rotated_column_definitions)

            # Concatenate the totals row at the top of the DataFrame
            updated_df = pd.concat([totals_row, data_rows], ignore_index=True)

            # Apply sorting to the DataFrame based on sorting_info
            if self.sorting_manager.sorting_info:
                # Sort the columns by their sort_order and prepare them for sorting
                columns_to_sort = [col for col in sorted(self.sorting_manager.sorting_info, key=lambda x: self.sorting_manager.sorting_info[x]['sort_order'])]
                ascending_states = [self.sorting_manager.sorting_info[col]['ascending'] for col in columns_to_sort]
                updated_df = self.sorting_manager.sort_dataframe(updated_df, columns_to_sort, ascending_states)

                #print(f"Initializing grid with sorting. Columns to sort: {columns_to_sort}, Ascending states: {ascending_states}")

            # Update the column definitions for sorted/filtered columns
            new_column_definitions = gv.all_column_definitions.copy()
            updated_column_definitions = self.css_manager.get_column_definitions_with_gradient(new_column_definitions, self.sorting_manager.sorting_info)

            # Create the qgrid widget
            widget = qgrid.show_grid(
                updated_df,
                show_toolbar=False,
                column_definitions=updated_column_definitions,
                grid_options={'forceFitColumns': False, 'filterable': True, 'sortable': True, 'minVisibleRows': 17, 'maxVisibleRows': 30}
            )

            # Apply CSS if needed
            if self.css_manager.needs_custom_styles(widget, rotate_suffix):
                self.css_manager.apply_css_to_widget(widget, self.custom_css_class)
            else:
                widget.remove_class(self.custom_css_class)

            # Register event handlers for sorting and filtering
            widget.on('sort_changed', self.sorting_manager.handle_sort_changed)

            return widget

from MyWidgets import EnhancedSelectMultiple, VBoxManager
class FilterGrid:
    """
    Manages the grid for filtering data based on user-defined criteria.
    """
    def __init__(self, function_refresh):
        """
        Initializes a new instance of the FilterGrid class.

        Args:
            update_decks_display (function): The function to call when the filter grid is updated.
        """
        self.refresh_function = function_refresh
        self.df = self.create_initial_dataframe()
        self.qgrid_filter = self.create_filter_qgrid()
        self.selection_box, self.selection_widgets, self.toggle_buttons_dict = self.create_selection_box()
        DataSelectionManager.register_observer(self.update)

    def create_filter_qgrid(self):
        """
        Creates the filter qgrid.

        Returns:
            qgrid.QGridWidget: The qgrid widget for filtering.
        """
        qgrid_filter = qgrid.show_grid(
            self.df,
            grid_options={'forceFitColumns': False, 'minVisibleRows': 4, 'maxVisibleRows': 5, 'enableColumnReorder': False},
            column_definitions={'index': {'width': 50}, 'op1': {'width': 50}, 'op2': {'width': 50}},
            show_toolbar=True
        )
        qgrid_filter.layout = widgets.Layout(height='auto')
        qgrid_filter.on('row_added', self.grid_filter_on_row_added)
        qgrid_filter.on('row_removed', self.grid_filter_on_row_removed)
        qgrid_filter.on('cell_edited', self.grid_filter_on_cell_edit)        
        return qgrid_filter

    @staticmethod
    def create_initial_dataframe():
        """
        Creates the initial dataframe for the filter grid.

        Returns:
            pandas.DataFrame: The initial dataframe.
        """
        
        #initial_type = 'Deck'
        
        return DEFAULT_FILTER
    
    # pd.DataFrame({
    #         'Type': [initial_type],
    #         'Name': [''],
    #         'Modifier': [''],
    #         'Creature': [''],
    #         'Spell': [''],            
    #         'Forgeborn Ability': [''],
    #         'Active': [True],
    #         'Mandatory Fields': ['Name, Forgeborn Ability']
    #     })

    def grid_filter_on_row_removed(self, event, widget):
        """
        Handles the 'row_removed' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        if gv.out_debug:
            with gv.out_debug:
                print(f"FilterClass::grid_filter_on_row_removed() - Removing row {event['indices']} from filter grid")
        
        num_rows = len(widget.get_changed_df())
        #print(f"Number of rows in filter grid: {num_rows}")
        active_rows = []
        
        if num_rows == 0:                                
            df = pd.DataFrame({
                'Type': ['Deck'],
                'Name': [''],
                'Modifier': [''],
                'Creature': [''],                
                'Spell': [''],            
                'Forgeborn Ability': [''],                
                'Active': [False],                
                'Mandatory Fields': ['Name, Forgeborn Ability']
            })
            widget.df = df
                          
        widget.df = widget.get_changed_df()

        # Update the `Active` status or remove rows entirely
        #for row_index in event['indices']:
        #    if row_index in widget.df.index:
        #        widget.df.at[row_index, 'Active'] = False  # Mark as inactive

         # Get indices of active rows
        active_indices = widget.df[widget.df['Active']].index.tolist()
        

        # Pass indices, not DataFrame, to refresh_function
        #self.refresh_function({'new': active_indices, 'old': event['indices'], 'owner': 'filter'})
        self.refresh_function(event, widget)
                

    def grid_filter_on_row_added(self, event, widget):
        """
        Handles the 'row_added' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        #if gv.out_debug:
        #    with gv.out_debug:
        logger.info(f"FilterClass::grid_filter_on_row_added() - Adding new row to filter grid")
        
        new_row_index = event['index']
        df = widget.get_changed_df()

        mandatory_fields = []

        # Set the values for each column in the new row
        for column in df.columns:
            if column in self.selection_widgets:
                widget_value = self.selection_widgets[column].value
                logger.info(f"FilterClass::grid_filter_on_row_added() - Column: {column}, Value: {widget_value}")
                # Special handling for the 'Forgeborn Ability' column
                if column == 'Forgeborn Ability':
                    fb_ability_list = [fb_ability.split(' : ')[1] for fb_ability in widget_value]
                    value = '; '.join(fb_ability_list)
                else:
                    # Convert the widget value to string, handling different possible types
                    if isinstance(widget_value, (list, set, tuple)):
                        if len(widget_value) == 1:
                            # If there's only one element in the list/set/tuple, use that element directly
                            value = str(widget_value[0])
                        else:
                            # Join multiple values into a semicolon-separated string
                            value = '; '.join([str(v) for v in widget_value])
                    elif isinstance(widget_value, str):
                        value = widget_value
                    else:
                        value = str(widget_value)

                # Assign the flattened string value to the DataFrame
                df.at[new_row_index, column] = value

                # Check if the field is mandatory
                if column in self.toggle_buttons_dict and self.toggle_buttons_dict[column].value:
                    mandatory_fields.append(column)
                    

        # Always set the "Active" column to True for new rows    
        df.at[new_row_index, 'Active'] = True

        # Update the "Mandatory Fields" column
        df.at[new_row_index, 'Mandatory Fields'] = ', '.join(mandatory_fields)

        widget.df = df

        logger.info(f"FilterClass::grid_filter_on_row_added() - Calling refresh function for index {new_row_index}")
        
        self.refresh_function(event, widget)
        #self.refresh_function({'new': new_row_index, 'old': None, 'owner': 'filter'})

    def grid_filter_on_cell_edit(self, event, widget):
        """
        Handles the 'cell_edited' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        #if gv.out_debug:
            #with gv.out_debug:
                #print(f"FilterClass::grid_filter_on_cell_edit() - Editing cell in filter grid")
        row_index, column_index = event['index'], event['column']
        widget.df.loc[row_index, column_index] = event['new']
        
        widget.df = widget.df
        #Print the edited row from the widget
        #if gv.out_debug:
            #with gv.out_debug:
                #print(f"Edited row: {widget.df.loc[row_index]}")
        rebuild = False
        if column_index == 'Active' and widget.df.loc[row_index, 'Active']: rebuild = True
        #self.refresh_function({'new': row_index, 'old': None, 'owner': 'filter'})
        self.refresh_function(event, widget)

    def update(self, event, widget):
        """
        Updates the filter grid based on changes in the data selection sets.
        """
        if gv.out_debug:
            with gv.out_debug:
                print(f"FilterClass::update() -> Updating filter grid with new data selection sets: {gv.data_selection_sets.keys()}")
        self.selection_widgets['Data Set'].options = gv.data_selection_sets.keys()

    
    ### Selection Box Functions ###
    def update_selection_content(self, change):
        """
        Updates the selection content based on changes in the widget values.

        Args:
            change (dict): The change notification data.
        """
        if change['name'] == 'value' and change['new'] != change['old']:
            for cardType in ['Modifier', 'Creature', 'Spell']:
                widget = self.selection_widgets[cardType]
                widget.options = [''] + get_cardType_entity_names(cardType)
            
            if gv.myDB: 
                dbDeckNames = gv.myDB.find('Deck', {}, {'name': 1})  # Get documents with only 'name' field
                # Extract the 'name' field from each result and sort alphabetically
                sorted_deckNames = [''] + sorted([deck.get('name', '') for deck in dbDeckNames if 'name' in deck], key=lambda x: x.lower())
                #self.selection_widgets['Name'].options = sorted_deckNames
                self.selection_widgets['Name'].update_options_from_db(sorted_deckNames)
                #print(f"DeckNames = {self.selection_widgets['Name'].options}")

    def create_cardType_names_selector(self, cardType, options=None):
        if options is None:
            options = {}
        layout_options = {
            'width': '20%',  # Default width
            'height': 'auto',
            'align_items': 'center',
            'justify_content': 'center',
            'overflow': 'hidden',
        }
        # Update default options with any overrides from 'options'
        layout_options.update(options)
        cardType_entity_names = [''] + get_cardType_entity_names(cardType)
        cardType_name_widget = EnhancedSelectMultiple(
            options=cardType_entity_names,
            toggle_description = cardType,
            description='',
            layout=widgets.Layout(**layout_options)
        )
        return cardType_name_widget

    
    # Create a function to use the EnhancedSelectMultiple widget
    def create_deckName_selector(self):
        deckNames = []
        if gv.myDB:
            # Query the database to find all deck names
            dbDeckNames = gv.myDB.find('Deck', {}, {'name': 1})  # Get documents with only 'name' field
            # Extract the 'name' field from each result
            deckNames = [deck.get('name', '') for deck in dbDeckNames if 'name' in deck]
            # Sort the deck names alphabetically
            deckNames = sorted(deckNames, key=lambda x: x.lower())  # Sort case-insensitively

        # Add an empty option to the beginning of the list
        deckNames.insert(0, '')

        # Debug statement to verify deckNames before creating the widget
        #print(f"Deck names before initializing EnhancedSelectMultiple: {deckNames}")

        # Create the enhanced SelectMultiple widget with search functionality
        deckName_widget = EnhancedSelectMultiple(
            options=deckNames,
            description='',
            toggle_description='Name',
            layout=widgets.Layout(width='30%', height='auto', align_items='center', justify_content='center', overflow='hidden'),
            toggle_default=True
        )
        return deckName_widget

    # Function to create aligned selection box with labels
    def create_selection_box(self):
        # Define widgets with their layout settings
        widgets_dict = {
            'Type': EnhancedSelectMultiple(
                options=['Deck', 'Fusion'],
                value=['Deck'],
                description='',
                toggle_description='Type',
                toggle_default=True,
                toggle_disable=True,
                layout=widgets.Layout(width='10%', border='1px solid cyan', align_items='center', justify_content='center')
            ),
            'Name': self.create_deckName_selector(),
            'Modifier': self.create_cardType_names_selector('Modifier', options={'border': '1px solid blue'}),
            'Creature': self.create_cardType_names_selector('Creature', options={'border': '1px solid green'}),
            'Spell': self.create_cardType_names_selector('Spell', options={'border': '1px solid red'}),
            'Forgeborn Ability': EnhancedSelectMultiple(options=[''] + get_forgeborn_abilities(), description='', toggle_description='Forgeborn Ability', toggle_default=True, 
                                                        layout=widgets.Layout(width='30%', height='auto', border='1px solid orange', align_items='center', justify_content='center', overflow='hidden')),
        }

        # Create widget row with all selection widgets
        widget_row_items = [widgets_dict[key] for key in widgets_dict]
        #widget_row = widgets.HBox(widget_row_items, layout=widgets.Layout(display='flex', flex_flow='row nowrap', width='100%', align_items='center', justify_content='flex-start', gap='5px'))

        widget_row_items = [widget.get_widget() if isinstance(widget, EnhancedSelectMultiple) else widget for widget in widget_row_items]
        widget_row = widgets.HBox(widget_row_items, layout=widgets.Layout(display='flex', flex_flow='row nowrap', width='100%', align_items='center', justify_content='flex-start', gap='5px'))


        # Build the toggle button dictionary
        toggle_buttons_dict = { key : widget.toggle_button for key, widget in widgets_dict.items() if hasattr(widget, 'toggle_button') and key != 'Type'}
        
        # Vertical box to hold both rows
        selection_box = widgets.VBox([widget_row], layout=widgets.Layout(width='100%'))

        return selection_box, widgets_dict, toggle_buttons_dict



    def get_changed_df(self):
        """
        Returns the current DataFrame with any user changes.

        Returns:
            pandas.DataFrame: The changed dataframe.
        """
        return self.qgrid_filter.get_changed_df()

    def get_widgets(self):
        """
        Returns the widgets associated with the filter grid.

        Returns:
            tuple: A tuple containing the selection box and the filter qgrid widget.
        """
        return self.selection_box, self.qgrid_filter


def get_cardType_entity_names(cardType):
    """
    Retrieves the names of entities that match the specified card type.

    Args:
        cardType (str): The type of card.

    Returns:
        list: A list of entity names that match the card type.
    """
    commonDB = DatabaseManager('common')
    cardType_entities = commonDB.find('Entity', {"attributes.cardType": cardType})
    cardType_entities_names = [entity['name'] for entity in cardType_entities]
    if gv.myDB: 
        # If the user has a database, filter the cardType_entities_names to only include cards that are in the user's database
        cards = gv.myDB.find('Card', {})
        cardNames = [card.get('title', card.get('name', '')) for card in cards]
        cardType_entities_names = [name for name in cardType_entities_names if any(name in cardName for cardName in cardNames)]
    cardType_entities_names.sort()
    return cardType_entities_names

def get_forgeborn_abilities():
    """
    Retrieves the names of forgeborn abilities.

    Returns:
        list: A list of forgeborn ability names.
    """
    commonDB = DatabaseManager('common')
    forgeborns = commonDB.find('Forgeborn', {})
    forgeborn_abilities_list = [forgeborn['abilities'] for forgeborn in forgeborns]
    ability_names = [ f"{id[5:-5].capitalize()} : {name}" for abilities in forgeborn_abilities_list for id, name in abilities.items() if "Fraud" not in name]
    # Cut out the forgeborn ability prefix 'C<number> - '
    ability_names = [re.sub(r'C\d+ - ', '', name) for name in ability_names]
    # Remove duplicates
    ability_names = list(set(ability_names))
    #print(f"Found {len(ability_names)} forgeborn abilities : {ability_names}")
    ability_names.sort()
    return ability_names


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
            first_target = ['cardTitles']
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
            if column not in mandatory_fields and column not in ['Type', 'Mandatory Fields', 'Active'] and isinstance(filter_row[column], str) and filter_row[column]:
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

import json
def apply_filter_to_database(filter_df):    
    def query_to_mongo_compass_format(query: dict) -> str:
        """
        Converts a MongoDB query dictionary into a JavaScript-compatible string
        for use in MongoDB Compass.

        Args:
            query (dict): The MongoDB query dictionary.

        Returns:
            str: The formatted query string for MongoDB Compass.
        """
        try:
            # Convert Python dictionary to a JSON string
            compass_query = json.dumps(query, indent=4)
            # Replace JSON-specific syntax with JavaScript-compatible syntax
            compass_query = compass_query.replace('"$and"', '$and')
            compass_query = compass_query.replace('"$in"', '$in')
            compass_query = compass_query.replace('"$regex"', '$regex')
            compass_query = compass_query.replace('"$options"', '$options')
            return compass_query
        except Exception as e:
            raise ValueError(f"Failed to convert query for MongoDB Compass: {e}")

    def filter_by_substring(filter_row):
        def build_query(filter_step):
            # Extract information from filter step
            first_target = filter_step.get('first_target', [''])
            second_target = filter_step.get('second_target', [''])
            first_operator = filter_step.get('first_operator', 'OR')
            second_operator = filter_step.get('second_operator', 'OR')

            if first_target == [''] or second_target == ['']:
                return {}

            # Initialize the query parts
            query_parts = []

            # Iterate over the first target (fields or substrings)
            for first_item in first_target:
                field_queries = []

                # Iterate over the second target (substrings or fields)
                for second_item in second_target:
                    if filter_step['first_target_type'] == 'field':
                        # First target is field, second is substring
                        string_item = second_item
                        field_item = first_item
                    else:
                        # First target is substring, second is field
                        string_item = first_item
                        field_item = second_item

                    # Prepare the regex for MongoDB
                    string_item = re.sub(r',\s*', ' ', string_item)
                    #regex = fr"(^|\W){re.escape(string_item)}($|\W)"
                    regex = re.escape(string_item)
                    
                    # Build the field query
                    field_query = {field_item: {"$regex": regex, "$options": "i"}}
                    field_queries.append(field_query)

                # Combine field queries with the second operator
                if second_operator == 'AND':
                    query_parts.append({"$and": field_queries})
                else:  # OR logic
                    query_parts.append({"$or": field_queries})

            # Combine all field queries with the first operator
            if first_operator == 'AND':
                return {"$and": query_parts}
            else:  # OR logic
                return {"$or": query_parts}

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
            first_operator = 'OR'
            second_operator = substring_operator
            first_target = ['cardTitles']
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

            return {
                'first_target': first_target,
                'second_target': second_target,
                'first_operator': first_operator,
                'second_operator': second_operator,
                'first_target_type': first_target_type 
            }

        # Begin building the query for the filter row
        mongo_query = {}

        # Apply Type filter first (always mandatory)
        if 'Type' in filter_row and isinstance(filter_row['Type'], str) and filter_row['Type']:
            type_substrings = filter_row['Type'].split(',')
            type_query = {"type": {"$in": type_substrings}}
            mongo_query.update(type_query)

        # Apply mandatory fields
        mandatory_fields = filter_row.get('Mandatory Fields', '')
        if isinstance(mandatory_fields, str):
            mandatory_fields = mandatory_fields.split(', ')
        mandatory_fields = [column.strip() for column in mandatory_fields]

        for column in mandatory_fields:
            filter_step = determine_filter_config(column, filter_row, filter_row[column])            
            query_part = build_query(filter_step)
            mongo_query.update(query_part)

        # Apply optional fields (at least one must match)
        or_conditions = []
        for column in filter_row.index:
            if column not in mandatory_fields and column not in ['Type', 'Mandatory Fields', 'Active'] and isinstance(filter_row[column], str) and filter_row[column]:
                filter_step = determine_filter_config(column, filter_row, filter_row[column]) 
                query_part = build_query(filter_step)
                or_conditions.append(query_part)

        if or_conditions:
            mongo_query["$or"] = or_conditions

        return mongo_query

    # Beginning of the apply_filter_to_database function
    active_filters = filter_df[filter_df['Active'] == True]  # Get only the active filters
    final_query = {"$and": []}  # Combine all filter queries with AND logic

    for _, filter_row in active_filters.iterrows():
        row_query = filter_by_substring(filter_row)
        final_query["$and"].append(row_query)

    # Execute the query
    results = []
    if gv.myDB:
        myQuery = query_to_mongo_compass_format(final_query)
        print(f"Final query: {myQuery}")
        results = list(gv.myDB.find('Fusion', final_query))
    return results


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

from functools import partial
import webbrowser
import FieldUnifier
from GraphVis import display_graph
import logging
import time
from datetime import datetime
import numpy as np

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class DynamicGridManager:

    def __init__(self, data_generate_functions, qg_options, out_debug):
        self.out_debug = out_debug       
        self.data_generate_functions = data_generate_functions
        self.qg_options = qg_options
        self.qm = GridManager(out_debug)
        
        self.filterGridObject = FilterGrid(self.refresh_gridbox)
        self.deck_content_Grid = self.create_deck_content_Grid()
        self.sorting_info = {}
        self.css_manager = CSSManager()        
        self.custom_css_class = self.css_manager.create_and_inject_css('deck_content', rotate_suffix)        
        self.grid_widget_states = {}
        self.refresh_needed = False  # Flag to indicate whether refresh is needed
    
    
        # Toolbar 
            
        """
        Creates an ActionToolbar instance and assigns callbacks specific to the grid_id.
        """
        button_configs = {
            "Authenticate": {"description": "Login", "button_style": 'info', "callback": self.authenticate},
            "Generate": {"description": "Generate Table", "button_style": "success"},
        }
        action_toolbar = ActionToolbar(button_configs=button_configs)
        # Assign callbacks using partial to bind grid_id
        action_toolbar.assign_callback('Generate', self.handle_database_change, refresh_needed=True)
    
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
        
        
    def apply_filters(self, df, widget_states):
        # Filter columns based on the filter_row
        info_level = widget_states['info_level']
        data_set = widget_states['data_set']
        filter_row = widget_states['filter_row']
        #if filter_row['Type'] == 'Fusion':
        #    results = apply_filter_to_database(pd.DataFrame([filter_row]))
        #else:
        filtered_df = apply_filter_to_dataframe(df, pd.DataFrame([filter_row]))        
        return self.determine_columns(filtered_df, info_level, data_set, filter_row['Type'])
        
    def determine_columns(self, df, info_level, data_set, item_type):
        
        data_set_columns = FieldUnifier.generate_final_fields(info_level, data_set, item_type)        
        existing_columns = [col for col in data_set_columns if col in df.columns]
        filtered_df = df.loc[:, existing_columns]    
        
        return filtered_df


    def handle_database_change(self, refresh_needed=False):
        """
        Handles updates required when the database changes, ensuring updates are only performed if flagged.
        """
        if refresh_needed:   self.set_refresh_needed(True)
        
        if not self.refresh_needed:
            logging.info("No refresh needed. Skipping database change handling.")
            return

        logging.info("Handling database change in DynamicGridManager.")

        # Step 1: Update the collection DataFrame
        try:
            collection_df = self.data_generate_functions['central_dataframe']()
            self.qm.add_grid('collection', collection_df, options=self.qg_options)
            logging.info(f"Collection DataFrame updated with {len(collection_df)} rows.")
        except Exception as e:
            logging.error(f"Failed to update collection DataFrame: {e}")
            return

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
                self.update_or_refresh_grid(grid_identifier, filter_row=filter_row, collection_df=collection_df)
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
            collection_df = self._get_collection_dataframe(event)

            # Get active and inactive filter rows
            if widget: # If a widget is provided, use its filter row
                filter_df = widget.get_changed_df()
            else:
                filter_df = self.filterGridObject.get_changed_df()
            active_filters_df = filter_df[filter_df['Active']]
            inactive_filters_df = filter_df[~filter_df['Active']]

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
                logger.info(f"Handling row-specific update from filter: {specific_index}")
                    
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
                            self.update_or_refresh_grid(grid_identifier, collection_df, filter_row)
                            return    
                
                # Handle case where specific_index is a DataFrame
                if isinstance(specific_index, pd.DataFrame):
                    logger.info("Specific index is a DataFrame. Extracting indices.")
                    specific_index = specific_index.index.tolist()

                # Check for empty or malformed selections
                if isinstance(specific_index, (list, pd.DataFrame)) and not specific_index:
                    logger.info("Received empty selection; no grids to update.")
                    return

                self._handle_specific_update(specific_index, active_filters_df, inactive_filters_df, collection_df)
                return
    

            # Default: Refresh all active grids and remove inactive grids
            logger.info("No specific change provided; refreshing all active grids and removing inactive grids.")
            self._refresh_all_grids(active_filters_df, collection_df)
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

    def _handle_specific_update(self, specific_index, active_filters_df, inactive_filters_df, collection_df):
        """
        Handles updates for specific indices based on the change object.

        Args:
            specific_index (int, list, or unexpected type): Index or indices to update.
            active_filters_df (DataFrame): Active filter rows.
            inactive_filters_df (DataFrame): Inactive filter rows.
            collection_df (DataFrame): The collection DataFrame.
        """
        if isinstance(specific_index, (int, np.integer)):  # Single index
            self._process_single_index(specific_index, active_filters_df, inactive_filters_df, collection_df)

        elif isinstance(specific_index, list):  # Multiple indices
            for grid_index in specific_index:
                self._process_single_index(grid_index, active_filters_df, inactive_filters_df, collection_df)

        elif isinstance(specific_index, pd.DataFrame):  # Unexpected DataFrame case
            logger.warning(f"Received DataFrame instead of index: {specific_index}. Attempting to resolve.")
            # Attempt to resolve, e.g., by using the DataFrame's index or resetting the gridbox
            resolved_index = specific_index.index.tolist() if not specific_index.empty else None
            if resolved_index:
                self._handle_specific_update(resolved_index, active_filters_df, inactive_filters_df, collection_df)
            else:
                logger.error("Cannot process DataFrame; no valid indices found.")
        
        else:  # Other unexpected types
            logger.warning(f"Invalid type for specific_index: {type(specific_index)}. Contents: {specific_index}")

    def _process_single_index(self, grid_index, active_filters_df, inactive_filters_df, collection_df):
        """
        Process a single grid index for updating or removal.

        Args:
            grid_index (int): Index of the grid to process.
            active_filters_df (DataFrame): Active filter rows.
            inactive_filters_df (DataFrame): Inactive filter rows.
            collection_df (DataFrame): The collection DataFrame.
        """
        if grid_index in active_filters_df.index:
            filter_row = active_filters_df.loc[grid_index]
            grid_identifier = f"filtered_grid_{grid_index}"
            self.update_or_refresh_grid(grid_identifier, collection_df, filter_row)

        elif grid_index in inactive_filters_df.index:
            self.VBoxGrids.remove_widget(grid_index)
            logger.info(f"Removed inactive grid with index '{grid_index}'.")

        else:
            self.VBoxGrids.remove_widget(grid_index)
            logger.info(f"Removed grid with index '{grid_index}'.")
            #logger.warning(f"Grid index {grid_index} not found in any filter indices.")

    def _refresh_all_grids(self, active_filters_df, collection_df):
        """
        Refreshes all active grids.

        Args:
            active_filters_df (DataFrame): Active filter rows.
            collection_df (DataFrame): The collection DataFrame.
        """
        for row_index, filter_row in active_filters_df.iterrows():
            grid_identifier = f"filtered_grid_{row_index}"
            self.update_or_refresh_grid(grid_identifier, collection_df, filter_row)

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
        filter_row_widget = qgrid.show_grid(
            pd.DataFrame([filter_row]), 
            show_toolbar=False,
            grid_options={'forceFitColumns': True, 'filterable': False, 'sortable': False, 'editable': True}
        )
        filter_row_widget.layout = widgets.Layout(height='70px')

        # Add event listener for cell edits in filter_row_widget
        def on_filter_row_change(event, qgrid_widget=filter_row_widget):
            # Only trigger update if there's a significant change
            if event['new'] != event['old']:
                print(f"Cell edited in filter_row_widget for grid '{grid_identifier}': {event}")  # Debug statement                
                self.refresh_gridbox(event, qgrid_widget)

        # Attach only one event listener to avoid redundancy
        if not hasattr(filter_row_widget, '_event_listener_attached'):
            filter_row_widget.on('cell_edited', on_filter_row_change)
            filter_row_widget._event_listener_attached = True

        return widgets.VBox([toolbar_widget, filter_row_widget, grid.get_grid_box()],
                            layout=widgets.Layout(border='2px solid black'))

    def _get_collection_dataframe(self, event):
        """
        Retrieves or generates the collection DataFrame based on the change parameter.
        """
        collection_df = self.qm.get_grid_df('collection')
        if collection_df.empty or (event and 'name' in event and event['name'] in {'username', 'generation'}):
            print(f"Generating new collection DataFrame for event: {event}")
            collection_df = self.data_generate_functions['central_dataframe']()
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
            "data_set": grid_state.get("data_set", 'Stats'),
            "filter_row": filter_row.to_dict()
        })
        logging.info(f"Grid state updated for '{grid_identifier}': {grid_state}")
        self.grid_widget_states[grid_identifier] = grid_state
        return grid_state
    
    def update_or_refresh_grid(self, grid_identifier, collection_df=None, filter_row=None):
        """
        Updates or refreshes the grid based on the rebuild parameter.

        Args:
            grid_identifier (str): Identifier of the grid to update or refresh.
            collection_df (pd.DataFrame, optional): Collection DataFrame used for filtering.
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
                    
        grid_state = self._get_or_update_grid_state(grid_identifier, filter_row)
        
        if not grid_state:
            logging.info(f"No state found for grid identifier: {grid_identifier}")
            return

        # Retrieve collection data only if it's not provided
        if collection_df is None:
            collection_df = self.qm.get_grid_df('collection')
            logging.info(f"Default collection DataFrame retrieved with {len(collection_df)} rows and {len(collection_df.columns)} columns")

        # Apply filters
        filtered_df = self.apply_filters(collection_df, grid_state)

        # Update or create the grid
        if grid_identifier not in self.qm.grids:
            logging.info(f"Rebuilding grid '{grid_identifier}'")
            grid = self.qm.add_grid(grid_identifier, filtered_df, options=self.qg_options)
            
            # Register the selection event callback for the grid
            logging.info(f"Registering selection event for grid '{grid_identifier}'")
            self.qm.on(grid_identifier, 'selection_changed', self.update_deck_content)            
            self.qm.on(grid_identifier, 'selection_changed', self.get_selected_grid_items)
            self.qm.on(grid_identifier, 'filter_changed', self.update_deck_content)
            self.qm.on(grid_identifier, 'filter_changed', self.get_selected_grid_items)
            logging.info(f"Grid '{grid_identifier}' rebuilt with {len(filtered_df)} rows and {len(filtered_df.columns)} columns")            
            
        else:
            logging.info(f"Updating grid '{grid_identifier}' with filtered data")
            grid = self.qm.grids[grid_identifier]
            self.qm.update_dataframe(grid_identifier, filtered_df)
            logging.info(f"Grid '{grid_identifier}' updated with {len(filtered_df)} rows and {len(filtered_df.columns)} columns")
        
        # Check if grid widget exists already in VBoxGrids
        if not self.VBoxGrids.has_widget(grid_identifier):
            
            # Construct the UI for this grid using the helper function            
            new_widget = self.construct_grid_ui(grid_identifier, filter_row, grid)
            index = grid_identifier.split('_')[-1]
            self.VBoxGrids.add_widget(new_widget, index)
            logging.info(f"WidgetBox constructed for index '{index}' with grid '{grid_identifier}'")            
                  
    def create_action_toolbar(self, grid_id):
        """
        Creates an ActionToolbar instance and assigns callbacks specific to the grid_id.
        """
        action_toolbar = ActionToolbar()
        # Assign callbacks using partial to bind grid_id
        #action_toolbar.assign_callback('Solbind', partial(self.solbind_request, grid_id))
        #action_toolbar.assign_callback('Rename', partial(self.rename_fusion, grid_id))
        action_toolbar.assign_callback('Export', partial(self.save_dataframes_to_csv, grid_id))
        action_toolbar.assign_callback('Open', partial(self.open_deck, grid_id))
        action_toolbar.assign_callback('Graph', partial(self.show_graph, grid_id))
        #action_toolbar.add_button('Open', 'Open (web)', callback_function=partial(self.open_deck, grid_id))
        #action_toolbar.add_button('Graph', 'Show Graph', callback_function=partial(self.show_graph, grid_id))
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

        data_set_dropdown = widgets.Dropdown(
            options=gv.data_selection_sets.keys(),
            value=list(gv.data_selection_sets.keys())[0] if gv.data_selection_sets else None,
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
        
        if gv.out_debug: 
            with gv.out_debug:
                """Update the deck content DataFrame based on the selected item in the grid."""
                logging.info(f"DynamicGridManager::update_deck_content() - Updating deck content with event: {event}")
                if event['name'] == 'selection_changed':
                    selected_indices = event['new']
                    
                #elif event['name'] == 'filter_changed':
                    
                
                grid_df = widget.get_changed_df()            

                if grid_df is not None and selected_indices:
                    # Get the selected rows based on indices
                    selected_rows = grid_df.iloc[selected_indices]

                    # Fetch the 'collection' DataFrame
                    collection_df = self.qm.get_grid_df('collection')

                    # Initialize a list to collect all selected deck names
                    selected_deck_names = []

                    for row in selected_rows.itertuples(index=False):
                        # Find the corresponding row in the collection DataFrame
                        row_name = None
                        if not hasattr(row, 'Name') or 'Name' not in collection_df.columns:
                            logging.warning(f"Name not found in row or collection_df: {row}")
                            # Try 'name' instead of 'Name'
                            if hasattr(row, 'name') :
                                logging.info(f"Row with 'name' attribute: {row}")
                                row_name = row.name
                        else:
                            row_name = row.Name

                        logging.info(f"Row name: {row_name}")
                        # Locate the matching row in collection_df
                        collection_row = collection_df.loc[collection_df['Name'] == row_name]

                        if not collection_row.empty:
                            item_type = collection_row['type'].values[0]

                            if item_type.lower() == 'fusion':
                                # If it's a fusion, add both Deck A and Deck B names
                                if 'Deck A' in collection_row.columns and 'Deck B' in collection_row.columns:
                                    selected_deck_names.extend([collection_row['Deck A'].values[0], collection_row['Deck B'].values[0]])
                            elif item_type.lower() == 'deck':
                                # If it's a deck, add the Name
                                selected_deck_names.append(collection_row['Name'].values[0])

                    # Remove any duplicates in the selected deck names
                    selected_deck_names = list(set(selected_deck_names))
                                    
                    # Generate the deck content DataFrame using the provided function
                    deck_content_df = self.data_generate_functions['deck_content'](selected_deck_names)
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
    def open_deck(self, grid_id, button):
        
        if not grid_id in self.grid_widget_states or not 'Selection' in self.grid_widget_states[grid_id]: 
            logging.warning(f"No selection found for grid_id '{grid_id}', skipping...")
            return
        
        selected_items_list = self.grid_widget_states[grid_id]['Selection']

        # Get the rows from the central dataframe based on the selected names
        central_df = self.qm.get_grid_df('collection').copy()

        for item in selected_items_list:
            # Get the row corresponding to the selected item
            item_row = central_df[central_df['Name'] == item]
            
            if not item_row.empty:
                # Convert the single-row DataFrame to a dictionary
                item_dict = item_row.to_dict(orient='records')[0]

                # Access 'id' and 'type' directly from the dictionary
                item_id = item_dict['id']
                item_type = item_dict['type']

                # Determine the correct URL path based on the item type
                if item_type == 'Fusion':
                    item_type = 'fused'
                elif item_type == 'Deck':
                    item_type = 'decks'

                # Create the link and open it in the web browser
                item_link = f'https://solforgefusion.com/{item_type}/{item_id}'
                webbrowser.open(item_link)
            else:
                print(f"Item '{item}' not found in the central dataframe.")

    def show_graph(self, grid_id, button):
        selected_items_list = self.grid_widget_states[grid_id]['Selection']        
        display_graph(selected_items_list)    

    def authenticate(self, widget):
        if gv.myDB:
            username = gv.myDB.get_current_db_name()  
            password = widget.value  # Get the password from the text box
            net_api = gv.NetApi
            net_api.authenticate(username, password)
        
    # # Function for making a solbind request
    # def solbind_request(self, grid_id):
        
    #     selected_items_info = self.grid_widget_states[grid_id]['Selection']
    #     password = text_box.value  # Get the password from the text box
        
    #     # Here, handle multiple selected items if needed
    #     if ',' in selected_items_info:
    #         print("Multiple items selected, please select only one deck.")
    #         return
    #     deck_name = selected_items_info  # Assuming single selection
    #     deck_data = gv.myDB.find_one('Deck', {'name': deck_name})
    #     if deck_data:
    #         deck_id = deck_data.get('id')
        
    #     # Proceed with the solbind request using NetApi
    #     net_api = NetApi(username, password)
    #     net_api.post_solbind_request(deck_id)

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