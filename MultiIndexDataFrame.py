import pandas as pd
import qgridnext as qgrid
from IPython.display import display, clear_output
import ipywidgets as widgets

class MultiIndexDataFrame():
    def __init__(self, df=None):
        self.df = df
        self.combined_df = None
        self.df_cleaned = None
        self.qgrid_widget = None
        self.output_area = widgets.Output()

    def transpose_and_prepare_df(self):
        if self.df is None:
            raise ValueError("Provided DataFrame is None, cannot prepare for display.")
        # Extract level values and create a DataFrame for each level
        levels = self.df.columns.names
        level_values = [self.df.columns.get_level_values(i) for i in range(len(levels))]

        # Create DataFrames for the levels and the values
        level_dfs = []
        for i, level_value in enumerate(level_values):
            level_df = pd.DataFrame([level_value], columns=self.df.columns)
            level_df.index = [levels[i]]
            level_dfs.append(level_df)

        value_df = pd.DataFrame(self.df.values, columns=self.df.columns, index=self.df.index)
        self.combined_df = pd.concat(level_dfs + [value_df]).T

        # Adjust column and row names to handle duplicates and maintain structure
        new_columns = [col if col not in levels else f'_{col}' for col in self.combined_df.columns]
        self.combined_df.columns = new_columns

        # Filter out columns with underscores (not needed for viewing)
        columns_to_keep = [col for col in self.combined_df.columns if '_' not in col]
        self.df_cleaned = self.combined_df[columns_to_keep]

    def display_in_qgrid(self):
        # Display the cleaned DataFrame in qgrid with toolbar enabled
        self.qgrid_widget = qgrid.show_grid(self.df_cleaned, show_toolbar=True)
        self.qgrid_widget.on('filter_changed', self.on_filter_change)
        display(self.qgrid_widget)
        display(self.output_area)

    def on_filter_change(self, event, widget):
        # Handle filtering changes by updating the output area
        with self.output_area:
            clear_output(wait=True)
            filtered_df = widget.get_changed_df().T
            display(filtered_df)
            
    def write_dataframe(self, df, file_path, delimiter=';'):
        if df is None:
            raise ValueError("Provided DataFrame is None, cannot serialize to file.")
        # Write DataFrame to CSV, ensuring MultiIndex is preserved
        df.to_csv(file_path, header=True, index=True, sep=delimiter)

    def read_dataframe(self, file_path, delimiter=';'):
        # Read DataFrame from CSV, handling MultiIndex headers and index
        df = pd.read_csv(file_path, header=[0, 1, 2], index_col=0, sep=delimiter)
        self.df = df
        return df

    def getWidgets(self):
        # Provide access to the qgrid widget and the output area for external manipulation
        return self.qgrid_widget, self.output_area