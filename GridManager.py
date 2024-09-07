from datetime import datetime
from email import header
import pandas as pd
import qgrid
import ipywidgets as widgets
from GlobalVariables import global_vars as gv

from DataSelectionManager import DataSelectionManager
from MongoDB.DatabaseManager import DatabaseManager

# module global variables 

class GridManager:
    EVENT_DF_STATUS_CHANGED = 'df_status_changed'

    def __init__(self, debug_output):
        self.grids = {}
        self.callbacks = {}
        self.qgrid_callbacks = {}
        self.relationships = {}
        self.debug_output = debug_output

    def add_grid(self, identifier, df, options=None, dependent_identifiers=None, grid_type='qgrid'):
        """Add or update a grid to the GridManager."""
        if dependent_identifiers is None:
            dependent_identifiers = []

        if identifier in self.grids:
            # Grid exists, update DataFrame
            grid = self.grids[identifier]
            self.set_default_data(identifier, df)
            self.update_dataframe(identifier, df)  # Ensure grid object has a method to update its DataFrame
            with self.debug_output:
                print(f"GridManager::add_grid() - Grid {identifier} updated.")
        else:
            # Create a new grid
            grid = QGrid(identifier, df, options) if grid_type == 'qgrid' else print("Not QGrid Type!") #PandasGrid(identifier, df, options)
            self.grids[identifier] = grid
            self.relationships[identifier] = dependent_identifiers
            self._setup_grid_events(identifier, grid)
            with self.debug_output:
                print(f"GridManager::add_grid() - Grid {identifier} added.")
        
        return grid
        
    def get_grid_df(self, identifier, version='default'):
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
            self.synchronize_widgets(identifier)
            grid.df_status['current'] = 'changed'
            grid.df_status['last_set']['changed'] = datetime.now()
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid.df_status)

        grid.toggle_widget.on('cell_edited', on_toggle_change)
        if isinstance(grid, QGrid):
            grid.main_widget.on('filter_changed', on_filter_change)

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
        self.grid_options = options if options else {}
        self.main_widget = None
        self.toggle_widget = self.create_toggle_widget(df)
        self.create_main_widget(df)

    def create_main_widget(self, df):
        raise NotImplementedError("Subclasses should implement this method.")

    def create_toggle_widget(self, df):
        toggle_df = pd.DataFrame([True] * len(df.columns), index=df.columns, columns=['Visible']).T
        toggle_grid = qgrid.show_grid(toggle_df, show_toolbar=False, grid_options={'forceFitColumns': False, 'filterable': False, 'sortable': False})
        toggle_grid.layout = widgets.Layout(height='65px')
        return toggle_grid

    def get_grid_box(self):
        return widgets.VBox([self.toggle_widget, self.main_widget])

    def update_main_widget(self, new_df):
        raise NotImplementedError("Subclasses should implement this method.")

    def set_dataframe_version(self, version, df):
        self.df_versions[version] = df
        self.df_status['current'] = 'filtered'
        self.df_status['last_set']['filtered'] = datetime.now()

    def reset_dataframe(self):
        self.df_versions['default'] = pd.DataFrame()
        self.update_main_widget(self.df_versions['default'])

class QGrid(BaseGrid):
    def create_main_widget(self, df):
        print(f"QGrid::create_main_widget() - Creating QGrid -> column_definitions = {self.grid_options.get('column_definitions', {})}")
        self.main_widget = qgrid.show_grid(
            df,
            column_options=self.grid_options.get('column_options', {}),
            column_definitions=self.grid_options.get('column_definitions', {}),
            grid_options={'forceFitColumns': False, 'enableColumnReorder': True},
            show_toolbar=False
        )
        self.main_widget.add_class('qgrid-custom-css')
        #apply_rotation_css_to_qgrid(self.main_widget, 12, header_height=150, custom_class='qgrid-rotated-header')

    def update_main_widget(self, new_df):
        self.main_widget.df = new_df
        self.set_dataframe_version('filtered', new_df)

