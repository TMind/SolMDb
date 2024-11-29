import os
import datetime
import pandas as pd
from datetime import datetime

class CMManager:
    def __init__(self, db_manager, sheet_url, local_copy_path='csv/sff.csv', sheets_client=None):
        self.db_manager = db_manager
        self.sheet_url = sheet_url
        self.local_copy_path = local_copy_path
        self.sheets_client = sheets_client  # Pass GoogleSheetsClient for online‚ interaction
        self.title = None
        self.timestamp = None
        self.cm_tags = None

        if not sheets_client:
            raise ValueError("CMManager requires an instance of GoogleSheetsClient for online interaction.")
        
        # Load metadata from the database
        self.load_metadata()
        
        # Check if the local CSV file exists; if not, download it        
        if not os.path.exists(self.local_copy_path):
            print(f"Local CSV '{self.local_copy_path}' not found. Downloading from Google Sheet...")
            self.update_local_csv('Card Database')

    def update_local_csv(self, worksheet_name):
        try:
            # Read data from the Google Sheet using GoogleSheetsClient
            rows = self.sheets_client.read_data_from_google_sheet(worksheet_name)

            # Convert rows to a DataFrame
            df = pd.DataFrame(rows[1:], columns=rows[0])  # Assuming the first row is headers

            # Save DataFrame to CSV
            df.to_csv(self.local_copy_path, index=False, sep=';')
            print(f"Local CSV updated at {self.local_copy_path}")

            # After updating the local CSV, fetch the new metadata
            raw_timestamp = self.sheets_client.get_sheet_timestamp()
            self.timestamp = self.format_timestamp(raw_timestamp)  # Format the timestamp            
            self.title = self.sheets_client.get_sheet_title()  # Get updated title
            
            # Get the index of the starting column
            start_column_index = df.columns.get_loc('Beast')        
            # Retrieve column names starting from the specified column
            self.cm_tags = df.columns[start_column_index:].tolist()
            
            # Store the updated metadata in the database
            self.store_sheet_metadata(self.timestamp, self.title, self.cm_tags)  # Pass tags if needed

        except Exception as e:
            print(f"An error occurred while updating the local CSV: {e}")


    def format_timestamp(self, raw_timestamp):
        """ Converts the raw timestamp from the Google Sheets API into a human-readable format. """
        try:
            # Parse the ISO 8601 timestamp without the trailing 'Z'
            dt = datetime.strptime(raw_timestamp[:-1], '%Y-%m-%dT%H:%M:%S.%f')  # Adjust format as needed
            # Format it as a human-readable string
            return dt.strftime('%Y-%m-%d %H:%M:%S')  # Adjust format as needed
        except ValueError:
            print(f"Invalid timestamp format: {raw_timestamp}")
            return raw_timestamp  # Return the original if formatting fails

    def load_metadata(self):
        stored_data = self.db_manager.find_one('sheet_metadata', {'sheet_name': 'Card Database'})
        if stored_data:
            self.title = stored_data.get('title')
            self.timestamp = stored_data.get('timestamp')
            self.cm_tags = stored_data.get('cm_tags')
            #print(f"Loaded metadata: title='{self.title}', timestamp='{self.timestamp}'")
        else:
            print("No metadata found in the database.")

    def store_sheet_metadata(self, timestamp, title, tags):
        self.timestamp = timestamp
        self.title = title
        self.cm_tags = tags
        metadata = {
            'sheet_name': 'Card Database',
            'timestamp': timestamp,
            'title': title,
            'cm_tags': tags
        }
        try:
            if self.db_manager:
                self.db_manager.upsert('sheet_metadata', {'sheet_name': 'Card Database'}, metadata)
                print(f"Sheet metadata updated in database {self.db_manager.get_current_db_name()}: {metadata}")
            else:
                print("commonDB is not initialized.")
        except Exception as e:
            print(f"Failed to store sheet metadata: {e}")
            
    def get_column_names_from(self, worksheet_name, start_column_name):
        """
        Retrieves column names from the local CSV file starting from a specific column.
        """
        df = pd.read_csv(self.local_copy_path, sep=';')
        
        # Ensure the DataFrame contains the desired start_column_name
        if start_column_name not in df.columns:
            raise ValueError(f"Column '{start_column_name}' not found in the local sheet.")

        # Get the index of the starting column
        start_column_index = df.columns.get_loc(start_column_name)
        
        # Retrieve column names starting from the specified column
        column_names = df.columns[start_column_index:].tolist()
        return column_names