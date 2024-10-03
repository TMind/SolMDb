import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleSheetsClient:
    def __init__(self, service_account_file_path='~/soldb-gc-key.json'):
        self.sheet_url = 'https://docs.google.com/spreadsheets/d/1HFDXfrO4uE70-HyNAxdHuCVlt_ALjBK9f6tpveRudZY/edit'
        self.service_account_file_path = os.path.expanduser(service_account_file_path)
        self.drive_service = None
        self.credentials = None
        self.gc = None

    def authenticate_google_sheets(self):
        """
        Authenticates using the service account file.
        """
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly', 'https://www.googleapis.com/auth/drive']
        if os.path.exists(self.service_account_file_path):
            self.credentials = Credentials.from_service_account_file(self.service_account_file_path, scopes=SCOPES)
            self.gc = build('sheets', 'v4', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
        else:
            print(f"Service Account File does not exist!")
            return

    def read_data_from_google_sheet(self, worksheet_name):
        """
        Reads data from the Google Sheet using the Google Sheets API.
        """
        if self.gc is None:
            self.authenticate_google_sheets()

        spreadsheet_id = self.sheet_url.split('/d/')[1].split('/')[0]
        range_name = f"{worksheet_name}"  # Adjust the range as necessary

        try:
            result = self.gc.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
            rows = result.get('values', [])
            return rows
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    def get_sheet_timestamp(self):
        try:
            if not self.credentials:
                self.authenticate_google_sheets()
            spreadsheet_id = self.sheet_url.split('/d/')[1].split('/')[0]
            file_metadata = self.drive_service.files().get(fileId=spreadsheet_id, fields='modifiedTime').execute()
            return file_metadata['modifiedTime']
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def get_sheet_title(self):
        try:
            if not self.credentials:
                self.authenticate_google_sheets()
            spreadsheet_id = self.sheet_url.split('/d/')[1].split('/')[0]
            file_metadata = self.drive_service.files().get(fileId=spreadsheet_id, fields='name').execute()
            return file_metadata.get('name', None)
        except Exception as e:
            print(f"An error occurred while fetching the title: {e}")
            return None