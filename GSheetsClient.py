import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
class GoogleSheetsClient:
    def __init__(self, service_account_file_path='~/soldb-gc-key.json', sheet_url=None, doc_id = None, doc_url=None):
        self.sheet_url = sheet_url
        self.doc_url = doc_url
        self.doc_id = doc_id
        self.service_account_file_path = os.path.expanduser(service_account_file_path)
        self.drive_service = None
        self.credentials = None
        self.gc = None
        self.docs_service = None

    def authenticate_google_services(self):
        """
        Authenticates using the service account file for both Google Sheets, Drive, and Google Docs APIs.
        """
        # Scopes for Google Sheets, Drive, and Docs
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/documents.readonly'
        ]
        
        if os.path.exists(self.service_account_file_path):
            self.credentials = Credentials.from_service_account_file(self.service_account_file_path, scopes=SCOPES)
            # Google Sheets and Drive clients
            self.gc = build('sheets', 'v4', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            # Google Docs client
            self.docs_service = build('docs', 'v1', credentials=self.credentials)
        else:
            print(f"Service Account File '{self.service_account_file_path}' does not exist!")
            return

    def read_data_from_google_sheet(self, worksheet_name):
        """
        Reads data from the Google Sheet using the Google Sheets API.
        """
        if self.gc is None:
            self.authenticate_google_services()

        if not self.sheet_url:
            raise ValueError("Sheet URL is not set. Cannot read data from Google Sheet.")

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
                self.authenticate_google_services()

            if not self.sheet_url:
                raise ValueError("Sheet URL is not set. Cannot retrieve timestamp.")

            spreadsheet_id = self.sheet_url.split('/d/')[1].split('/')[0]
            file_metadata = self.drive_service.files().get(fileId=spreadsheet_id, fields='modifiedTime').execute()
            return file_metadata['modifiedTime']
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def get_sheet_title(self):
        try:
            if not self.credentials:
                self.authenticate_google_services()

            if not self.sheet_url:
                raise ValueError("Sheet URL is not set. Cannot retrieve title.")

            spreadsheet_id = self.sheet_url.split('/d/')[1].split('/')[0]
            file_metadata = self.drive_service.files().get(fileId=spreadsheet_id, fields='name').execute()
            return file_metadata['name']
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def get_document_link_from_google_doc(self):
        """
        Fetches and extracts a Google Sheets URL from the Google Docs content (if available).
        """
        if self.docs_service is None:
            self.authenticate_google_services()

        if not self.doc_url:
            raise ValueError("Document URL is not set. Cannot extract link from Google Doc.")

        document_id = self.doc_url.split('/d/')[1].split('/')[0]
        doc_id = '1cee1_eJKZtxUiebmL1LjrrGQFn_kTj_sMMdr81S7YOI'

        try:
            doc = self.docs_service.documents().get(documentId=self.doc_id).execute()
            content = doc.get('body', {}).get('content', [])

            # Look for a link to a Google Sheet in the document
            for element in content:
                if 'paragraph' in element:
                    text_runs = element['paragraph'].get('elements', [])
                    for text_run in text_runs:
                        if 'textRun' in text_run and 'link' in text_run['textRun'].get('textStyle', {}):
                            link = text_run['textRun']['textStyle']['link'].get('url')
                            if link and "docs.google.com/spreadsheets/d/" in link:
                                return link
            raise ValueError("No Google Sheets link found in the document.")
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

        
from CMManager import CMManager        
def main():
    # Define credentials and document ID
    SERVICE_ACCOUNT_FILE = '~/soldb-gc-key.json'
    GOOGLE_DOC_ID = '1cee1_eJKZtxUiebmL1LjrrGQFn_kTj_sMMdr81S7YOI'

    # Initialize GoogleSheetsClient
    sheets_client = GoogleSheetsClient(service_account_file_path=SERVICE_ACCOUNT_FILE, doc_url=f"https://docs.google.com/document/d/{GOOGLE_DOC_ID}")

    # Dummy database manager
    db_manager = None  # Replace with your actual DatabaseManager instance

    # Initialize CMManager
    cm_manager = CMManager(
        db_manager=db_manager,
        doc_id=GOOGLE_DOC_ID,
        sheets_client=sheets_client
    )

    # Display the fetched sheet URL and metadata
    print("Fetched Sheet URL:", cm_manager.sheets_client.sheet_url)
    print("Sheet Title:", cm_manager.title)
    print("Sheet Timestamp:", cm_manager.timestamp)


if __name__ == "__main__":
    main()