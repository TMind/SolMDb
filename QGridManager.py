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
        self.qgrid_callbacks = {}
        self.relationships = {}
        self.outputs = {'debug' : widgets.Output()}  
        self.main_output = main_output        
        #display(self.outputs['debug'])
        #with self.outputs['debug']:
        #    print("QGridManager::__init__()::Debug output widget initialized.")

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

    def on(self, identifier, event_name, callback):
        """
        Adds an event listener to a grid widget.

        Args:
            identifier (str): The grid identifier.
            event_name (str): The name of the event.
            callback (function): The callback function to execute when the event is triggered.
        """
        grid_info = self.grids.get(identifier)
        if grid_info:
            #print(f"on()::Adding event listener for identifier: {identifier} and event: {event_name}")
            grid_info['main_widget'].on(event_name, callback)

            # Store the callback in qgrid_callbacks
            if identifier not in self.qgrid_callbacks:
                self.qgrid_callbacks[identifier] = {}
            self.qgrid_callbacks[identifier].setdefault(event_name, []).append(callback)


    def reapply_callbacks(self, identifier):
            """
            Reapplies all callbacks to a grid widget.

            Args:
                identifier (str): The grid identifier.
            """
            grid_info = self.grids.get(identifier)
            if grid_info:
                # Reapply callbacks registered via register_callback()
                if identifier in self.callbacks:
                    for event_name, callbacks in self.callbacks[identifier].items():
                        for callback in callbacks:
                            #print(f"reapply_callbacks()::Reapplying callback for identifier: {identifier} and event: {event_name}")
                            grid_info['main_widget'].on(event_name, callback)

                # Reapply callbacks passed to qgrid.on()
                if identifier in self.qgrid_callbacks:
                    for event_name, callbacks in self.qgrid_callbacks[identifier].items():
                        for callback in callbacks:
                            #print(f"reapply_callbacks()::Reapplying qgrid.on() callback for identifier: {identifier} and event: {event_name}")
                            grid_info['main_widget'].on(event_name, callback)

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

        # Set up the grid events
        self._setup_grid_events(identifier, grid_widget, toggle_grid)
        
        # Display the output widget in the main output
        #print(f"add_grid()::Appending Output on main_output for grid: {identifier}")
        self.main_output.append_display_data(output)

    def replace_grid(self, identifier, new_df):
        #print(f"replace_grid() called for identifier: {identifier}")
        grid_info = self.grids.get(identifier)
        output = self.outputs.get(identifier)        

        if grid_info and output:
            #print("replace_grid()::Updating grid:", identifier)

            # Close the old widgets and turn off their event handlers
            grid_info['main_widget'].off('filter_changed', None)
            grid_info['toggle_widget'].off('cell_edited', None)
            grid_info['main_widget'].close()
            grid_info['toggle_widget'].close()

            new_main_grid = qgrid.show_grid(
                pd.DataFrame(),
                column_options=grid_info['grid_options'].get('col_options', {}),
                column_definitions=grid_info['grid_options'].get('col_defs', {}),
                grid_options={'forceFitColumns': False, 'enableColumnReorder': True},
                show_toolbar=False
            )
            new_main_grid.df = new_df

            new_toggle_df = pd.DataFrame([True] * len(new_df.columns), index=new_df.columns, columns=['Visible']).T
            new_toggle_grid = qgrid.show_grid(new_toggle_df, show_toolbar=False, grid_options={'forceFitColumns': True, 'filterable': False, 'sortable': False})
            new_toggle_grid.layout = widgets.Layout(height='65px')

            grid_info['main_widget'] = new_main_grid
            grid_info['toggle_widget'] = new_toggle_grid
            grid_info['df_versions']['filtered'] = new_df.copy()
            grid_info['df_versions']['changed'] = new_df.copy()
            grid_info['df_status']['current'] = 'default'
            grid_info['df_status']['last_set']['default'] = datetime.now()
            
            self.update_visible_columns(None, new_main_grid)
            self._setup_grid_events(identifier, new_main_grid, new_toggle_grid)
            self.display_grid(identifier)                        
            self.synchronize_widgets(identifier)

    def reset_dataframe(self, identifier):
        grid_info = self.grids.get(identifier)
        if grid_info:
            grid_info['main_widget'].df = pd.DataFrame()

    def display_grid(self, identifier):
        output = self.outputs.get(identifier)
        grid_info = self.grids.get(identifier)
        if grid_info and output:
            #print(f"display_grid()::Displaying grid for identifier: {identifier}")
            #print(grid_info['main_widget'].df.head())
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
            
            old_toggle_df = grid_info['toggle_widget'].get_changed_df()            
            
            for column in old_toggle_df.columns:
                if column in df.columns:
                    # Check if the value in the cell needs to be updated 
                    if (column in df.columns) != old_toggle_df.loc['Visible', column]:
                        #print(f"update_toggle_df()::Editing cell for column: {column} with value {df.loc['Visible', column]}")
                        grid_info['toggle_widget'].edit_cell('Visible', column, df.loc['Visible', column])                
                else:
                    #print(f"update_toggle_df()::Adding column: {column} to toggle grid with value False")
                    grid_info['toggle_widget'].df[column] = False
                    # Check if the value in the cell needs to be updated                    
                    if False != grid_info['toggle_widget'].get_changed_df().loc['Visible', column]:
                        #print(f"update_toggle_df()::Editing cell for column: {column} with value False")
                        grid_info['toggle_widget'].edit_cell('Visible', column, False)


    def update_visible_columns(self, event, widget):
        """
        Updates the visibility of columns based on user interactions with the toggle grid.

        Args:
            event (dict): The event data.
            widget (qgrid.QGridWidget): The grid widget.
        """
        
        #print(f"update_visible_columns() called ")        
        zero_width_columns = [col for col in widget.get_changed_df().columns if not widget.get_changed_df()[col].ne('').any()]
        #print(f"update_visible_columns()::zero_width_columns: {zero_width_columns}")
        if zero_width_columns:
            for grid_id, grid_info in self.grids.items():
                if grid_info['main_widget'] == widget:
                    #print(f"... for identifier: {grid_id}")                        
                    #print(f"update_visible_columns()::widget colums: {widget.df.columns}")
                    widget.df = widget.df.drop(columns=zero_width_columns, errors='ignore')
                    self.update_toggle_df(widget.df, grid_id)
                    
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
            #print(filtered_df.head())
            self.replace_grid(dependent_identifier, filtered_df)             


    def _setup_grid_events(self, identifier, grid_widget, toggle_grid):
       
        """
        Sets up the necessary events for the grid widgets.

        Args:
            identifier (str): The grid identifier.
            grid_widget (qgrid.QGridWidget): The main grid widget.
            toggle_grid (qgrid.QGridWidget): The toggle grid widget.
        """
        #print(f"_setup_grid_events()::Setting up events for identifier: {identifier}")
        grid_info = self.grids[identifier]

        def on_toggle_change(event, qgrid_widget):
            #with self.outputs['debug']:
            #print(f"on_toggle_change() called for identifier: {identifier}")
            toggled_df = toggle_grid.get_changed_df()
            #print(f"on_toggle_change()::toggled_df: ...")
            #display(toggled_df)
            if 'Visible' in toggled_df.index:
                visible_columns = [col for col in toggled_df.columns if toggled_df.loc['Visible', col]]
            else:
                print("'Visible' index does not exist in toggled_df")

            df_versions = grid_info['df_versions']
            #print(f"on_toggle_change()::visible_columns: {visible_columns}")
            
            #grid_widget.df = grid_widget.df[visible_columns]
            #print(f"on_toggle_change()::df: {grid_widget.df}")

            #if not df_versions['changed'].empty:
            #    grid_widget.df = df_versions['changed'][visible_columns].copy()
            if not df_versions['filtered'].empty:
                grid_widget.df = df_versions['filtered'][visible_columns].copy()
            else:
                grid_widget.df = df_versions['default'][visible_columns].copy()

            grid_info['df_status']['current'] = 'filtered'
            grid_info['df_status']['last_set']['filtered'] = datetime.now()
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid_info['df_status'])

        def on_filter_change(event, qgrid_widget):
            #print(f"on_filter_change() called for identifier: {identifier}")
            changed_df = grid_widget.get_changed_df()
            self.grids[identifier]['df_versions']['changed'] = changed_df.copy()
            self.update_visible_columns(event, grid_widget)
            self.update_toggle_df(changed_df, identifier)  
            self.synchronize_widgets(identifier)              
            grid_info = self.grids[identifier]
            grid_info['df_status']['current'] = 'changed'
            grid_info['df_status']['last_set']['changed'] = datetime.now()
            self.trigger(self.EVENT_DF_STATUS_CHANGED, identifier, grid_info['df_status'])

        toggle_grid.on('cell_edited', on_toggle_change)
        grid_widget.on('filter_changed', on_filter_change)
        
        # Reapply additional callbacks
        self.reapply_callbacks(identifier)

