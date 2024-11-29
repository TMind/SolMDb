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

from dateutil import parser
import pytz

def compare_times(time_str1, time_str2, default_timezone=pytz.UTC):
    """
    Compares two time strings that may be in different formats and timezones.
    
    Parameters:
    - time_str1: The first time string.
    - time_str2: The second time string.
    - default_timezone: The timezone to assume if a time string has no timezone info (default is UTC).
    
    Returns:
    - -1 if time_str1 is earlier than time_str2.
    -  0 if time_str1 is equal to time_str2.
    -  1 if time_str1 is later than time_str2.
    - None if there is an error parsing the time strings.
    """
    try:
        # Parse the first time string
        dt1 = parser.parse(time_str1)
        # Parse the second time string
        dt2 = parser.parse(time_str2)
    except (ValueError, TypeError) as e:
        print(f"Error parsing time strings: {e}")
        return None
    
    # Ensure both datetime objects are timezone-aware
    # If timezone is missing, assign the default timezone
    if dt1.tzinfo is None:
        dt1 = default_timezone.localize(dt1)
    else:
        dt1 = dt1.astimezone(default_timezone)
        
    if dt2.tzinfo is None:
        dt2 = default_timezone.localize(dt2)
    else:
        dt2 = dt2.astimezone(default_timezone)
    
    # Compare the datetime objects
    if dt1 < dt2:
        return -1  # time_str1 is earlier
    elif dt1 > dt2:
        return 1   # time_str1 is later
    else:
        return 0   # times are equal
    
def get_min_time(time_strings, default_timezone=pytz.UTC, output_format='%Y-%m-%d %H:%M:%S%z'):
    """
    Returns the earliest time from a list of time strings.

    Parameters:
    - time_strings: A list of time strings.
    - default_timezone: The timezone to assume if a time string has no timezone info (default is UTC).
    - output_format: The format string to output the time (default includes timezone offset).

    Returns:
    - The earliest time as a formatted string.
    - None if there is an error parsing the time strings or if the list is empty.
    """
    if not time_strings:
        return None

    min_dt = None

    for time_str in time_strings:
        if not time_str:
            continue  # Skip empty strings
        try:
            # Parse the time string
            dt = parser.parse(time_str)
        except (ValueError, TypeError) as e:
            print(f"Error parsing time string '{time_str}': {e}")
            continue  # Skip invalid time strings

        # Ensure datetime object is timezone-aware
        if dt.tzinfo is None:
            dt = default_timezone.localize(dt)
        else:
            dt = dt.astimezone(default_timezone)

        # Update min_dt if this datetime is earlier
        if (min_dt is None) or (dt < min_dt):
            min_dt = dt

    if min_dt is not None:
        # Return the earliest time as a formatted string
        #print(f"Returning min time: {min_dt}")
        return min_dt.strftime(output_format)
    else:
        # All time strings were invalid
        return None