import requests
import json

AUTHENTICATION_TOKEN = 'eyJraWQiOiJtRW5iWXZvODY1dXNYOE15XC9GYXF5cWNkN1R1SjVxVlllZGJrUktaTVMyaz0iLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiI3NzQ4ODhkMC01NDllLTRhNWQtOWE0NC05MmJmZjdmMjgxZWEiLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAudXMtZWFzdC0xLmFtYXpvbmF3cy5jb21cL3VzLWVhc3QtMV9qVkpKWmxSS3YiLCJjdXN0b206aXNKdWRnZSI6ImZhbHNlIiwiY3VzdG9tOmFjY291bnRUYWdzIjoiW10iLCJhdmF0YXJJZCI6IkF2YXRhcl8zaWUxeWhpOWw0ZDlpZnYwIiwiY3VzdG9tOnN0b3JlVXNlciI6ImZhbHNlIiwiY3VzdG9tOmlzT3JnYW5pemVyIjoidHJ1ZSIsImF1dGhfdGltZSI6MTcyNTU2MzQ4NSwiZXhwIjoxNzI3NTIwNjUyLCJpYXQiOjE3Mjc1MTcwNTMsImp0aSI6ImVlMzk4NGZlLTE4M2ItNGM0Yi04M2QyLTYzMTE4Y2JkMWIxYiIsImVtYWlsIjoic3RlZmFuMjU4MUBnbWFpbC5jb20iLCJjdXN0b206YW1iYXNzYWRvclBvaW50cyI6IjAiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiYXZhdGFyVXJsIjoiaHR0cHM6XC9cL3Nmd21lZGlhMTE0NTMtbWFpbi5zMy51cy1lYXN0LTEuYW1hem9uYXdzLmNvbVwvcHVibGljXC9zdGVlbC1yb3NldHRhLWNyb3BwZWQucG5nIiwiY29nbml0bzp1c2VybmFtZSI6InRtaW5kIiwiY3VzdG9tOnN1YnNjcmliZXIiOiJmYWxzZSIsImdpdmVuX25hbWUiOiJTdGVmYW4iLCJjdXN0b206dXNlcklkIjoiMlVESFZUV0w2VyIsIm9yaWdpbl9qdGkiOiI5MjIzZmVmMC03MGRjLTQyMDktODYxNC01OWI3OGM5ZDk4YjMiLCJhdmF0YXJOYW1lIjoiU3RlZWwgUm9zZXR0YSIsImF1ZCI6Ijc1bWNyN2o4cmVsZWFkMDBwaWExZGJzZTljIiwiZXZlbnRfaWQiOiIxM2M5OWVlNS01Y2E3LTRiZmMtOGNlNi1mMDI5MGRlYzExNDQiLCJ0b2tlbl91c2UiOiJpZCIsImN1c3RvbTphbGxvd19tYXJrZXRpbmciOiJ0cnVlIiwiZmFtaWx5X25hbWUiOiJSIn0.nPZG1Z6ASLz2jlmpo573U2GiIvbKQg3MoIdLm3f1XjVykR0_VTsd6sJPz8KifV5aiDQQtOQueg_ZyJ8HfDQc4UUEX938ERa8Y5Hf8A_AzOryBas2kqFG0rp-CxG7XGz17GTDXMAYH0d3QZjNaYB0S8T0pCH_Yl-71QPri3uTS8RztuXOHAw_Kr0og2i8hNjujooNENgUyvnqOEeTwJT8S86O9QiRd4wBygF3SaVJS5_qMzQpkL48t85QvaavjC5r52da_SNPag0fMwn-Iw_EC6TSndGijF5XlqeIG0ywtt6fegalAB_xxY8bwDPipztXBy19Rdrn35CFNKQCb6vT5w'

