from ctypes import alignment
from datetime import datetime
import pandas as pd
import qgrid
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import GlobalVariables as gv

# Simplified GridManager implementation
class GridManager:
    EVENT_DF_STATUS_CHANGED = 'df_status_changed'

    def __init__(self, main_output):
        self.grids = {}
        self.callbacks = {}
        self.qgrid_callbacks = {}
        self.relationships = {}
        self.outputs = {'debug': widgets.Output()}
        self.main_output = main_output

    def add_grid(self, identifier, df, options=None, dependent_identifiers=None, grid_type='qgrid'):
        if dependent_identifiers is None:
            dependent_identifiers = []

        grid = QGrid(identifier, df, options) if grid_type == 'qgrid' else PandasGrid(identifier, df, options)
        self.grids[identifier] = grid
        self.relationships[identifier] = dependent_identifiers
        self.outputs[identifier] = widgets.Output()

        self._setup_grid_events(identifier, grid)
        with self.outputs['debug']:
            print(f"GridManager::add_grid() - Grid {identifier} added. Appending to main_output.")        
        self.outputs[identifier].append_display_data(grid.get_grid_box())            
        self.main_output.append_display_data(self.outputs[identifier])
        return grid.get_grid_box()
        

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
        print(f"GridManager::replace_grid() - Replacing grid {identifier} with new DataFrame")
        grid = self.grids.get(identifier)
        if grid:
            grid.update_main_widget(new_df)
            return grid.get_grid_box()

    def redraw_all_grids(self):
        """Clears and redraws all grids in the main_output."""
        #self.main_output.clear_output(wait=True)  # Clear the output to prevent flickering
        for identifier, grid in self.grids.items():
            #self.outputs[identifier].clear_output()
            #self.outputs[identifier].append_display_data(grid.get_grid_box())
            self.main_output.append_display_data(self.outputs[identifier])
    
    def reset_dataframe(self, identifier):
        grid = self.grids.get(identifier)
        if grid:
            print(f"GridManager::reset_dataframe() - Resetting DataFrame for {identifier}")
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
        return None

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
        zero_width_columns = [col for col in current_df.columns if not current_df[col].ne('').any()]
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
        self.progress_bar = widgets.IntProgress(min=0, max=100)  # Create progress bar
        self.progress_label = widgets.Label('Initialised!')  # Label for progress bar

    def create_main_widget(self, df):
        raise NotImplementedError("Subclasses should implement this method.")

    def create_toggle_widget(self, df):
        toggle_df = pd.DataFrame([True] * len(df.columns), index=df.columns, columns=['Visible']).T
        toggle_grid = qgrid.show_grid(toggle_df, show_toolbar=False, grid_options={'forceFitColumns': True, 'filterable': False, 'sortable': False})
        toggle_grid.layout = widgets.Layout(height='65px')
        return toggle_grid

    def get_grid_box(self):
        # Add the progress bar and label to an HBox to position them nicely
        progress_container = widgets.HBox([self.progress_label, self.progress_bar])
        # Return a VBox with the toggle widget, the main widget, and the progress bar
        return widgets.VBox([self.toggle_widget, self.main_widget, progress_container])

    def update_progress(self, value, description=None):
        self.progress_bar.value = value
        if description:         
            self.progress_label.value = description

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
        #print("QGrid::create_main_widget() - Creating QGrid")
        self.main_widget = qgrid.show_grid(
            df,
            column_options=self.grid_options.get('col_options', {}),
            column_definitions=self.grid_options.get('col_defs', {}),
            grid_options={'forceFitColumns': False, 'enableColumnReorder': True},
            show_toolbar=False
        )

    def update_main_widget(self, new_df):
        self.main_widget.df = new_df
        self.set_dataframe_version('filtered', new_df)


class PandasGrid(BaseGrid):
    def create_main_widget(self, df):
        self.update_main_widget(df)

    def update_main_widget(self, new_df):
        self.df_versions['default'] = new_df.copy()
        self.set_dataframe_version('filtered', new_df)

    def render_main_widget(self):
        display(self.df_versions['default'])



