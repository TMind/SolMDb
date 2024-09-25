import requests
import json
from GlobalVariables import global_vars as gv 


class NetApi:

    def __init__(self, csvfile=None):
        self.csvfile = csvfile or 'csv/sff.csv'
        self.base_url  = "https://ul51g2rg42.execute-api.us-east-1.amazonaws.com/main"  

    def make_request(self, id="", type="deck", username="TMind", params=None):
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


    def request_decks(self, id="", type="deck", username="TMind", filename=None, params=None):
        if id.startswith('Fused'):  
            type = 'fuseddeck'         
        decks_data = self.make_request(id, type, username, params)        
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
