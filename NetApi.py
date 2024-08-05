import requests
import json
#from UniversalLibrary import UniversalLibrary
#from CardLibrary import Fusion
#from typing import List, Tuple, Dict
#from tqdm.notebook import tqdm
import GlobalVariables as gv 


class NetApi:

    def __init__(self, ucl, csvfile=None):
        self.csvfile = csvfile or 'csv/sff.csv'
        self.ucl = ucl
        self.base_url = "https://ul51g2rg42.execute-api.us-east-1.amazonaws.com/main"  

    def make_request(self, id="", type="deck", username="TMind"):
        params = {            
            "inclPvE": "true",
            "username": username
        }        
        endpoint = f"{self.base_url}/{type}/app?{id}"
                
#        print(f"Requesting Data from Website: {','.join([username, type, id])}")
#        print(f"Endpoint: {endpoint}")
#        print(f"Params: {params}")

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors
            pageData = response.json()
            #print(f"Initial response data: {pageData}")

            lastPK = ""
            all_decks = pageData['Items']                        
            total = pageData['Count']

#            with tqdm(total=total, initial=pageData['Count'], desc="Fetching Data", colour='YELLOW') as pbar:
            gv.update_progress('Network API', 0, pageData['Count'], f"{total} records fetched") 
            #gv.intProgressBar.max = total             
            #gv.load_progress.n = pageData['Count']
 
            while 'LastEvaluatedKey' in pageData and lastPK != pageData['LastEvaluatedKey']['PK']:
                lastPK = pageData['LastEvaluatedKey']['PK']            
                lastSK = pageData['LastEvaluatedKey']['SK']            
                params.update({"exclusiveStartKeyPK": lastPK, 'exclusiveStartKeySK': lastSK})
                response = requests.get(endpoint, params=params)
                response.raise_for_status()
                pageData = response.json()
                #print(f"Page data: {pageData}")

                if 'error' in pageData:
                    print(f"Error in response: {pageData['error']}")
                    return []
                all_decks.extend(pageData['Items'])
                records_fetched = pageData['Count']                

                total += records_fetched
                gv.update_progress('Network API', total, total, f"{records_fetched} additional records from {total} fetched")
                #if gv.intProgressBar.value + records_fetched > gv.intProgressBar.max:
                #    gv.intProgressBar.max += records_fetched
                #gv.intProgressBar.value = records_fetched

            if 'error' in pageData:
                print(f"Error in response: {pageData['error']}")
                return []

            if 'Items' in all_decks:     
                return all_decks['Items']
            else:                   
                return all_decks

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON response: {e}")
            return []

    def request_decks(self, id="", type="deck", username="TMind", filename=None):
        if id.startswith('Fused'):  
            type = 'fuseddeck'         
        decks_data = self.make_request(id, type, username)        
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
