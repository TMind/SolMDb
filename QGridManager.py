from datetime import datetime
import pandas as pd
import qgrid
import ipywidgets as widgets
from IPython.display import display, clear_output
from icecream import ic

import GlobalVariables as gv


class QGridManager:
    """
    Manages multiple qgrid widgets, allowing for dynamic interactions and updates
    across related grids.
    """
    
    EVENT_DF_STATUS_CHANGED = 'df_status_changed'

    def __init__(self, main_output):
        """
        Initializes a new instance of the QGridManager class.
        """
        self.grids = {}
        self.callbacks = {}
        self.relationships = {}
        self.outputs = {}
        self.main_output = main_output        

    def register_callback(self, event_name, callback, identifier=None):
        """
        Registers a callback function that will be triggered for the given event.

        Args:
            event_name (str): The name of the event.
            callback (function): The callback function to register.
            identifier (str, optional): The grid identifier. If None, the callback is registered for all grids.
        """
        if identifier is None:
            for grid_id in self.grids:
                self._register_callback_for_identifier(grid_id, event_name, callback)
        else:
            self._register_callback_for_identifier(identifier, event_name, callback)

    def _register_callback_for_identifier(self, identifier, event_name, callback):
        """
        Helper function to register a callback for a specific grid identifier.

        Args:
            identifier (str): The grid identifier.
            event_name (str): The name of the event.
            callback (function): The callback function to register.
        """
        self.callbacks.setdefault(identifier, {}).setdefault(event_name, []).append(callback)

    def trigger(self, event_name, *args, **kwargs):
        """
        Triggers callbacks associated with the specified event.

        Args:
            event_name (str): The event to trigger.
        """
        for identifier in self.callbacks:
            for callback in self.callbacks[identifier].get(event_name, []):
                callback(*args, **kwargs)

    def add_grid(self, identifier, df, options=None, dependent_identifiers=None):
        if options is None:
            options = {}
        if dependent_identifiers is None:
            dependent_identifiers = []

        grid_widget = qgrid.show_grid(
            df,
            column_options=options.get('col_options', {}),
            column_definitions=options.get('col_defs', {}),
            grid_options={'forceFitColumns': False, 'enableColumnReorder': True},
            show_toolbar=False
        )

        toggle_df = pd.DataFrame([True] * len(df.columns), index=df.columns, columns=['Visible']).T
        toggle_grid = qgrid.show_grid(toggle_df, show_toolbar=False, grid_options={'forceFitColumns': False, 'filterable': False, 'sortable': False})
        toggle_grid.layout = widgets.Layout(height='65px')

        output = widgets.Output()        
        self.grids[identifier] = {
            'main_widget': grid_widget,
            'toggle_widget': toggle_grid,
            'grid_options': options,
            'df_versions': {'default': df.copy(), 'filtered': pd.DataFrame(), 'changed': pd.DataFrame()},
            'df_status': {'current': 'default', 'last_set': {'default': datetime.now(), 'filtered': None, 'changed': None}}
        }
        self.relationships[identifier] = dependent_identifiers
        self.outputs[identifier] = output

        #print(f"Grid {identifier} added successfully.")
        # Ensure the new grid's output is displayed
        #self.display_grid(identifier)

        # Display the output widget in the main output
        #print(f"add_grid()::Appending Output on main_output for grid: {identifier}")
        self.main_output.append_display_data(output)

    def replace_grid(self, identifier, new_df):
        print(f"replace_grid() called for identifier: {identifier}")
        grid_info = self.grids.get(identifier)
        output = self.outputs.get(identifier)        

        if grid_info and output:
            print("replace_grid()::Updating grid:", identifier)
            new_main_grid = qgrid.show_grid(
                new_df,
                column_options=grid_info['grid_options'].get('col_options', {}),
                column_definitions=grid_info['grid_options'].get('col_defs', {}),
                grid_options={'forceFitColumns': False, 'enableColumnReorder': True},
                show_toolbar=False
            )

            new_toggle_df = pd.DataFrame([[True] * len(new_df.columns)], columns=new_df.columns)
            new_toggle_grid = qgrid.show_grid(new_toggle_df, show_toolbar=False, grid_options={'forceFitColumns': True, 'filterable': False, 'sortable': False})
            new_toggle_grid.layout = widgets.Layout(height='65px')

            grid_info['main_widget'] = new_main_grid
            grid_info['toggle_widget'] = new_toggle_grid
            grid_info['df_versions']['default'] = new_df.copy()
            grid_info['df_versions']['filtered'] = pd.DataFrame()
            grid_info['df_versions']['changed'] = pd.DataFrame()
            grid_info['df_status']['current'] = 'default'
            grid_info['df_status']['last_set']['default'] = datetime.now()

            #print(f"replace_grid()::New main grid: ...")  # Debug info
            #print(f"replace_grid()::New toggle grid: ...")  # Debug info

            self.display_grid(identifier)
