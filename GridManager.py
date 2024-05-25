from datetime import datetime
import pandas as pd
import qgrid
import ipywidgets as widgets
from IPython.display import display, clear_output

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

        if grid_type == 'qgrid':
            grid = QGrid(identifier, df, options)
        else:
            grid = PandasGrid(identifier, df, options)

        self.grids[identifier] = grid
        self.relationships[identifier] = dependent_identifiers
        self.outputs[identifier] = widgets.Output()

        self._setup_grid_events(identifier, grid)
        #print(f"GridManager::add_grid() - Grid {identifier} added. Appending to main_output.")
        self.main_output.append_display_data(self.outputs[identifier])

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
        grid = self.grids.get(identifier)
        output = self.outputs.get(identifier)

        if grid and output:
            grid.update_main_widget(new_df)
            self.display_grid(identifier)
            self.synchronize_widgets(identifier)
            #if isinstance(grid, QGrid):
            #    self.update_visible_columns(None, grid.main_widget)

    def display_grid(self, identifier):
            output = self.outputs.get(identifier)
            grid = self.grids.get(identifier)
            if grid and output:
                with output:
                    clear_output(wait=True)
                    if isinstance(grid, QGrid):
                        #print(f"display_grid()::Rendering QGrid for {identifier}")
                        display(widgets.VBox([grid.toggle_widget, grid.main_widget]))
                    else:
                        #print(f"display_grid()::Rendering PandasGrid for {identifier}")
                        grid.render_main_widget()  # Render within the main widget context
            else:
                print(f"display_grid()::Grid identifier {identifier} or output widget not found.")

    def reset_dataframe(self, identifier):
        grid = self.grids.get(identifier)
        if grid:
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
            print(f"Zero width columns: {zero_width_columns}")
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
            self.replace_grid(dependent_identifier, filtered_df)

    def _setup_grid_events(self, identifier, grid):
        def on_toggle_change(event, qgrid_widget):
            toggled_df = grid.toggle_widget.get_changed_df()
            if 'Visible' in toggled_df.index:
                visible_columns = [col for col in toggled_df.columns if toggled_df.loc['Visible', col]]
            else:
                print("'Visible' index does not exist in toggled_df")

            df_versions = grid.df_versions
            if not df_versions['filtered'].empty:
                grid.main_widget.df = df_versions['filtered'][visible_columns].copy()
            else:
                grid.main_widget.df = df_versions['default'][visible_columns].copy()

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
            if identifier not in self.qgrid_callbacks:
                self.qgrid_callbacks[identifier] = {}
            self.qgrid_callbacks[identifier].setdefault(event_name, []).append(callback)

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

    def create_main_widget(self, df):
        raise NotImplementedError("Subclasses should implement this method.")

    def create_toggle_widget(self, df):
        toggle_df = pd.DataFrame([True] * len(df.columns), index=df.columns, columns=['Visible']).T
        toggle_grid = qgrid.show_grid(toggle_df, show_toolbar=False, grid_options={'forceFitColumns': True, 'filterable': False, 'sortable': False})
        toggle_grid.layout = widgets.Layout(height='65px')
        return toggle_grid

    def update_main_widget(self, new_df):
        raise NotImplementedError("Subclasses should implement this method.")

    def set_dataframe_version(self, version, df):
        """
        Set a DataFrame for a specific version.

        Parameters:
        version (str): The version key for the DataFrame.
        df (pd.DataFrame): The DataFrame to set.
        """
        self.df_versions[version] = df
        self.df_status['current'] = 'filtered'
        self.df_status['last_set']['filtered'] = datetime.now()

    def reset_dataframe(self):
        self.df_versions['default'] = pd.DataFrame()
        self.update_main_widget(self.df_versions['default'])


class QGrid(BaseGrid):
    def create_main_widget(self, df):
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
        #print("PandasGrid::update_main_widget() - Clearing Output")
        self.df_versions['default'] = new_df.copy()
        self.set_dataframe_version('filtered', new_df)        

    def render_main_widget(self):
        #print("PandasGrid::render_main_widget() - Displaying DataFrame pure")
        display(self.df_versions['default'])
