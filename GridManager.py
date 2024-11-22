import os
from datetime import datetime
from gc import enable
from unittest.mock import DEFAULT
from click import option
from matplotlib.pyplot import grid
from numpy import isin
import pandas as pd
from qgridnext import QgridWidget

from CardLibrary import ForgebornAbility
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


DEFAULT_FILTER =  pd.DataFrame({
            'Type': ['Deck', 'Deck'],
            'Name': ['','' ],
            'Modifier': ['',''],
            'Creature': ['',''],
            'Spell': ['',''],            
            'Forgeborn Ability': ['',''],
            'Active': [True,True],
            'Mandatory Fields': ['Name, Forgeborn Ability','Name, Forgeborn Ability']
        })
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

    def add_grid(self, identifier, df, options=None, grid_type='qgrid', rebuild=False):
        """Add or update a grid to the GridManager."""
        if identifier in self.grids and not rebuild:
            grid = self.grids[identifier]
            self.set_default_data(identifier, df)
            
        else:
            grid = QGrid(identifier, pd.DataFrame(), options) if grid_type == 'qgrid' else print("Not QGrid Type!")
            if grid:
                self.grids[identifier] = grid        
                self._setup_grid_events(identifier, grid)            
                
        self.update_dataframe(identifier, df)
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
        return None


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
            grid.update_main_widget(new_df)
            self.update_visible_columns(None, grid.main_widget)
            grid.update_sum_column()
            
            self.css_manager.apply_conditional_class(grid.main_widget, rotate_suffix, self.custom_css_class)                        
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

    def synchronize_widgets(self, master_identifier):
        master_grid = self.grids[master_identifier]
        master_df = master_grid.main_widget.get_changed_df()
        for dependent_identifier in self.relationships[master_identifier]:
            dependent_grid = self.grids[dependent_identifier]
            dependent_df = dependent_grid.df_versions['default']
            filtered_df = dependent_df[dependent_df.index.isin(master_df.index)]
            print(f"Synchronizing {dependent_identifier} with {master_identifier}")
            #self.replace_grid(dependent_identifier, filtered_df)

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

        grid.toggle_widget.on('cell_edited', on_toggle_change)
        if isinstance(grid, QGrid):
            grid.main_widget.on('filter_changed', on_filter_change)

        self.reapply_callbacks(identifier)

    def _setup_sorting_events(self, identifier, grid):
        """
        Set up sorting events for the grid using the SortingManager.
        """
        def on_sort_change(event):
            """
            This function is triggered when a sort change event is detected. 
            It will invoke the SortingManager to handle the sorting and update the grid accordingly.
            """
            sorted_df = self.sorting_manager.handle_sort_changed( event, grid.main_widget.df)

            # Re-update the grid with the newly sorted DataFrame
            self.update_dataframe(identifier, sorted_df)
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid.df_status)

        # Register the sorting event
        grid.main_widget.on('sort_changed', on_sort_change)
        with self.debug_output:
            print(f"Sorting enabled for grid {identifier}.")


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

    def update_sum_column(self):
        df = self.main_widget.get_changed_df()
        if gv.rotated_column_definitions:
            # Get the list of columns to sum, ensuring they exist in the DataFrame
            columns_to_sum = [col for col in gv.rotated_column_definitions.keys() if col in df.columns]
            if columns_to_sum:
                # Ensure the columns to sum are numeric; replace non-numeric with NaN
                numeric_df = df[columns_to_sum].apply(pd.to_numeric, errors='coerce')

                # Calculate the sum for each row across the rotated columns
                df['Sum'] = numeric_df.sum(axis=1)

                # Fill the NaN values in the DataFrame with empty strings
                df.fillna('', inplace=True)
                self.update_main_widget(df)

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
        
    def update_main_widget(self, new_df):        
        self.main_widget.df = new_df
        self.set_dataframe_version('filtered', new_df)

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

