import requests

import json

from Card_Library import UniversalCardLibrary



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


    def request_decks(self, id="", type="deck", username="TMind"):
                

        if id.startswith('Fused') :

            type = 'fuseddeck'         


        endpoint = f"{self.base_url}/{type}/{id}"


        self.params.update({"username" : username})
        

        response = requests.get(endpoint, params=self.params)

        data = json.loads(response.content)


        with open('online_request.json', 'w') as f:

            json.dump(data, f)



        # Format 

        # 1. Single Deck  -> List of cards []

        # 2. Single Fusion-> List of decks        [myDecks]

        # 3. All Decks    -> List of decks [Items]

        # 4. All Fusions  -> List of decks [Items][myDecks]


        decks = self.ucl.load_online('online_request.json')


        deck_data = [deck.to_json() for deck in decks]

        with open("online_dump.json", "w") as f:

            json.dump(deck_data, f)


        return self.ucl.load_decks('online_dump.json')