#        else:           
            #print(f"replace_grid()::Grid identifier {identifier} or output widget not found.")

    def display_grid(self, identifier):
        output = self.outputs.get(identifier)
        grid_info = self.grids.get(identifier)
        if grid_info and output:
            #print(f"display_grid()::Displaying grid for identifier: {identifier}")
            with output:
                #print(f"display_grid()::Displaying grid for identifier: {identifier}")
                clear_output(wait=True)
                display(widgets.VBox([grid_info['toggle_widget'], grid_info['main_widget']]))
        else:
            print(f"display_grid()::Grid identifier {identifier} or output widget not found.")


    def get_default_data(self, identifier):
        """
        Returns the default version of the DataFrame for the specified grid.

        Args:
            identifier (str): The grid identifier.

        Returns:
            pandas.DataFrame: The default dataframe.
        """
        return self.grids.get(identifier, {}).get('df_versions', {}).get('default')

    def set_default_data(self, identifier, new_data):
        """
        Sets the default DataFrame for the specified grid.

        Args:
            identifier (str): The grid identifier.
            new_data (pandas.DataFrame): The new default dataframe.
        """
        grid_info = self.grids.get(identifier)
        if grid_info:
            grid_info['df_versions']['default'] = new_data.copy()
            grid_info['main_widget'].df = new_data
            toggle_df = pd.DataFrame([True] * len(new_data.columns), index=new_data.columns, columns=['Visible']).T
            grid_info['toggle_widget'].df = toggle_df
            grid_info['df_status']['current'] = 'default'
            grid_info['df_status']['last_set']['default'] = datetime.now()
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid_info['df_status'])

    def update_toggle_df(self, df, identifier):
        """
        Updates the toggle DataFrame for the specified grid based on the new DataFrame.

        Args:
            df (pandas.DataFrame): The new DataFrame.
            identifier (str): The grid identifier.
        """
        grid_info = self.grids.get(identifier)
        if grid_info:
            new_toggle_df = pd.DataFrame({col: [True] for col in df.columns}, index=['Visible'])
            current_toggle_df = grid_info['toggle_widget'].get_changed_df()
            grid_info['toggle_widget'].df = new_toggle_df
            for column in current_toggle_df.columns:
                if column in new_toggle_df.columns:
                    # Check if the value in the cell needs to be updated
                    if current_toggle_df.loc['Visible', column] != new_toggle_df.loc['Visible', column]:
                        grid_info['toggle_widget'].edit_cell('Visible', column, current_toggle_df.loc['Visible', column])
                else:
                    new_toggle_df[column] = False
                    # Check if the value in the cell needs to be updated
                    if False != grid_info['toggle_widget'].get_changed_df().loc['Visible', column]:
                        grid_info['toggle_widget'].edit_cell('Visible', column, False)

    def update_visible_columns(self, event, widget):
        """
        Updates the visibility of columns based on user interactions with the toggle grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The grid widget.
        """
        zero_width_columns = [col for col in widget.get_changed_df().columns if not widget.get_changed_df()[col].ne('').any()]
        if zero_width_columns:
            for grid_id, grid_info in self.grids.items():
                if grid_info['main_widget'] == widget:
                    toggle_grid = grid_info['toggle_widget']
                    for column in toggle_grid.df.columns:
                        toggle_grid.df[column] = column in widget.df.columns
                    toggle_grid.df = toggle_grid.df
            widget.df = widget.df.drop(columns=zero_width_columns, errors='ignore')

    def synchronize_widgets(self, master_identifier):
        """
        Synchronizes the dependent widgets with the master widget based on filtered data.

        Args:
            master_identifier (str): The identifier of the master widget.
        """
        master_widget = self.grids[master_identifier]['main_widget']
        master_df = master_widget.get_changed_df()
        for dependent_identifier in self.relationships[master_identifier]:
            dependent_df = self.grids[dependent_identifier]['df_versions']['default']
            filtered_df = dependent_df[dependent_df.index.isin(master_df.index)]
            dependent_widget = self.grids[dependent_identifier]['main_widget']
            dependent_widget.df = filtered_df
            self.grids[dependent_identifier]['df_versions']['filtered'] = filtered_df
            self.update_visible_columns(None, dependent_widget)

    def on(self, identifier, event_name, handler_func):
        """
        Adds an event listener to a grid widget.

        Args:
            identifier (str): The grid identifier.
            event_name (str): The name of the event.
            handler_func (function): The handler function to execute when the event is triggered.
        """
        grid_info = self.grids.get(identifier)
        if grid_info:
            grid_info['main_widget'].on(event_name, handler_func)

    def _setup_grid_events(self, identifier, grid_widget, toggle_grid):
        """
        Sets up the necessary events for the grid widgets.

        Args:
            identifier (str): The grid identifier.
            grid_widget (qgrid.QGridWidget): The main grid widget.
            toggle_grid (qgrid.QGridWidget): The toggle grid widget.
        """
        def on_toggle_change(event, qgrid_widget):
            toggled_df = toggle_grid.get_changed_df()
            visible_columns = [col for col in toggled_df.columns if toggled_df.loc['Visible', col]]
            grid_info = self.grids[identifier]
            if grid_info:
                df_versions = grid_info['df_versions']
            #     if not df_versions['changed'].empty:
            #         grid_widget.df = df_versions['changed'][visible_columns].copy()
                if not df_versions['filtered'].empty:
                    grid_widget.df = df_versions['filtered'][visible_columns].copy()
                else:
                    grid_widget.df = df_versions['default'][visible_columns].copy()

                grid_info['df_status']['current'] = 'filtered'
                grid_info['df_status']['last_set']['filtered'] = datetime.now()
                self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid_info['df_status'])

        def on_filter_change(event, qgrid_widget):
            changed_df = grid_widget.get_changed_df()
            self.grids[identifier]['df_versions']['changed'] = changed_df.copy()
            self.update_toggle_df(changed_df, identifier)
            grid_info = self.grids[identifier]
            grid_info['df_status']['current'] = 'changed'
            grid_info['df_status']['last_set']['changed'] = datetime.now()
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid_info['df_status'])

        toggle_grid.on('cell_edited', on_toggle_change)
        grid_widget.on('filter_changed', on_filter_change)
        grid_widget.on('filter_changed', self.update_visible_columns)

