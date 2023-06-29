from attr import dataclass
import requests
import json
from Card_Library import UniversalCardLibrary, Fusion
from typing import List, Tuple, Dict


class NetApi:

    def __init__(self, csvfile=None):
        self.csvfile = csvfile or 'csv/sff.csv'
        self.ucl = UniversalCardLibrary(self.csvfile, 'csv/forgeborn.csv')
        self.base_url = "https://ul51g2rg42.execute-api.us-east-1.amazonaws.com/main"
        self.params = {
            "inclCards": "true",
            "inclDecks": "true",
            "inclCategories": "true",
            "username": "TMind", 
        }        

    def make_request(self, id="", type="deck", username="TMind"):
        
        endpoint = f"{self.base_url}/{type}/{id}"

        self.params.update({"username" : username})
        print(f"Requesting Data from Website: {','.join([username,type,id])}")
        response = requests.get(endpoint, params=self.params)        
        data = json.loads(response.content)

        #insert pagination code

        if "LastEvaluatedKey" in data:
            paginatationRequired = True
        else:
            paginatationRequired = False

        while paginatationRequired == True:
            self.params["exclusiveStartKey"] = json.dumps(data['LastEvaluatedKey'])
            page_response = requests.get(endpoint, params=self.params)
            page_data = json.loads(page_response.content)
            if 'error' in page_data:
                print(f"Error in response: {page_data['error']}")
                return []
            data["Items"].extend(page_data["Items"])
            if "LastEvaluatedKey" in page_data:
                data["LastEvaluatedKey"] = page_data["LastEvaluatedKey"]
            else:
                paginatationRequired = False
                
        #end pagination code

        if 'error' in data:
            print(f"Error in response: {data['error']}")
            return []

        with open('data/online_request.json', 'w') as f:
            json.dump(data, f)

        print("Loading Data...")
        decks_data = self.ucl.load_data('data/online_request.json')
        return decks_data

    def handle_response(self, data, type):
        decks_data = data

        if type == 'fuseddeck':
            fusions, incomplete_fusionsdata = self.ucl.load_fusions(decks_data)

            incomplete_decks_data = []
            # Fetch the incomplete decks
            for incomplete_fusiondata in incomplete_fusionsdata:
                fusion_decks = []                
                for incomplete_deckdata in incomplete_fusiondata['myDecks']:
                    print(f"Requesting further data: {incomplete_deckdata['id']}")
                    deckdata = self.make_request(id=incomplete_deckdata['id'])    
                    deck_loaded, incomplete_deckdata_loaded = self.ucl.load_decks_from_data(deckdata)                                        
                    fusion_decks.extend(deck_loaded)
                if fusion_decks:
                    fusions.append(Fusion(incomplete_fusiondata['name'], fusion_decks))                                                    
            return fusions
        else:
            decks, incompletes = self.ucl.load_decks_from_data(decks_data)
            return decks


    def request_decks(self, id="", type="deck", username="TMind", filename=None):
        if id.startswith('Fused'):  type = 'fuseddeck'         
        decks_data = self.make_request(id, type, username)
        decks = self.handle_response(decks_data, type)

        if filename:
            deck_data = [deck.to_json() for deck in decks]
            filepath = f"data/{filename}.json"
            with open(filepath, "w") as f:
                json.dump(deck_data, f)
                print(f"Dumped deck data to: {filepath}")

        return decks