class PandasGrid(BaseGrid):
    def create_main_widget(self, df):
        self.update_main_widget(df)

    def update_main_widget(self, new_df):
        self.df_versions['default'] = new_df.copy()
        self.set_dataframe_version('filtered', new_df)


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
        self.selection_box, self.selection_widgets = self.create_selection_box()
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
        return pd.DataFrame({
            'Type': ['Deck'],
            'Modifier': [''],
            'op1': [''],
            'Creature': [''],
            'op2': [''],
            'Spell': [''],            
            'Forgeborn Ability': [''],
            'Data Set': ['Deck Stats'],
            'Active': [True],
        })

    def grid_filter_on_row_removed(self, event, widget):
        """
        Handles the 'row_removed' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        if gv.out_debug:
            with gv.out_debug:
                print(f"FilterClass::grid_filter_on_row_removed() - Removing row {event['index']} from filter grid")
        active_rows = []
        if 0 in event['indices']:
            df = pd.DataFrame({
                'Type': [''],
                'Modifier': [''],
                'op1': [''],
                'Creature': [''],
                'op2': [''],
                'Spell': [''],            
                'Forgeborn Ability': [''],
                'Data Set': [''],
                'Active': [False],
            })
            widget.df = pd.concat([df, widget.get_changed_df()], ignore_index=True)
            event['indices'].remove(0)
        
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

        #print(f"Adding new row at index {new_row_index} with values: {event}")

        # Set the values for each column in the new row
        for column in df.columns:
            if column in ['Type', 'op1', 'op2', 'Data Set']:  # Directly use the value for these fields
                df.at[new_row_index, column] = self.selection_widgets[column].value
            elif column == 'Active':  # Assume these are multi-select fields and join their values
                df.at[new_row_index, 'Active'] = True
            elif column == 'Forgeborn Ability':
                fb_ability_list = self.selection_widgets[column].value
                fb_ability_list = [fb_ability.split(' : ')[1] for fb_ability in fb_ability_list]
                df.at[new_row_index, column] = ';'.join(fb_ability_list)
            else:
                df.at[new_row_index, column] = '; '.join(self.selection_widgets[column].value)

        widget.df = df

        self.refresh_function({'new': new_row_index, 'old': None, 'owner': 'filter'})

    def grid_filter_on_cell_edit(self, event, widget):
        """
        Handles the 'cell_edited' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        if gv.out_debug:
            with gv.out_debug:
                print(f"FilterClass::grid_filter_on_cell_edit() - Editing cell in filter grid")
        row_index, column_index = event['index'], event['column']
        widget.df.loc[row_index, column_index] = event['new']
        
        widget.df = widget.df
        #Print the edited row from the widget
        if gv.out_debug:
            with gv.out_debug:
                print(f"Edited row: {widget.df.loc[row_index]}")
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

    def create_cardType_names_selector(self, cardType, options=None):
        """
        Creates a selector for the names of card types.

        Args:
            cardType (str): The type of card.

        Returns:
            ipywidgets.SelectMultiple: The selector widget.
        """
        if options is None:
            options = {}
        cardType_entity_names = [''] + get_cardType_entity_names(cardType)
        cardType_name_widget = widgets.SelectMultiple(
            options=cardType_entity_names,
            description='',
            layout=widgets.Layout(width='200px', height='auto', align_items='center', justify_content='center', **options)
        )
        return cardType_name_widget

    def create_selection_box(self):
        # Define widgets with their layout settings
        widgets_dict = {
            'Type': widgets.Dropdown(
                options=['Deck', 'Fusion'],
                description='',
                layout=widgets.Layout(width='100px', border='1px solid cyan', align_items='center', justify_content='center')
            ),
            'Modifier': self.create_cardType_names_selector('Modifier', options={'border': '1px solid blue'}),
            'op1': widgets.Dropdown(options=['', 'AND', 'OR', '+'], description='', layout=widgets.Layout(width='75px', border='1px solid purple', align_items='center', justify_content='center', margin='5px')),
            'Creature': self.create_cardType_names_selector('Creature', options={'border': '1px solid green'}),
            'op2': widgets.Dropdown(options=['', 'AND', 'OR'], description='', layout=widgets.Layout(width='75px', border='1px solid purple', align_items='center', justify_content='center')),
            'Spell': self.create_cardType_names_selector('Spell', options={'border': '1px solid red'}),            
            'Forgeborn Ability': widgets.SelectMultiple(options=[''] + get_forgeborn_abilities(), description='', layout=widgets.Layout(width='300px', border='1px solid orange', align_items='center', justify_content='center')),
            'Data Set': widgets.Dropdown(
                options=gv.data_selection_sets.keys(),
                description='',
                layout=widgets.Layout(width='150px', border='1px solid purple', align_items='center', justify_content='center')
            ),
        }

        # Create widget row first and add a fixed-width spacer
        widget_row_items = [widgets_dict[key] for key in widgets_dict]
        fixed_spacer = widgets.Box(layout=widgets.Layout(width='50px'))  # Fixed-width spacer
        widget_row_items.append(fixed_spacer)

        widget_row = widgets.HBox(widget_row_items, layout=widgets.Layout(display='flex', flex_flow='row nowrap', width='100%', ))

        # Creating label row using the same layout settings from widget_row
        label_items = [widgets.Label(key, layout=widgets_dict[key].layout) for key in widgets_dict]
        label_fixed_spacer = widgets.Label('', layout=widgets.Layout(width='50px'))
        label_items.append(label_fixed_spacer)

        label_row = widgets.HBox(label_items, layout=widgets.Layout(display='flex', flex_flow='row nowrap', width='100%'))

        # Vertical box to hold both rows
        selection_box = widgets.VBox([label_row, widget_row])

        return selection_box, widgets_dict

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
def apply_cardname_filter_to_dataframe(df_to_filter, filter_df, update_progress=None):

    def filter_by_substring(df, filter_row):    
        def apply_filter(df, substrings, filter_fields=['cardTitles'], apply_operator='OR'):
            if not substrings or not filter_fields:
                return df

            if apply_operator == 'AND':
                # Create a boolean mask initialized to True for "AND" logic
                mask = pd.Series([True] * len(df), index=df.index)
                for substring in substrings:
                    # Create a temporary mask for each substring
                    temp_mask = pd.Series([False] * len(df), index=df.index)
                    for field in filter_fields:
                        if field in df.columns:
                            # If the substring is found in any of the field‚s, update the temp_mask
                            temp_mask |= df[field].apply(lambda title: substring.lower() in str(title).lower())
                    # Update the main mask with the temp_mask using AND logic
                    mask &= temp_mask
            else:
                # Create a boolean mask initialized to False for "OR" logic
                mask = pd.Series([False] * len(df), index=df.index)
                for field in filter_fields:
                    if field in df.columns:
                        for substring in substrings:
                            mask |= df[field].apply(lambda title: substring.lower() in str(title).lower())

            # Filter the DataFrame using the boolean mask
            current_filter_results = df[mask].copy()

            return current_filter_results   

        def determine_operator_and_substrings(string): 
            and_symbols = {
                ':': r'\s*:\s*',
                '&': r'\s*&\s*',
                '+': r'\s*\+\s*'
            }            
            or_symbols = {
                '|': r'\s*\|\s*',
                '-': r'\s*-\s*'             
            }
            
            for symbol, pattern in and_symbols.items():
                if symbol in string:
                    #print(f"Found AND symbol '{symbol}' in '{string}'")
                    return 'AND', re.split(pattern, string)
            
            for symbol, pattern in or_symbols.items():
                if symbol in string:
                    #print(f"Found OR symbol '{symbol}' in '{string}'")
                    return 'OR', re.split(pattern, string)
            
            #print(f"Falling back on standard '{string}'")
            return 'OR', re.split(r'\s*;\s*', string)                                                   


        # Apply the first filter outside the loop
        df_filtered = df_to_filter
        #substrings = re.split(r'\s*;\s*', filter_row['Modifier']) if filter_row['Modifier'] else []
        apply_operator, substrings = determine_operator_and_substrings(filter_row['Modifier']) if filter_row['Modifier'] else ('OR', [])
        if substrings:
            df_filtered = apply_filter(df, substrings)

        # Apply the remaining filters in the loop
        for i, filter_type in enumerate(['Creature', 'Spell', 'Forgeborn Ability', 'Type'], start=1):
            operator = ''
            if f'op{i}' in filter_row:
                operator = filter_row[f'op{i}']
            
            filter_fields = ['cardTitles'] 
            if filter_type == 'Forgeborn Ability': 
                filter_fields = ['FB2', 'FB3', 'FB4'] 
                operator = 'AND'            

            if filter_type == 'Type':
                filter_fields = ['type']
                operator = 'AND'

            previous_substrings = substrings
            # Determine if we should use AND or OR logic based on the operator            
            apply_operator, substrings = determine_operator_and_substrings(filter_row[filter_type]) if filter_row[filter_type] else ("",[])
            #substrings = re.split(r'\s*;\s*', filter_row[filter_type]) if filter_row[filter_type] else []
            #print(f"Substrings = '{substrings}'")            
            
            if operator == '+':                
                substrings = [f"{s1} {s2}" for s1 in previous_substrings for s2 in substrings]
            
            # If previous_substrings is empty treat the operator as ''
            if not previous_substrings:
                operator = ''

            # If substrings is empty, skip this iteration
            if not substrings:
                substrings = previous_substrings
                continue

            # Apply the filter to the DataFrame
            current_filter_results = apply_filter(df, substrings, filter_fields, apply_operator=apply_operator)

            # Handle the operator logic in the outer loop
            if operator == 'AND':
                df_filtered = df_filtered[df_filtered.index.isin(current_filter_results.index)]
            elif operator == 'OR' :
                df_filtered = pd.concat([df_filtered, current_filter_results]).drop_duplicates()
            elif operator == '+' or operator == '':
                df_filtered = current_filter_results
            else:
                print(f"Operator '{operator}' not recognized")

        return df_filtered

    df_filtered = df_to_filter
    active_filters = filter_df[filter_df['Active'] == True]  # Get only the active filters

    for _, filter_row in active_filters.iterrows():
        df_filtered = filter_by_substring(df_filtered, filter_row)

    return df_filtered

