from multiprocessing import synchronize
from os import sync
import qgrid
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from icecream import ic

class QGridManager:
    def __init__(self):
        self.grids = {}  # Stores the grid widgets and their interactive components
        self.relationships = {}  # Stores the relationships between the grids

    def add_grid(self, identifier, df, options={}, dependent_identifiers=[]):
        """Create a qgrid widget with interactive column selection."""
        grid_widget = qgrid.show_grid(df,
                                      column_options=options.get('col_options', {}),
                                      column_definitions=options.get('col_defs', {}),
                                      grid_options={'forceFitColumns': False, 'enableColumnReorder': True},
                                      show_toolbar=False)

        # Initialize an empty toggle DataFrame for column visibility
        toggle_df = pd.DataFrame(columns=['Visible'])  # No columns initially
        toggle_grid = qgrid.show_grid(toggle_df, 
                                      show_toolbar=False, 
                                      grid_options={'forceFitColumns': True,  'filterable': False, 'sortable' : False})  # Force the grid to fit the width of its container
        toggle_grid.layout = widgets.Layout(height='65px')  # Set the height of the toggle grid

        # Function to handle changes in toggle grid
        def on_toggle_change(event, qgrid_widget):
            # Get current toggle state
            toggled_df = toggle_grid.get_changed_df()
            visible_columns = [col for col in toggled_df.columns if toggled_df.loc['Visible', col]]            

            # Use the default DataFrame to update the DataFrame in the main grid
            grid_widget.df = self.grids[identifier]['df_versions']['default'][visible_columns]

            # Update the target widgets
            # This is wrong, the dataframe shall not be changed , only adjusted 
            self.synchronize_widgets(identifier)

        def on_filter_change(event, qgrid_widget):
            # Get the changed Dataframe
            changed_df = grid_widget.get_changed_df()

            # Store the changed DataFrame
            self.grids[identifier]['df_versions']['changed'] = changed_df.copy()

            # Synchronize the dependent widgets
            self.synchronize_widgets(identifier)
        
        # to the toggle grid
        toggle_grid.on('cell_edited', on_toggle_change)

        # Attach event handlers 
        grid_widget.on('filter_changed', on_filter_change)
        grid_widget.on('filter_changed', self.update_visible_columns)

        # Store grid info
        self.grids[identifier] = {
            'main_widget': grid_widget,
            'toggle_widget': toggle_grid,
            'df_versions': {
                'default': df.copy(),
                'filtered': df.copy(),
                'changed': df.copy()
            }
        }

        # Store the relationships 
        self.relationships[identifier] = dependent_identifiers
        return grid_widget, toggle_grid

    def get_default_data(self, identifier):
        """Get the 'default' version of the DataFrame for a specified qgrid widget."""
        grid_info = self.grids.get(identifier)
        if grid_info:
            return grid_info['df_versions']['default']
        else:
            return None

    def set_default_data(self, identifier, new_data):
        """Set the 'default' version of the DataFrame for a specified qgrid widget."""
        grid_info = self.grids.get(identifier)
        if grid_info:
            grid_info['df_versions']['default'] = new_data.copy()
            # Update the main widget's DataFrame
            grid_info['main_widget'].df = new_data
            toggle_df = pd.DataFrame([True] * len(new_data.columns), index=new_data.columns, columns=['Visible']).T
            grid_info['toggle_widget'].df = toggle_df




    # Updating the DataFrame

    def update_data(self, identifier, new_data):
        """Update the data in a specified qgrid widget and adjust toggle grid accordingly."""
        grid_info = self.grids.get(identifier)
        if grid_info:
            # Update the default DataFrame
            grid_info['df_versions']['default'] = new_data.copy()
            # Update the main widget's DataFrame
            grid_info['main_widget'].df = new_data
            toggle_df = pd.DataFrame([True] * len(new_data.columns), index=new_data.columns, columns=['Visible']).T
            grid_info['toggle_widget'].df = toggle_df


    # Visibility of columns / Dropping columns

    def update_visible_columns(self, event, widget):
        ic('Updating visible columns', widget)
        zero_width_columns = []   

        # Function to check if any value in the column is not an empty string with regards to the changed_df of the qgrid widget
        def check_column_values(column, changed_df):
            # Check if the column exists in the DataFrame
            if column in changed_df.columns:  return changed_df[column].ne('').any()      
            else:                             return False

        # Analyze changed DataFrame for updates
        changed_df = widget.get_changed_df()
        for column in changed_df.columns:  
            # Check if column values are not just empty strings
            if not check_column_values(column, changed_df):
                zero_width_columns.append(column)
                changed_df.drop(column, axis=1, inplace=True)

        # Update the toggle grid
        ic('Zero width columns', zero_width_columns)
        if len(zero_width_columns) > 0:            
            for grid_id, grid_info in self.grids.items():
                ic('Is it grid?', grid_id)
                if grid_info['main_widget'] == widget:
                    ic('It is grid' , grid_id)
                    toggle_grid = grid_info['toggle_widget']
                    for column in toggle_grid.df.columns:
                        ic('Checking',column)
                        toggle_grid.df[column] = column in changed_df.columns
                        ic(toggle_grid.df[column])
                    # Update the toggle widget
                    toggle_grid.df = toggle_grid.df    
            
            widget.df = changed_df

    def display_grid_with_controls(self, identifier):
        """Display the qgrid widget with its column selectors."""
        grid_info = self.grids.get(identifier)
        if grid_info:
            display(widgets.VBox([grid_info['toggle_widget'], grid_info['main_widget']]))


    # Updating dependent widgets 

    def synchronize_widgets(self, master_identifier):
        ic('Synchronizing widgets', master_identifier)
        # Get the DataFrame from the master widget
        master_widget = self.grids[master_identifier]['main_widget']
        master_df = master_widget.get_changed_df()

        # Update the DataFrame in the dependent widgets
        for dependent_identifier in self.relationships[master_identifier]:
            # Start with the 'default' version of the DataFrame
            dependent_df = self.grids[dependent_identifier]['df_versions']['default']

            # Filter the DataFrame based on the index of the master widget
            filtered_df = dependent_df[dependent_df.index.isin(master_df.index)]

            # Set the filtered DataFrame as the DataFrame of the dependent widget
            dependent_widget = self.grids[dependent_identifier]['main_widget']
            dependent_widget.df = filtered_df

            # Update the 'filtered' version of the DataFrame
            self.grids[dependent_identifier]['df_versions']['filtered'] = filtered_df.copy()

            # Update the visible columns of the dependent grid
            self.update_visible_columns(None, dependent_widget)

    def apply_external_filter(self, widget_identifier, condition):
        # Always filter from the default to ensure full data set is considered
        default_df = self.grids[widget_identifier]['df_versions']['default']
        filtered_df = default_df[condition(default_df)]
        self.grids[widget_identifier]['df_versions']['filtered'] = filtered_df.copy()
        widget = self.grids[widget_identifier]['main_widget']
        widget.df = filtered_df




    def on(self, identifier, event_name, handler_func):
        """Add an event listener to a qgrid widget."""
        grid_info = self.grids.get(identifier)
        if grid_info and 'main_widget' in grid_info:
            grid_info['main_widget'].on(event_name, handler_func)



