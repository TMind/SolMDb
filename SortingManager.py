import pandas as pd
import utils

class SortingManager:
    def __init__(self, rotated_column_definitions):
        """
        Initialize SortingManager with rotated column definitions.
        Args:
            rotated_column_definitions (dict): A dictionary containing column information for rotated columns.
        """
        self.rotated_column_definitions = rotated_column_definitions            
        self.sorting_info = {}


    def handle_sort_changed(self, event, qgrid_widget):
        """
        Handle the sorting event and ensure the totals row stays at the top.
        This method works for any grid widget passed to it.
        """
        sort_column = event['new']['column']
        print(f"Sort column triggered: {sort_column}")

        if sort_column in self.rotated_column_definitions:
            self.update_sorted_columns(sort_column)

            # Prepare sorted columns and their ascending states
            columns_to_sort = [col for col in sorted(self.sorting_info, key=lambda x: self.sorting_info[x]['sort_order'])]
            ascending_states = [self.sorting_info[col]['ascending'] for col in columns_to_sort]

            # Get the updated DataFrame from the grid widget
            sorted_df = qgrid_widget.get_changed_df()

            # Remove the totals row from the sorted DataFrame
            data_rows = sorted_df[sorted_df['DeckName'] != 'Totals']

            # Reinsert the totals row at the top
            totals_row = utils.get_totals_row(data_rows, self.rotated_column_definitions)

            # Concatenate the totals row back at the top
            updated_df = pd.concat([totals_row, data_rows], ignore_index=True)

            # Sort the DataFrame manually based on sorted_columns and their ascending states
            updated_df = self.sort_dataframe(updated_df, columns_to_sort, ascending_states)

            # Recreate the grid with the updated DataFrame
            qgrid_widget.df = updated_df

            # Call the UI update function
            #update_ui_callback()

        else:
            # Handle non-rotated columns
            self.sorting_info = {}
            self.update_sorted_columns(sort_column)

            # Trigger sorting manually for non-rotated columns
            sorted_df = qgrid_widget.get_changed_df()

            # Recreate the grid with updated sorting
            qgrid_widget.df = sorted_df
            #update_ui_callback()

    def sort_dataframe(self, df, columns_to_sort, ascending_states):
        """
        Sort the DataFrame based on the given columns and their respective ascending states.
        If the columns are numeric but represented as strings, convert them to numbers for sorting.
        Treat empty cells as 0 for sorting purposes.

        Args:
            df (pd.DataFrame): The DataFrame to sort.
            columns_to_sort (list): The columns to sort by.
            ascending_states (list): Boolean list representing ascending or descending order for each column.

        Returns:
            pd.DataFrame: The sorted DataFrame.
        """
        # Identify numeric columns in rotated_columns
        numeric_cols = [col for col in columns_to_sort if col in self.rotated_column_definitions]

        # Convert numeric columns to numeric type, treating empty cells as 0
        df[numeric_cols] = df[numeric_cols].apply(lambda col: pd.to_numeric(col, errors='coerce').fillna(0))

        # Perform the sorting
        sorted_df = df.sort_values(by=columns_to_sort, ascending=ascending_states)

        # Convert numeric columns back to strings, but replace 0 with '' where the original value was empty
        for col in numeric_cols:
            sorted_df[col] = sorted_df[col].apply(lambda x: '' if x == 0 else str(int(x) if x.is_integer() else x))

        return sorted_df
    
    
    def update_sorted_columns(self, new_sort_column):
        """
        Update the sorting information for the new sorted column.
        Flip the ascending state if the column is already sorted.
        """
        # If the column is already in sorting_info, flip the ascending state
        if new_sort_column in self.sorting_info:
            self.sorting_info[new_sort_column]['ascending'] = not self.sorting_info[new_sort_column]['ascending']
            print(f"Flipping sort order for column {new_sort_column} to {'ascending' if self.sorting_info[new_sort_column]['ascending'] else 'descending'}")
        else:
            # Add the new column with ascending state and sort order
            self.sorting_info[new_sort_column] = {
                'ascending': False,  # Default to descending for new column
                'sort_order': len(self.sorting_info) + 1  # Track the order of sorting
            }
            print(f"Adding new sorted column {new_sort_column} with ascending order.")

        return self.sorting_info
    
    
    
