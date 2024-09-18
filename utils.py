import pandas as pd 

def get_totals_row(df, rotated_column_definitions):
    """
    Helper method to generate the totals row from the current DataFrame.
    For numeric columns, sum values; for non-numeric columns, return an empty string or appropriate label.
    """
    numeric_df = df.copy()
    numeric_cols = [col for col in df.columns if col in rotated_column_definitions]

    for col in numeric_cols:
        numeric_df[col] = pd.to_numeric(numeric_df[col], errors='coerce')

    totals = numeric_df[numeric_cols].sum(numeric_only=True)

    totals_row = pd.DataFrame(totals).T
    totals_row['DeckName'] = 'Totals'

    for col in df.columns:
        if col not in totals_row.columns:
            totals_row[col] = ''

    totals_row = totals_row[df.columns]
    return totals_row