#import pygui as pgui
import pandas as pd


def add_row_in_qgrid(GridManager, id=0, row_data=None, grid_manager=None):
    """
    Programmatically adds a row to the qgrid widget and triggers the row_added event.
    """
    # Ensure the deck content grid has data
    grid_id = f"filtered_grid_{id}"
    filter_df = GridManager.filterGridObject.get_changed_df()

    if filter_df is not None:
        # Add a new row to the DataFrame
        new_row = pd.DataFrame({
            'Type': ['Deck'],
            'Name': [''],
            'Modifier': [''],
            'Creature': [''],
            'Spell': ['Preserved Habitat'],
            'Forgeborn Ability': [''],
            'Active': [True],
            'Mandatory Fields': ['Name, Forgeborn Ability']
        })
        filter_df = pd.concat([filter_df, new_row], ignore_index=True)

        # Update the grid with the new DataFrame
        GridManager.filterGridObject.df = filter_df

        # Trigger the row_added event manually
        event = {
            'index': len(filter_df) - 1  # Index of the newly added row
        }

        # Call the handler if grid_manager is provided
        if GridManager:
            GridManager.filterGridObject.grid_filter_on_row_added(event, GridManager.filterGridObject.qgrid_filter)
    else:
        print("No data in the grid to add a row.")

def test_update_filter_grid(grid_manager):
    """
    Simulates updating a value in the filter grid and triggers the necessary updates.

    Args:
        grid_manager (DynamicGridManager): The grid manager instance to interact with.
    """
    # Access the filter grid
    filter_grid_widget = grid_manager.filterGridObject.qgrid_filter

    # Retrieve the current DataFrame from the filter grid
    filter_df = filter_grid_widget.get_changed_df()

    # Ensure there is data in the filter grid
    if filter_df is not None and not filter_df.empty:
        # Select the first row and update a value programmatically
        row_index = 0
        new_value = "The People of Bearing"

        # Update the 'Name' column in the first row
        filter_df.at[row_index, 'Name'] = new_value

        # Apply the updated DataFrame back to the filter grid
        filter_grid_widget.df = filter_df

        # Trigger the `cell_edited` event manually
        event = {
            'index': row_index,
            'column': 'Name',
            'old': "",  # Original value
            'new': new_value  # New value
        }
        # Trigger the cell edit handler to reflect the change in the system
        grid_manager.filterGridObject.grid_filter_on_cell_edit(event, filter_grid_widget)

        print(f"Test: Updated filter grid row {row_index} 'Name' to '{new_value}'.")
    else:
        print("Filter grid is empty or unavailable.")

def select_row_in_qgrid(GridManager, id=0, row_index=0, grid_manager=None):
    """
    Programmatically selects a row in the qgrid widget and triggers the selection event.
    """
    # Ensure the deck content grid has data
    grid_id = f"filtered_grid_{id}"
    grid_df = GridManager.get_grid_df(grid_id)

    if grid_df is not None and not grid_df.empty:
        # Check if the specified row index is valid
        if 0 <= row_index < len(grid_df):
            # Programmatically select the row
            # Get the widget first
            widget = GridManager.grids[grid_id].main_widget
            widget.change_selection([row_index])

            # Trigger the selection event manually
            event = {
                'new': [row_index]  # 'new' key contains the selected row index
            }

            # Call the handler if grid_manager is provided
            if grid_manager:
                grid_manager.update_deck_content(event, widget)
        else:
            print(f"Invalid row index {row_index}. Must be between 0 and {len(grid_df) - 1}.")
    else:
        print("No data in the grid to select.")

def trigger_sort_on_column(deck_content_grid, column_name, grid_manager=None):
    """
    Programmatically triggers a sort on a specific column in the qgrid widget.
    """
    # Get the grid DataFrame
    
    grid_df = deck_content_grid.get_changed_df()
    
    if grid_df is not None and column_name in grid_df.columns:
                
        # Trigger the sort_changed event manually
        event = {
            'new': {
                'column': column_name,
                'ascending': True  # Adjust this based on desired sort order
            }
        }
        
        # Call the grid manager's sort handler
        if grid_manager:
            grid_manager.handle_sort_changed(event, deck_content_grid)
    else:
        print(f"Column '{column_name}' not found in the grid.")
        
        
def test_add_filter_row(filterGridObject, new_row_data=None):
    """
    Test function to add a new row to the filter grid programmatically.

    Args:
        grid_manager (DynamicGridManager): The grid manager instance.
        new_row_data (dict, optional): The data for the new row. Defaults to a predefined row structure.
    """
    if new_row_data is None:
        # Default data for a new filter row
        new_row_data = {
            'Type': 'Deck',
            'Name': '',
            'Modifier': '',
            'Creature': '',
            'Spell': 'Preserved Habitat',
            'Forgeborn Ability': '',
            'Active': True,
            'Mandatory Fields': 'Name, Forgeborn Ability'
        }

    # Retrieve the filter grid widget
    filter_widget = filterGridObject.qgrid_filter
    if filter_widget is None:
        print("Filter grid widget not found.")
        return

    # Get the current filter DataFrame
    filter_df = filter_widget.get_changed_df()
    if filter_df is None:
        print("Filter grid DataFrame is empty or unavailable.")
        return

    # Add the new row to the DataFrame
    new_row = pd.DataFrame([new_row_data])
    updated_filter_df = pd.concat([filter_df, new_row], ignore_index=True)

    # Update the filter grid widget
    filter_widget.df = updated_filter_df

    # Trigger the row_added event manually
    #event = {'index': len(updated_filter_df) - 1}  # Index of the newly added row
    event = {'index': len(updated_filter_df) - 1, 'name' : 'row_added', 'source': 'gui'}  # List of added row indices
    filterGridObject.grid_filter_on_row_added(event, filter_widget)

    print(f"Test: Added new row to filter grid. Current row count: {len(updated_filter_df)}")
    
def test_remove_filter_row(filterGridObject, row_index=0):
    """
    Test function to remove a row from the filter grid programmatically.

    Args:
        grid_manager (DynamicGridManager): The grid manager instance.
        row_index (int, optional): The index of the row to remove. Defaults to 0.
    """
    # Retrieve the filter grid widget
    filter_widget = filterGridObject.qgrid_filter
    if filter_widget is None:
        print("Filter grid widget not found.")
        return

    # Get the current filter DataFrame
    filter_df = filter_widget.get_changed_df()
    if filter_df is None or filter_df.empty:
        print("Filter grid DataFrame is empty or unavailable.")
        return

    # Check if the row_index is valid
    if row_index < 0 or row_index >= len(filter_df):
        print(f"Invalid row index {row_index}. Must be between 0 and {len(filter_df) - 1}.")
        return

    # Remove the row from the DataFrame
    #updated_filter_df = filter_df.drop(index=row_index).reset_index(drop=True)

    # Update the filter grid widget
    #filter_widget.df = updated_filter_df

    # Trigger the row_removed event manually
    event = {'indices': [row_index], 'name' : 'row_removed'}  # List of removed row indices
    filter_widget._remove_rows([row_index])
    filterGridObject.grid_filter_on_row_removed(event, filter_widget)

    print(f"Test: Removed row {row_index} from filter grid. Current row count: {len(filter_widget.get_changed_df())}")