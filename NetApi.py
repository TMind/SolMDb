import requests
import json
from Card_Library import UniversalCardLibrary


class NetApi:

    def __init__(self, csvfile=None):
        self.csvfile = csvfile or 'sff.csv'
        self.ucl = UniversalCardLibrary(self.csvfile)
        self.base_url = "https://ul51g2rg42.execute-api.us-east-1.amazonaws.com/main/deck"
        self.params = {
            "inclCards": "true",
            "inclDecks": "true",
        }

    def request_decks(self, deck_id=None, params=None):
        format = 'list'
        if deck_id:
            format = 'deck'
            url = f"{self.base_url}/{deck_id}"
        else:
            url = self.base_url

        if params:
            self.params.update(params)

        response = requests.get(url, params=self.params)
        data = json.loads(response.content)

        with open('online_request.json', 'w') as f:
            json.dump(data, f)

        decks = self.ucl.load_decks_online('online_request.json', format)

        deck_data = [deck.to_json() for deck in decks]
        with open("online_dump.json", "w") as f:
            json.dump(deck_data, f)

        return self.ucl.load_decks('online_dump.json')