class FilterGrid:
    """
    Manages the grid for filtering data based on user-defined criteria.
    """
    def __init__(self, function_refresh, functions_data_generation):
        """
        Initializes a new instance of the FilterGrid class.

        Args:
            update_decks_display (function): The function to call when the filter grid is updated.
        """
        self.refresh_function = function_refresh
        self.data_generation_functions = functions_data_generation
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
            'Data Function': 'Deck Stats',
            'Active': [True]
        })

    def grid_filter_on_row_removed(self, event, widget):
        """
        Handles the 'row_removed' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        active_rows = []
        if 0 in event['indices']:
            df = self.create_initial_dataframe()
            widget.df = pd.concat([df, widget.get_changed_df()], ignore_index=True)
            event['indices'].remove(0)
        
        #if event['indices']:
        active_rows = widget.df[widget.df['Active'] == True]
        
        self.refresh_function({'new': active_rows, 'old': None, 'owner': 'filter'})
        
        

    def grid_filter_on_row_added(self, event, widget):
        """
        Handles the 'row_added' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        new_row_index = event['index']
        df = widget.get_changed_df()

        #print(f"Adding new row at index {new_row_index} with values: {event}")

        # Set the values for each column in the new row
        for column in df.columns:
            if column in ['op1', 'op2', 'Active', 'Data Function']:  # Directly use the value for these fields
                df.at[new_row_index, column] = self.selection_widgets[column].value
            else:  # Assume these are multi-select fields and join their values
                df.at[new_row_index, column] = '; '.join(self.selection_widgets[column].value)
        
        widget.df = df

        #if widget.df.loc[new_row_index, 'Active']:
        self.refresh_function({'new': new_row_index, 'old': None, 'owner': 'filter'})

    def on_cell_edit(self, event, widget):
        """
        Handles the 'cell_edited' event for the filter grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The filter grid widget.
        """
        row_index, column_index = event['index'], event['column']
        widget.df.loc[row_index, column_index] = event['new']
        
        #if column_index == 'Active' or widget.df.loc[row_index, 'Active']:
        self.refresh_function({'new': row_index, 'old': None, 'owner': 'filter'})

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
            print(f"Updated selection content with {change}")
            #self.refresh_function(change)

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
            'Modifier': self.create_cardType_names_selector('Modifier', options={'border': '1px solid blue'}),
            'op1': widgets.Dropdown(options=['+', 'AND', 'OR', ''], description='', layout=widgets.Layout(width='75px', border='1px solid purple', align_items='center', justify_content='center', margin='5px')),
            'Creature': self.create_cardType_names_selector('Creature', options={'border': '1px solid green'}),
            'op2': widgets.Dropdown(options=['AND', 'OR', ''], description='', layout=widgets.Layout(width='75px', border='1px solid purple', align_items='center', justify_content='center')),
            'Spell': self.create_cardType_names_selector('Spell', options={'border': '1px solid red'}),            
            'Data Function': widgets.Dropdown(
                options=list(self.data_generation_functions.keys()),
                description='',
                layout=widgets.Layout(width='150px', border='1px solid purple', align_items='center', justify_content='center')
            ),
            'Active': widgets.Checkbox(value=True, description='', layout=widgets.Layout(width='100px', height='auto', align_items='center', justify_content='center'))  # Added label and alignment
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
    cardType_entities = gv.commonDB.find('Entity', {"attributes.cardType": cardType})
    cardType_entities_names = [entity['name'] for entity in cardType_entities]
    cards = gv.myDB.find('Card', {})
    cardNames = [card.get('title', card.get('name', '')) for card in cards]
    cardType_entities_names = [name for name in cardType_entities_names if any(name in cardName for cardName in cardNames)]
    cardType_entities_names.sort()
    return cardType_entities_names