class NetApi:

    def __init__(self,  auth_token=AUTHENTICATION_TOKEN):        
        self.base_url  = "https://ul51g2rg42.execute-api.us-east-1.amazonaws.com/main"  
        self.auth_token = auth_token

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

            return all_decks

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON response: {e}")
            return []


    def post_solbind_request(self, username, deck_id):
        """
        Sends a POST request to the solbind endpoint with the given username and deck_id.
        """
        url = f"{self.base_url}/user/solbind/{deck_id}"

        payload = {"username": username}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}"
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


    def update_fused_deck(self, username, fusion, new_name):
        """
        Updates the name of a fused deck for the given fuse_id.

        :param fusion: The Fusion Data from the DB.
        :param new_name: The new name to assign to the fused deck.
        :param auth_token: Authorization token for API access.
        :return: The response from the API.
        """
        
        # Fetch the fused deck data
        fused_deck_data = fusion
        fuse_id = fused_deck_data.get('id')
        
        forgebornIds = fused_deck_data.get('ForgebornIds')
        currentForgebornId = fused_deck_data.get('currentForgebornId')
        myDecks = fused_deck_data.get('myDecks')
        
        # Define the URL with the fuse_id
        url = self.base_url + f"/fuseddeck/{fuse_id}"
        
        auth_token = input("Enter the authorization token: ")
        
        # Define headers, including the authorization token
        headers = {
            "Authorization": f"Bearer {auth_token}",  # Use the provided auth token
            "Content-Type": "application/json"
        }

        # Define the payload with the new name and other required fields
        payload = {
            "username": username,
            "name": new_name,  # Use the new name provided as a parameter
            #"forgebornId": forgebornIds[0],
            #"currentForgebornId": currentForgebornId,
            "myDecks": myDecks            
        }

        # Send the POST request
        response = requests.post(url, json=payload, headers=headers)
        print(f"Response: {response}")


    def request_decks(self, id="", type="deck", username="TMind", filename=None, params=None):
        if id.startswith('Fused'):  
            type = 'fuseddeck'         
        decks_data = self.collection_request(id, type, username, params)        
        #print(f"Fetched decks data: {decks_data}")
        return decks_data

    def load_data(self, filename):
        with open(filename, 'r') as f:
            content = f.read()
            data = json.loads(content)

        if 'Items' in data:
            return data['Items']
        else:                                
            return [data]


import boto3

# CognitoAuth class encapsulates the authentication logic
class CognitoAuth:
    def __init__(self, client_id, username, password, region='us-east-1'):
        self.client_id = client_id
        self.username = username
        self.password = password
        self.client = boto3.client('cognito-idp', region_name=region)

    def initiate_auth(self):
        """
        Initiate the authentication process with USER_PASSWORD_AUTH.
        Returns the response from Cognito, which may contain a challenge.
        """
        try:
            response = self.client.initiate_auth(
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': self.username,
                    'PASSWORD': self.password
                },
                ClientId=self.client_id
            )
            return response
        except self.client.exceptions.NotAuthorizedException as e:
            print(f"Authentication failed: {e}")
            return None

    def respond_to_challenge(self, challenge_response):
        """
        Responds to the PASSWORD_VERIFIER challenge.
        """
        if challenge_response.get('ChallengeName') == 'PASSWORD_VERIFIER':
            try:
                response = self.client.respond_to_auth_challenge(
                    ClientId=self.client_id,
                    ChallengeName='PASSWORD_VERIFIER',
                    ChallengeResponses={
                        'USERNAME': self.username,
                        # Add any additional required parameters here based on the challenge
                        # For example: 'PASSWORD_CLAIM_SIGNATURE': 'generate_signature_here'
                    }
                )
                return response
            except Exception as e:
                print(f"Error responding to challenge: {e}")
                return None

    def authenticate(self):
        """
        Full authentication flow. Returns tokens if successful.
        """
        # Initiate auth
        auth_response = self.initiate_auth()

        if auth_response and 'ChallengeName' in auth_response:
            # Respond to challenge
            challenge_response = self.respond_to_challenge(auth_response)
            if challenge_response:
                tokens = challenge_response['AuthenticationResult']
                return tokens
        elif auth_response and 'AuthenticationResult' in auth_response:
            # No challenge, return tokens
            tokens = auth_response['AuthenticationResult']
            return tokens
        else:
            print("Authentication failed or unexpected response.")
            return None

    def get_access_token(self):
        """
        Get the access token after authentication.
        """
        tokens = self.authenticate()
        if tokens:
            return tokens.get('AccessToken')
        return None

    def get_id_token(self):
        """
        Get the ID token after authentication.
        """
        tokens = self.authenticate()
        if tokens:
            return tokens.get('IdToken')
        return None

    def get_refresh_token(self):
        """
        Get the refresh token after authentication.
        """
        tokens = self.authenticate()
        if tokens:
            return tokens.get('RefreshToken')
        return None