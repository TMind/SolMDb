import requests
import json
from UniversalLibrary import UniversalLibrary
from CardLibrary import Fusion
from typing import List, Tuple, Dict
from tqdm import tqdm

class NetApi:

    def __init__(self, ucl, csvfile=None):
        self.csvfile = csvfile or 'csv/sff.csv'
        self.ucl = ucl
        self.base_url = "https://ul51g2rg42.execute-api.us-east-1.amazonaws.com/main"
        # self.params = {
        #     #"inclCards": "true",
        #     #"inclDecks": "true",
        #     #"inclCategories": "true",
        #     "inclPvE": "true",
        #     "username": "TMind", 
        # }        

    def make_request(self, id="", type="deck", username="TMind"):
        params = {            
            "inclPvE": "true",
            "username": "TMind"
        }        
        endpoint = f"{self.base_url}/{type}/app?{id}"
        
        params.update({"username" : username})
        print(f"Requesting Data from Website: {','.join([username,type,id])}")
        response = requests.get(endpoint, params=params)        
        pageData = response.json()

        lastPK = ""
        all_decks = pageData['Items']                        
        total = pageData['Count']
                
        with tqdm(total=total, initial=pageData['Count'], desc="Fetching Data", colour='YELLOW') as pbar:
            while 'LastEvaluatedKey' in pageData and lastPK != pageData['LastEvaluatedKey']['PK']:
                lastPK = pageData['LastEvaluatedKey']['PK']            
                lastSK = pageData['LastEvaluatedKey']['SK']            
                params.update({"exclusiveStartKeyPK" : lastPK , 'exclusiveStartKeySK' : lastSK})
                response = requests.get(endpoint, params=params)
                pageData = response.json()
                if 'error' in pageData:
                    print(f"Error in response: {pageData['error']}")
                    return []
                all_decks.extend(pageData['Items'])
                            
                records_fetched = pageData['Count']                
                if pbar.n + records_fetched > pbar.total:
                    pbar.total += records_fetched
                pbar.update(records_fetched)
                        
        if 'error' in pageData:
            print(f"Error in response: {pageData['error']}")
            return []

        #with open('data/online_request.json', 'w') as f:
        #    json.dump(data, f)

        #print("Loading Data...")
        #decks_data = self.load_data('data/online_request.json')
        if 'Items' in all_decks:     return all_decks['Items']
        else:                   return all_decks
       
    def handle_response(self, data, type):
        decks_data = data

        # if type == 'fuseddeck':
        #     fusions, incomplete_fusionsdata = self.ucl.load_fusions(decks_data)

        #     incomplete_decks_data = []
        #     # Fetch the incomplete decks
        #     for incomplete_fusiondata in incomplete_fusionsdata:
        #         fusion_decks = []                
        #         for incomplete_deckdata in incomplete_fusiondata['myDecks']:
        #             print(f"Requesting further data: {incomplete_deckdata['id']}")
        #             deckdata = self.make_request(id=incomplete_deckdata['id'])    
        #             deck_loaded, incomplete_deckdata_loaded = self.ucl.load_decks_from_data(deckdata)                                        
        #             fusion_decks.extend(deck_loaded)
        #         if fusion_decks:
        #             fusions.append(Fusion(incomplete_fusiondata['name'], fusion_decks))                                                    
        #     return fusions
        # else:
            #decks, incompletes = self.ucl.load_decks_from_data(decks_data)
            #return decks_data


    def request_decks(self, id="", type="deck", username="TMind", filename=None):
        if id.startswith('Fused'):  type = 'fuseddeck'         
        decks_data = self.make_request(id, type, username)
        #decks_data = self.handle_response(data, type)        

        return decks_data

    def load_data(self, filename):
        with open(filename, 'r') as f:
            content = f.read()
            data = json.loads(content)

        if 'Items' in data:
            return data['Items']
        else:                                
            return [data]