from MultiIndexDataFrame import MultiIndexDataFrame

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

class DynamicGridManager:

    def __init__(self, data_generate_functions, qg_options, out_debug):
        self.out_debug = out_debug       
        self.data_generate_functions = data_generate_functions
        self.qg_options = qg_options
        self.qm = GridManager(out_debug)
        self.grid_layout = widgets.GridspecLayout(1, 1)        
        self.filterGridObject = FilterGrid(self.refresh_gridbox)
        self.deck_content_grid = qgrid.show_grid(pd.DataFrame(), show_toolbar=False, grid_options={'forceFitColumns': False, 'filterable': True, 'sortable': True})

        # UI elements
        self.selectionGrid, self.filterGrid = self.filterGridObject.get_widgets()
        #self.ui = widgets.VBox([self.selectionGrid, filter_grid_bar, self.filterGrid, filter_results_bar, self.grid_layout, deck_content_bar])
        self.ui = widgets.VBox([])
        self.update_ui()
        self.update_grid_layout()

    def reset_grid_layout(self, new_size):
        self.ui.children = [self.selectionGrid, self.filterGrid] 
        self.grid_layout = widgets.GridspecLayout(new_size, 1)
        #print(f"Resetting grid layout to size {new_size} : {self.grid_layout}")
        self.update_ui()

    def update_grid_layout(self):
        filter_df = self.filterGridObject.get_changed_df()
        active_filters_count = len(filter_df[filter_df['Active']])
        new_grid = widgets.GridspecLayout(active_filters_count, 1)
        for idx, child in enumerate(self.grid_layout.children):
            if idx < active_filters_count:
                new_grid[idx, 0] = child
        self.grid_layout = new_grid
        self.update_ui()

    def apply_filters(self, df, filter_row):
        # Filter columns based on the data_selection_list, remove all values not in the list                
        filtered_df = apply_cardname_filter_to_dataframe(df, pd.DataFrame([filter_row]))
        data_set_type = filter_row['Data Set']
        existing_columns = [col for col in gv.data_selection_sets[data_set_type] if col in filtered_df.columns]
        filtered_df = filtered_df.loc[:, existing_columns]    
        
        return filtered_df            
        

    def refresh_gridbox(self, change=None):
        #print(f"DynamicGridManager::refresh_gridbox() - Refreshing grid box with change: {change}")
        gv.update_progress('Gridbox', 0, message="Refreshing Gridbox")
        collection_df = self.qm.get_default_data('collection')
        if collection_df.empty or (change and 'type' in change and (change['type'] == 'username' or change['type'] == 'generation')):            
            collection_df = self.data_generate_functions['central_dataframe']()
            self.qm.add_grid('collection', collection_df, options=self.qg_options)            
        
        # Filter the DataFrame to include only active filters
        filter_df = self.filterGridObject.get_changed_df()
        active_filters_df = filter_df[filter_df['Active']]
        #print(f"{len(active_filters_df)} Active Filters: {active_filters_df} ")
        self.reset_grid_layout(len(active_filters_df))

        gv.update_progress('Gridbox', 0, len(active_filters_df), "Refreshing Gridbox - Applying Filters")
        for index, (row_index, filter_row) in enumerate(active_filters_df.iterrows()):            
            if filter_row['Active']:
                gv.update_progress("Gridbox", message = f"Applying filter {index+1}/{len(active_filters_df)} {filter_row['Type']} {filter_row['Modifier']} {filter_row['Creature']} {filter_row['Spell']} {filter_row['Forgeborn Ability']} {filter_row['Data Set']}")
                filtered_df = self.apply_filters(collection_df, filter_row)

                filter_widget = None
                grid_widget  = None 

                grid_identifier = f"filtered_grid_{index}"
                grid = self.qm.add_grid(grid_identifier, filtered_df, options=self.qg_options)
                
                # Register selection event callback using GridManager's register_callback
                with self.out_debug:
                    print(f"Registering selection_changed callback for grid {grid_identifier}")
                self.qm.on(grid_identifier, 'selection_changed', self.update_deck_content)
                self.qm.display_registered_events()

                filter_row_widget = qgrid.show_grid(pd.DataFrame([filter_row]), show_toolbar=False, grid_options={'forceFitColumns': True, 'filterable': False, 'sortable': False, 'editable': False})
                filter_row_widget.layout = widgets.Layout(height='70px') #, border='1px solid blue')

                filter_widget = filter_row_widget
                grid_widget = grid.get_grid_box()
                
                self.grid_layout[index, 0] = widgets.VBox([filter_widget, grid_widget], layout=widgets.Layout(border='2px solid black'))
        
        # After updating, reassign children to trigger update
        #print(f"Refresh Gridbox. Layout = {self.grid_layout}")
        self.update_ui()

    def update_deck_content(self, event, widget):
        """Update the deck content DataFrame based on the selected item in the grid."""
        selected_indices = event['new']
        grid_df = widget.get_changed_df()            

        if grid_df is not None and selected_indices:
            # Get the selected rows based on indices
            selected_rows = grid_df.iloc[selected_indices]

            # Fetch the 'collection' DataFrame
            collection_df = self.qm.get_default_data('collection')

            # Initialize a list to collect all selected deck names
            selected_deck_names = []

            for _, row in selected_rows.iterrows():
                # Find the corresponding row in the collection DataFrame
                collection_row = collection_df.loc[collection_df['Name'] == row['Name']]

                if not collection_row.empty:
                    item_type = collection_row['type'].values[0]

                    if item_type.lower() == 'fusion':
                        # If it's a fusion, add both Deck A and Deck B names
                        if 'Deck A' in collection_row and 'Deck B' in collection_row:
                            selected_deck_names.extend([collection_row['Deck A'].values[0], collection_row['Deck B'].values[0]])
                    elif item_type.lower() == 'deck':
                        # If it's a deck, add the Name
                        selected_deck_names.append(collection_row['Name'].values[0])

            # Remove any duplicates in the selected deck names
            selected_deck_names = list(set(selected_deck_names))
                            
            # Generate the deck content DataFrame using the provided function
            deck_content_df = self.data_generate_functions['deck_content'](selected_deck_names)

            # Create a new grid for the deck content and update the UI
            self.deck_content_grid = qgrid.show_grid(
                deck_content_df,
                show_toolbar=False,
                column_definitions=gv.all_column_definitions,
                grid_options={'forceFitColumns': False, 'filterable': True, 'sortable': True}
            )
            #apply_rotation_css_to_qgrid(self.deck_content_grid, 7, header_height=150)
            #apply_rotation_css_to_columns(self.deck_content_grid, gv.rotated_column_definitions.keys() ,header_height=150)
                            
            # Update the UI
            self.update_ui()

    def update_ui(self):
        """Helper method to update the self.ui.children with the common layout."""
        self.ui.children = [
            self.selectionGrid, 
            filter_grid_bar, 
            self.filterGrid, 
            filter_results_bar, 
            self.grid_layout, 
            deck_content_bar,
            self.deck_content_grid
        ]

    def get_ui(self):
        return self.ui


