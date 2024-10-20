import requests
import json
from GlobalVariables import global_vars as gv
from pycognito import Cognito

CLIENT_ID = '75mcr7j8relead00pia1dbse9c'
USER_POOL_ID = 'us-east-1_jVJJZlRKv'
class NetApi:
    def __init__(self, username='tmind', password=None):
        self.base_url = "https://ul51g2rg42.execute-api.us-east-1.amazonaws.com/main"
        self.cognito = Cognito(USER_POOL_ID, CLIENT_ID, username=username)
        self.auth_token = None
        self.username = username
        self.password = password

    def authenticate(self):
        """
        Authenticate using PyCognito and obtain the ID token.
        """
        try:
            self.cognito.authenticate(password=self.password)
            self.auth_token = self.cognito.id_token
            print(f"Authentication successful! ID Token: {self.auth_token}")
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False

    def collection_request(self, id="", type="deck", username="TMind", params=None):
        """
        Makes a request to the specified API, handles pagination for batch API, and returns all deck data for a user.
        """
        params = params or {}
        default_params = {
            "inclPvE": "true",
            "username": username
        }
        default_params.update(params)
        params = default_params

        if id:  # Use the old protocol (single entry)
            endpoint = f"{self.base_url}/{type}/{id}"  # URL for a single deck by ID
        else:  # Use the new protocol (batch entry)
            endpoint = f"{self.base_url}/{type}/app"

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors
            page_data = response.json()

            # Old protocol: no pagination, return single result directly
            if id:
                return [page_data]

            # New protocol: handle pagination
            all_decks = page_data.get('Items', [])
            last_evaluated_key = page_data.get('LastEvaluatedKey', {})

            # Paginate if LastEvaluatedKey is present
            gv.update_progress('Fetching decks')
            while last_evaluated_key and last_evaluated_key.get('PK') and last_evaluated_key.get('SK'):
                params.update({
                    "exclusiveStartKeyPK": last_evaluated_key['PK'],
                    "exclusiveStartKeySK": last_evaluated_key['SK']
                })
                response = requests.get(endpoint, params=params)
                response.raise_for_status()

                page_data = response.json()
                all_decks.extend(page_data.get('Items', []))

                # Check if there is another page to fetch
                last_evaluated_key = page_data.get('LastEvaluatedKey', {})
                gv.update_progress('Fetching decks', len(page_data.get('Items', [])), len(all_decks), "Paginate")
            gv.update_progress('Fetching decks', len(all_decks), len(all_decks), "Pagination finished")
            return all_decks

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON response: {e}")
            return []

    def post_solbind_request(self, deck_id):
        """
        Sends a POST request to the solbind endpoint with the given username and deck_id.
        This method ensures the authentication token is included in the request.
        """
        # Authenticate if token is not available
        if not self.auth_token and not self.authenticate():
            return None

        # Prepare URL and payload
        url = f"{self.base_url}/user/solbind/{deck_id}"
        if not (self.username and deck_id):
            print("Username and deck are required.")
            return None

        payload = {"username": self.username}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}"  # Include the ID token in the Authorization header
        }

        try:
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                print("Request was successful")
                return response.json()  # Assuming the response is in JSON format
            else:
                print(f"Request failed with status code: {response.status_code}")
                return response.text

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None

    def update_fused_deck(self, fusion, new_name):
        """
        Updates the name of a fused deck for the given fuse_id.
        """
        # Authenticate if token is not available
        if not self.auth_token and not self.authenticate():
            return None

        # Fetch the fused deck data
        fused_deck_data = fusion
        fuse_id = fused_deck_data.get('id')
        myDecks = fused_deck_data.get('myDecks')

        # Define the URL with the fuse_id
        url = f"{self.base_url}/fuseddeck/{fuse_id}"

        # Define headers, including the authentication token
        headers = {
            "Authorization": f"Bearer {self.auth_token}",  # Use the authenticated ID token
            "Content-Type": "application/json"
        }

        # Define the payload with the new name and other required fields
        payload = {
            "username": self.username,  # Use the username from the instance
            "name": new_name,
            "myDecks": myDecks
        }

        # Send the POST request
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                print("Deck name updated successfully")
                return response.json()  # Assuming the response is in JSON format
            else:
                print(f"Request failed with status code: {response.status_code}")
                return response.text
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None

    def request_decks(self, id="", type="deck", username="TMind", filename=None, params=None):
        if id.startswith('Fused'):
            type = 'fuseddeck'
        decks_data = self.collection_request(id, type, username, params)
        return decks_data

    def load_data(self, filename):
        with open(filename, 'r') as f:
            content = f.read()
            data = json.loads(content)

        if 'Items' in data:
            return data['Items']
        else:
            return [data]