from MyWidgets import EnhancedSelectMultiple
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

        active_rows = widget.df[widget.df['Active'] == True]
        
        self.refresh_function({'new': active_rows, 'old': None, 'owner': 'filter'})
                

    def grid_filter_on_row_added(self, event, widget):
        """
        Handles the 'row_added' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        if gv.out_debug:
            with gv.out_debug:
                print(f"FilterClass::grid_filter_on_row_added() - Adding new row to filter grid")
                
                new_row_index = event['index']
                df = widget.get_changed_df()

                mandatory_fields = []

                # Set the values for each column in the new row
                for column in df.columns:
                    if column in self.selection_widgets:
                        widget_value = self.selection_widgets[column].value

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

                self.refresh_function({'new': new_row_index, 'old': None, 'owner': 'filter'})

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
        #if column_index == 'Active' or widget.df.loc[row_index, 'Active']:
        self.refresh_function({'new': row_index, 'old': None, 'owner': 'filter'})

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
                    print(f"Field '{first_item}' not found in DataFrame")
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

                    regex = fr'\b{re.escape(string_item)}(?=[^\w\s]|\s|$)'  # Match word boundaries but allow space as part of the match

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
            print(f"apply_filter: {matched_count} rows matched for first_target '{first_target}' and second_target '{second_target}' with first_operator '{first_operator}' and second_operator '{second_operator}'")
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


# Function to create a styled HTML widget with a background color
def create_styled_html(text, text_color, bg_color, border_color):
    html = widgets.HTML(
        value=f"<div style='padding:10px; color:{text_color}; background-color:{bg_color};"
            f" border:solid 2px {border_color}; border-radius:5px;'>"
            f"<strong>{text}</strong></div>"
    )
    return html

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
    
        # GridSpecLayout
        self.rows = 1
        self.columns = 1    
        self.grid_layout = widgets.GridspecLayout(self.rows, self.columns)        

        # UI elements
        self.selectionGrid, self.filterGrid = self.filterGridObject.get_widgets()
        self.ui = widgets.VBox([])
    
        self.update_grid_layout(self.rows)        
        
        # Register observer for DataSelectionManager
        DataSelectionManager.register_observer(self.update_grids)

    def update_grids(self, event, widget):
        self.refresh_gridbox(rebuild = True)        

    def reset_grid_layout(self, new_size):           
        #print(f"Resetting grid layout to size {new_size} : {self.grid_layout}")            
        self.grid_layout = widgets.GridspecLayout(new_size or 1, 1)
        self.grid_widget_states = {}        
        self.update_ui()

    # def update_grid_layout(self):
    #     filter_df = self.filterGridObject.get_changed_df()
    #     active_filters_count = len(filter_df[filter_df['Active']]) or 1
    #     new_grid = widgets.GridspecLayout(active_filters_count, 1)
    #     for idx, child in enumerate(self.grid_layout.children):
    #         if idx < active_filters_count:
    #             new_grid[idx, 0] = child
    #     self.grid_layout = new_grid
    #     self.update_ui()
        
        
    def update_grid_layout(self, active_filters_count = 1):
        """
        Updates the GridspecLayout based on active filters.
        """
        try:
            # Retrieve the latest filter DataFrame
            #filter_df = self.filterGridObject.qgrid_filter.get_changed_df()
            
            # Validate the presence of the 'Active' column
            #if 'Active' not in filter_df.columns:
            #    raise ValueError("The filter DataFrame must contain an 'Active' column.")
            
            # Determine the number of active filters; default to 1 if none are active
            #active_filters_count = filter_df['Active'].sum()
            active_filters_count = active_filters_count if active_filters_count > 0 else 1
            
            # Check if the grid needs to be resized
            if active_filters_count != self.rows:
                # Create a new GridspecLayout with updated rows, preserving columns
                new_grid = widgets.GridspecLayout(
                    active_filters_count,
                    self.columns,
                    height=self.grid_layout.layout.height,
                    width=self.grid_layout.layout.width
                )
                
                # Reassign existing children to the new grid
                for idx in range(min(active_filters_count, self.rows)):
                    for col in range(self.columns):
                        child_idx = idx * self.columns + col
                        if child_idx < len(self.grid_layout.children):
                            new_grid[idx, col] = self.grid_layout.children[child_idx]
                
                # **Update the stored row count**
                self.rows = active_filters_count
                
                # Update the UI by replacing the old grid with the new grid
                self.ui.children = [new_grid]
                
                # Replace the old grid with the new grid
                self.grid_layout = new_grid
                
                print(f"Grid layout updated to {self.rows} rows and {self.columns} columns.")
            else:
                print("Grid layout size remains unchanged.")
            
            # Refresh or re-render additional UI components if necessary
            self.update_ui()
        
        except Exception as e:
            print(f"Error updating grid layout: {e}")

    def apply_filters(self, df, widget_states):
        # Filter columns based on the filter_row
        info_level = widget_states['info_level']
        data_set = widget_states['data_set']
        filter_row = widget_states['filter_row']
        filtered_df = apply_filter_to_dataframe(df, pd.DataFrame([filter_row]))        
        return self.determine_columns(filtered_df, info_level, data_set, filter_row['Type'])
        
    def determine_columns(self, df, info_level, data_set, item_type):
        
        data_set_columns = FieldUnifier.generate_final_fields(info_level, data_set, item_type)        
        existing_columns = [col for col in data_set_columns if col in df.columns]
        filtered_df = df.loc[:, existing_columns]    
        
        return filtered_df
        
    def updateFilterGridObject(self, event, widget):
        """
        Update the filter grid object when a cell is edited.

        Args:
            event (dict): The event data that contains details about the edit.
            widget: The widget where the event occurred.
        """
        # Extract row index, column name, and new value from the event data
        row_index = event['index']
        column_name = event['column']
        new_value = event['new']

        # Get the current filter DataFrame from the filter grid object
        filter_df = self.filterGridObject.qgrid_filter.get_changed_df()

        # Check if the row index and column name are valid in the filter DataFrame
        if row_index in filter_df.index and column_name in filter_df.columns:
            # Update the DataFrame with the new value
            filter_df.at[row_index, column_name] = new_value

            # Sync the changes back to the filterGridObject's DataFrame
            self.filterGridObject.qgrid_filter.df = filter_df

            # Debugging output to verify the update
            print(f"Updated filter grid: row {row_index}, column '{column_name}' set to '{new_value}'")
            grid_identifier = f"filtered_grid_{row_index}"
            self.grid_widget_states[grid_identifier]['filter_row'] = filter_df.loc[row_index].to_dict()
            self.refresh_grid_using_toolbar_and_filter(f"filtered_grid_{row_index}")


    def refresh_gridbox(self, change=None, rebuild = False):
        #print(f"DynamicGridManager::refresh_gridbox() - Refreshing grid box with change: {change}")        
        collection_df = self.qm.get_default_data('collection')
        if collection_df.empty or (change and 'type' in change and (change['type'] == 'username' or change['type'] == 'generation')):            
            collection_df = self.data_generate_functions['central_dataframe']()
            self.qm.add_grid('collection', collection_df, options=self.qg_options)            
        
        # Filter the DataFrame to include only active filters
        filter_df = self.filterGridObject.get_changed_df()
        active_filters_df = filter_df[filter_df['Active']]
        #print(f"{len(active_filters_df)} Active Filters: {active_filters_df} ")

        #print(f"Number of active filters: {len(active_filters_df)}")
        if len(active_filters_df) != len(self.grid_layout.children) or len(active_filters_df) == 0 :
            print("Resetting grid layout")
            #self.reset_grid_layout(len(active_filters_df))
            self.update_grid_layout(len(active_filters_df))

        gv.update_progress('Gridbox', 0, len(active_filters_df), message="Refreshing Gridbox - Applying Filters")
        for index, (row_index, filter_row) in enumerate(active_filters_df.iterrows()):            
            
            grid_identifier = f"filtered_grid_{index}"                
            
            # Check if this grid needs to be updated based on recent changes
            grid_state = self.grid_widget_states.get(grid_identifier, {})
            filter_changed = grid_state.get('filter_row') != filter_row.to_dict()
            
            if filter_changed or rebuild:            
            #if filter_row['Active']:
                gv.update_progress("Gridbox", message = f"Applying filter {index+1}/{len(active_filters_df)} {filter_row['Type']} {filter_row['Modifier']} {filter_row['Creature']} {filter_row['Spell']} {filter_row['Forgeborn Ability']}")
                
                # Update stored state                
                grid_state = {
                    "info_level": grid_state.get("info_level", 'Basic'),
                    "data_set": grid_state.get("data_set", 'Stats'),
                    "filter_row": filter_row.to_dict()  # Store the current filter row state
                }   
                self.grid_widget_states[grid_identifier] = grid_state
                #grid_state = self.grid_widget_states.get(grid_identifier)
                #grid = self.qm.grids.get(grid_identifier)
                            
                #filtered_df = self.apply_filters(collection_df, self.grid_widget_states[grid_identifier])
                filtered_df = self.apply_filters(collection_df, grid_state)
                #self.qm.update_dataframe(grid_identifier, filtered_df) 
  
                # Update or create the grid
                grid = self.qm.add_grid(grid_identifier, filtered_df, options=self.qg_options, rebuild=rebuild)                

                # Register the selection event callback for the grid
                self.qm.on(grid_identifier, 'selection_changed', self.update_deck_content)

                # Set up the layout for this grid
                toolbar_widget = self.create_toolbar(grid_identifier)
                filter_row_widget = qgrid.show_grid(pd.DataFrame([filter_row]), show_toolbar=False,
                                                    grid_options={'forceFitColumns': True, 'filterable': False, 'sortable': False, 'editable': True})
                filter_row_widget.layout = widgets.Layout(height='70px')
                
                #filter_row_widget.on('row_added', self.refresh_gridbox())
                #filter_row_widget.on('row_removed', self.filterGridObject.grid_filter_on_row_removed)
                filter_row_widget.on('cell_edited', self.updateFilterGridObject)  
                
                 # Add filter row observer
                def on_filter_row_change(event, qgrid_widget=filter_row_widget):
                    self.refresh_grid_using_toolbar_and_filter(grid_identifier)

                filter_row_widget.on('cell_edited', on_filter_row_change)

                # Update the overall layout
                self.grid_layout[index, 0] = widgets.VBox([toolbar_widget, filter_row_widget, grid.get_grid_box()],
                                                          layout=widgets.Layout(border='2px solid black'))

        self.update_ui()

    def create_action_toolbar(self, grid_id):
        """
        Creates an ActionToolbar instance and assigns callbacks specific to the grid_id.
        """
        action_toolbar = ActionToolbar()
        # Assign callbacks using partial to bind grid_id
        #action_toolbar.assign_callback('Solbind', partial(self.solbind_request, grid_id))
        #action_toolbar.assign_callback('Rename', partial(self.rename_fusion, grid_id))
        action_toolbar.assign_callback('Export', partial(self.save_dataframes_to_csv, grid_id))
        action_toolbar.add_button('Open', 'Open (web)', callback_function=partial(self.open_deck, grid_id))
        action_toolbar.add_button('Graph', 'Show Graph', callback_function=partial(self.show_graph, grid_id))
        return action_toolbar.get_ui()

    def create_toolbar(self, grid_identifier):
        # Create and setup toolbar widgets with observer functions
        info_level_button = widgets.ToggleButtons(
            options=['Basic', 'Detail'],
            value='Basic',
            description='Info Level:',
            button_style='info',
            layout=widgets.Layout(width='30%', height='25px', display='flex', flex_flow='row', align_items='center')
        )

        spacer = widgets.Box(layout=widgets.Layout(flex='1'))

        data_set_dropdown = widgets.Dropdown(
            options=gv.data_selection_sets.keys(),
            value=list(gv.data_selection_sets.keys())[0] if gv.data_selection_sets else None,
            description='Data Set:',
            layout=widgets.Layout(width='25%', align_self='flex-end')
        )

        def on_info_level_change(change):
            if change['type'] == 'change' and change['name'] == 'value':
                # Update state and refresh grid
                self.grid_widget_states[grid_identifier]['info_level'] = change['new']
                self.refresh_grid_using_toolbar_and_filter(grid_identifier)

        def on_data_set_change(change):
            if change['type'] == 'change' and change['name'] == 'value':
                # Update state and refresh grid
                self.grid_widget_states[grid_identifier]['data_set'] = change['new']
                self.refresh_grid_using_toolbar_and_filter(grid_identifier)

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


    def refresh_grid_using_toolbar_and_filter(self, grid_identifier):
        # Retrieve current state for this grid
        grid_state = self.grid_widget_states.get(grid_identifier)
        if not grid_state:
            print(f"No state found for grid identifier: {grid_identifier}")
            return
        print(f"Grid state retrieved for identifier {grid_identifier}: {grid_state}")

        # Retrieve the grid to be updated
        grid = self.qm.grids.get(grid_identifier)
        if not grid:
            print(f"No grid found for grid identifier: {grid_identifier}")
            return
        print(f"Grid retrieved for identifier {grid_identifier}")

        # Retrieve and copy the default data from the collection
        collection_df = self.qm.get_default_data('collection')
        print(f"Default collection DataFrame retrieved with {len(collection_df)} rows and {len(collection_df.columns)} columns")

        # Apply the filters from the filter row first
        filtered_df = self.apply_filters(collection_df, grid_state)
        print(f"Filtered DataFrame has {len(filtered_df)} rows after applying filters")

        # Update the grid with the filtered DataFrame
        self.qm.update_dataframe(grid_identifier, filtered_df)
        print(f"Grid {grid_identifier} updated with filtered data")
                  
            

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
        with self.out_debug:
            """Update the deck content DataFrame based on the selected item in the grid."""
            print(f"DynamicGridManager::update_deck_content() - Updating deck content with event: {event}")
            selected_indices = event['new']
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
                        print(f"Name not found in row or collection_df: {row}")
                        # Try 'name' instead of 'Name'
                        if hasattr(row, 'name') :
                            print(f"Row with 'name' attribute: {row}")
                            row_name = row.name
                    else:
                        row_name = row.Name

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

                # Update the UI
                self.update_ui()
                self.data_generate_functions['update_selection_area']()
            
    def update_ui(self):
        """Helper method to update the self.ui.children with the common layout."""
        #self.ui.children = []
        new_children =  [widget for widget in [
            self.selectionGrid, 
            filter_grid_bar, 
            self.filterGrid, 
            filter_results_bar, 
            self.grid_layout, 
            deck_content_bar,
            self.deck_content_Grid.get_grid_box()
        ] if widget is not None]
        #print(f"New UI children: {[type(child) for child in new_children]}") 
        self.ui.children = new_children

    def get_ui(self):
        return self.ui
    
    def get_selected_grid_items(self):
        """
        Retrieves the currently selected 'Name' items from all main_qgrid_widgets within the GridspecLayout.
        
        Returns:
            dict: A dictionary where keys are grid_ids and values are lists of selected 'Name' items.
        """
        selected_items = {}
        
        # Iterate over all rows and columns in the grid_layout
        for row in range(self.rows):
            for col in range(self.columns):
                cell = self.grid_layout[row, col]
                
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
                                    print(f"Selected names for grid_id '{grid_id}': {selected_names}")
                                else:
                                    print(f"No selected items in grid_id '{grid_id}' or 'Name' column missing.")
                            else:
                                print(f"No matching grid_id found for main_qgrid_widget ID {id(main_qgrid_widget)}.")
                    else:
                        print(f"Skipping cell [{row}, {col}] as inner_vbox does not contain enough children.")
                else:
                    print(f"Skipping cell [{row}, {col}] as it does not contain a valid VBox with at least 3 children.")
        
        print(f"\nFinal selected_items: {selected_items}")
        
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
                    print(f"Saved DataFrame '{identifier}' to {csv_filename}")
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
        for index, widget_box in enumerate(self.grid_layout.children):
            # Check if the widget is a VBox containing the grid
            if isinstance(widget_box, widgets.VBox) and len(widget_box.children) > 1:
                grid_widget_box = widget_box.children[1]  # The grid widget is typically the second child in the VBox
                grid_widget = grid_widget_box.children[1]  # Access the actual grid widget

                # Find the corresponding grid in the GridManager
                for grid_id, grid in self.qm.grids.items():
                    if grid.main_widget == grid_widget:
                        df_to_disk(grid.main_widget)
        with self.out_debug:
            print(f"All applicable DataFrames saved to {directory}:")
            
    # Function to open the selected deck in the browser
    def open_deck(self, grid_id, button):
        
        if not grid_id in self.grid_widget_states or not 'Selection' in self.grid_widget_states[grid_id]: 
            print(f"No selection found for grid_id '{grid_id}', skipping...")
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
        