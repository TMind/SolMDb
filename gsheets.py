import gspread
from google.oauth2.service_account import Credentials

class GoogleSheetsClient:
    def __init__(self):
        # Hardcode the path to your service account file and the sheet URL
        self.service_account_file = '/Users/tmind/Documents/Code/GitHub/SolDB/binder/soldb-434422-cf0ec4d74ebd.json'
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