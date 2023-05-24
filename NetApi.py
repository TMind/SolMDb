from attr import dataclass
import requests
import json
from Card_Library import UniversalCardLibrary, Fusion


class NetApi:

    def __init__(self, csvfile=None):
        self.csvfile = csvfile or 'sff.csv'
        self.ucl = UniversalCardLibrary(self.csvfile)
        self.base_url = "https://ul51g2rg42.execute-api.us-east-1.amazonaws.com/main"
        self.params = {
            "inclCards": "true",
            "inclDecks": "true",
            "username": "TMind",
        }        

    def make_request(self, id="", type="deck", username="TMind"):
        if id.startswith('Fused'):
            type = 'fuseddeck'         

        endpoint = f"{self.base_url}/{type}/{id}"

        self.params.update({"username" : username})
        
        response = requests.get(endpoint, params=self.params)
        data = json.loads(response.content)

        with open('online_request.json', 'w') as f:
            json.dump(data, f)

        decks_data = self.ucl.load_online('online_request.json')
        return decks_data

    def handle_response(self, data, type):
        decks_data = data

        if type == 'fuseddeck':
            fusions, incomplete_fusions = self.ucl.load_fusions(decks_data)

            # Fetch the incomplete decks
            for incomplete_fusion in incomplete_fusions:
                fusion_data = {'myDecks' : []}
                for deck_data in incomplete_fusion['myDecks']:
                    data = self.make_request(id=deck_data['id'])                
                    fusion_data['myDecks'].extend(self.ucl.load_decks(data))
                complete_fusion, incomplete_fusion_data = self.ucl.load_fusions([fusion_data])
                if incomplete_fusion_data:
                    incomplete_fusions.extend(incomplete_fusion_data)    
                if complete_fusion:
                    fusions.extend(complete_fusion)

            return fusions
        else:
            decks = self.ucl.load_decks(decks_data)
            return decks


    def request_decks(self, id="", type="deck", username="TMind", filename=None):
        decks_data = self.make_request(id, type, username)
        decks = self.handle_response(decks_data, type)

        if filename:
            deck_data = [deck.to_json() for deck in decks]
            with open(f"{filename}.json", "w") as f:
                json.dump(deck_data, f)

        return decks





    # def request_decks(self, id="", type="deck", username="TMind", filename=None):
                
    #     if id.startswith('Fused') :
    #         type = 'fuseddeck'         

    #     endpoint = f"{self.base_url}/{type}/{id}"

    #     self.params.update({"username" : username})
        
    #     response = requests.get(endpoint, params=self.params)
    #     data = json.loads(response.content)

    #     with open('online_request.json', 'w') as f:
    #         json.dump(data, f)

    #     if type=='fuseddeck' and id=="":
    #         # Request each deck separately 
    #         fusions = []            
    #         for fused_deck in decks:                
    #             # Getting the individual decks from the fused deck
    #             fusion_decks = []
    #             for deck_id in fused_deck.decks:
    #                 deck = self.request_decks(id=deck_id)
    #                 fusion_decks.append(deck)
    #             name = "|".join(deck.name for deck in fused_deck.decks)
    #             fusions.append(Fusion(name,fusion_decks))
    #         # Replace decks with the full decks
    #         decks = fusions
    #     else:
    #         decks = self.ucl.load_online('online_request.json', type)        
            
    #     if filename:
    #         deck_data = [deck.to_json() for deck in decks]
    #         with open(f"{filename}.json", "w") as f:
    #              json.dump(deck_data, f)

    #         #decks = self.ucl.load_offline('online_dump.json')

    #     return decks
