import requests
import json
from GlobalVariables import global_vars as gv 


class NetApi:

    def __init__(self, csvfile=None):
        self.csvfile = csvfile or 'csv/sff.csv'
        self.base_url = "https://ul51g2rg42.execute-api.us-east-1.amazonaws.com/main"  

    def make_request(self, id="", type="deck", username="TMind", params=None):
        params = params or {}
        default_params = {
            "inclPvE": "true",
            "username": username
        }
        default_params.update(params)
        params = default_params

        # Rest of the code...
        #endpoint = f"{self.base_url}/{type}/app?{id}"
        endpoint = f"{self.base_url}/{type}/{id}"
                
#        print(f"Requesting Data from Website: {','.join([username, type, id])}")
#        print(f"Endpoint: {endpoint}")
#        print(f"Params: {params}")

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors
            pageData = response.json()
            #print(f"Initial response data: {pageData}")

            # If there's an error in the response, return an empty list
            if 'error' in pageData:
                print(f"Error in response: {pageData['error']}")
                return []

                    # Check if this is a paginated result
            if 'LastEvaluatedKey' in pageData:
                # Multiple pages: fetch all items
                all_decks = pageData['Items']
                lastPK = pageData['LastEvaluatedKey']['PK']
                lastSK = pageData['LastEvaluatedKey']['SK']
                total = pageData['Count']
                lastPK = ""
                all_decks = pageData['Items']                        
                total = pageData['Count']

                gv.update_progress('Network API', 0, pageData['Count'], f"Fetching online records") 
 
                while 'LastEvaluatedKey' in pageData and lastPK != pageData['LastEvaluatedKey']['PK']:
                    lastPK = pageData['LastEvaluatedKey']['PK']            
                    lastSK = pageData['LastEvaluatedKey']['SK']            
                    params.update({"exclusiveStartKeyPK": lastPK, 'exclusiveStartKeySK': lastSK})
                    
                    response = requests.get(endpoint, params=params)
                    response.raise_for_status()
                    pageData = response.json()
                    #print(f"Page data: {pageData}")
                    
                    # Handle any errors
                    if 'error' in pageData:
                        print(f"Error in response: {pageData['error']}")
                        return []

                    all_decks.extend(pageData['Items'])
                    records_fetched = pageData['Count']                

                    total += records_fetched
                    gv.update_progress('Network API', total, total, message = f"{records_fetched} additional records from {total} fetched")

                if 'error' in pageData:
                    print(f"Error in response: {pageData['error']}")
                    return []

                if 'Items' in all_decks:     
                    return all_decks['Items']
                else:                   
                    return all_decks

            # No pagination: return the single result directly
            else:
                return pageData['Items'] if 'Items' in pageData else [pageData]

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