class FilterGrid:
    """
    Manages the grid for filtering data based on user-defined criteria.
    """
    def __init__(self, update_decks_display):
        """
        Initializes a new instance of the FilterGrid class.

        Args:
            update_decks_display (function): The function to call when the filter grid is updated.
        """
        self.update_decks_display = update_decks_display
        self.df = self.create_initial_dataframe()
        self.qgrid_filter = self.create_filter_qgrid()
        self.selection_box, self.selection_widgets = self.create_selection_box()

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
        qgrid_filter.on('cell_edited', self.on_cell_edit)
        return qgrid_filter

    @staticmethod
    def create_initial_dataframe():
        """
        Creates the initial dataframe for the filter grid.

        Returns:
            pandas.DataFrame: The initial dataframe.
        """
        return pd.DataFrame({
            'Modifier': [''],
            'op1': [''],
            'Creature': [''],
            'op2': [''],
            'Spell': [''],
            'Active': [False]
        })

    def grid_filter_on_row_removed(self, event, widget):
        """
        Handles the 'row_removed' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        if 0 in event['indices']:
            df = self.create_initial_dataframe()
            widget.df = pd.concat([df, widget.get_changed_df()], ignore_index=True)
            event['indices'].remove(0)
        if event['indices']:
            active_rows = widget.df[widget.df['Active'] == True]
            self.update_decks_display({'new': active_rows, 'old': None, 'owner': 'filter'})

    def grid_filter_on_row_added(self, event, widget):
        """
        Handles the 'row_added' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        new_row_index = event['index']
        df = widget.get_changed_df()

        # Set the values for each column in the new row
        for column in df.columns:
            if column in ['op1', 'op2', 'Active']:  # Directly use the value for these fields
                df.at[new_row_index, column] = self.selection_widgets[column].value
            else:  # Assume these are multi-select fields and join their values
                df.at[new_row_index, column] = ', '.join(self.selection_widgets[column].value)
        
        widget.df = df

        if widget.df.loc[new_row_index, 'Active']:
            self.update_decks_display({'new': new_row_index, 'old': None, 'owner': 'filter'})

    def on_cell_edit(self, event, widget):
        """
        Handles the 'cell_edited' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        row_index, column_index = event['index'], event['column']
        widget.df.loc[row_index, column_index] = event['new']
        if widget.df.loc[row_index, 'Active']:
            self.update_decks_display({'new': row_index, 'old': None, 'owner': 'filter'})

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

    def create_cardType_names_selector(self, cardType):
        """
        Creates a selector for the names of card types.

        Args:
            cardType (str): The type of card.

        Returns:
            ipywidgets.SelectMultiple: The selector widget.
        """
        cardType_entity_names = [''] + get_cardType_entity_names(cardType)
        cardType_name_widget = widgets.SelectMultiple(
            options=cardType_entity_names,
            description='',
            value=()
        )
        return cardType_name_widget

    def create_selection_box(self):
        """
        Creates a selection box containing widgets for each card type.

        Returns:
            tuple: A tuple containing the selection box widget and a dictionary of individual selection widgets.
        """
        selection_widgets = {}
        selection_items = {}
        for cardType in ['Modifier', 'Creature', 'Spell']:
            widget = self.create_cardType_names_selector(cardType)
            if cardType == 'Modifier':
                label=widgets.Label(value='( Modifier')
            elif cardType == 'Spell':
                label=widgets.Label(value='Spell )')
            else:                
                label = widgets.Label(value=f'{cardType}')
            selection_widgets[cardType] = widget
            selection_items[cardType] = widgets.VBox([label, widget], layout=widgets.Layout(align_items='center'))

        operator_widgets = {
            'op1': widgets.Dropdown(options=['+', 'AND', 'OR', ''], description='', layout=widgets.Layout(width='60px'), value='OR'),
            'op2': widgets.Dropdown(options=['AND', 'OR', ''], description='', layout=widgets.Layout(width='60px'), value='OR'),
            'Active': widgets.Checkbox(value=True, description='Activated')
        }
        for name, widget in operator_widgets.items():
            label = widgets.Label(value='Operator' if 'op' in name else 'Active')
            selection_widgets[name] = widget
            selection_items[name] = widgets.VBox([label, widget], layout=widgets.Layout(align_items='center'))

        selection_box = widgets.HBox([selection_items[name] for name in ['Modifier', 'op1', 'Creature', 'op2', 'Spell', 'Active']])
        return selection_box, selection_widgets

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
    cardType_entities = gv.commonDB.find('Entity', {"attributes.cardType": cardType})
    cardType_entities_names = [entity['name'] for entity in cardType_entities]
    cards = gv.myDB.find('Card', {})
    cardNames = [card.get('title', card.get('name', '')) for card in cards]
    cardType_entities_names = [name for name in cardType_entities_names if any(name in cardName for cardName in cardNames)]
    cardType_entities_names.sort()
    return cardType_entities_names
