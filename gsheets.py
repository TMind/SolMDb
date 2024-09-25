import gspread
from google.oauth2.service_account import Credentials

class GoogleSheetsClient:
    def __init__(self):
        # Hardcode the path to your service account file and the sheet URL
        self.service_account_file = '/Users/tmind/Documents/Code/GitHub/SolDB/binder/soldb-434422-c16794c0f2da.json'
        self.sheet_url = 'https://docs.google.com/spreadsheets/d/1HFDXfrO4uE70-HyNAxdHuCVlt_ALjBK9f6tpveRudZY/edit'
        self.gc = None
        self.credentials = None

    def authenticate_google_sheets(self):
        """
        Authenticates using the hardcoded Google service account JSON and authorizes access to Google Sheets.
        """
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        self.credentials = Credentials.from_service_account_file(self.service_account_file, scopes=SCOPES)
        self.gc = gspread.authorize(self.credentials)

    def read_data_from_google_sheet(self, worksheet_name):
        """
        Reads data from the fixed Google Sheet and worksheet.
        """
        # Authenticate and open the sheet by URL
        if not self.gc:
            self.authenticate_google_sheets()
        
        sh = self.gc.open_by_url(self.sheet_url)
        worksheet = sh.worksheet(worksheet_name)
        rows = worksheet.get_all_values()
        return rows
    
    def get_column_names_from(self, worksheet_name, start_column_name):
        """
        Retrieves column names from the Google Sheet starting from a given column name to the end.
        
        :param worksheet_name: Name of the worksheet to read from.
        :param start_column_name: The column name from which to start.
        :return: A list of column names from the start column to the end.
        """
        # Authenticate if not already done
        if not self.gc:
            self.authenticate_google_sheets()

        # Open the sheet and the specified worksheet
        sh = self.gc.open_by_url(self.sheet_url)
        worksheet = sh.worksheet(worksheet_name)

        # Get the first row, which is typically the header
        header_row = worksheet.row_values(1)

        # Find the index of the start column
        try:
            start_column_index = header_row.index(start_column_name)
        except ValueError:
            raise ValueError(f"Column '{start_column_name}' not found in the sheet.")

        # Get the column names from the specified start column to the end
        column_names = header_row[start_column_index:]

        return column_names