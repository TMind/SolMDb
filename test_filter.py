import pandas as pd
import pytest
import sys, os

# Assuming gv.out_debug is available in your environment
import GlobalVariables as gv  # Replace with the actual module if needed

# Import the function you want to test
from GridManager import apply_cardname_filter_to_dataframe

# Fixture for the saved DataFrame
@pytest.fixture
def filtered_grid_0_df():
    return pd.read_csv('dataframes/filtered_grid_0.csv')

# Filter DataFrame defining the filters to be applied
@pytest.fixture
def filter_df():
    return pd.DataFrame({
        'Type': ['', '', ''],
        'Modifier': ['', 'Vampiric', 'Rallying'],
        'op1': ['', 'OR', ''],
        'Creature': ['Darkshaper Savant', 'Necromancer', ''],
        'op2': ['AND', '', 'AND'],
        'Spell': ['River of Souls', '', ''],
        'Forgeborn Ability': ['', '', 'Enhance'],
        'Active': [True, True, True]  # Filter only active rows
    })

# Test the function for every filter set in filter_df
def test_apply_filters_to_every_set(filtered_grid_0_df, filter_df):
    for index, filter_row in filter_df.iterrows():
        if filter_row['Active']:  # Apply only active filters
            # Convert the filter row to a DataFrame for the function
            filter_single_row_df = pd.DataFrame([filter_row])
            
            # Apply the filter to the DataFrame
            filtered_result_df = apply_cardname_filter_to_dataframe(filtered_grid_0_df, filter_single_row_df)
            
            # Print or assert some expected output
            print(f"Result after applying filter set {index}:\n", filtered_result_df)
            
            # You can add assertions or further analysis here based on expected results
            assert not filtered_result_df.empty, f"Filter set {index} should return non-empty results."
            
# Run pytest
if __name__ == '__main__':
    pytest.main()