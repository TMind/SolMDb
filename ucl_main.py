import requests
import json
import csv
import Graph
from collections import defaultdict
from DeckLibrary import DeckLibrary
from Card_Library import UniversalCardLibrary

# Read entities from CSV and create universal card library
myUCL = UniversalCardLibrary('sff.csv')

if (0):
    url = "https://ul51g2rg42.execute-api.us-east-1.amazonaws.com/main/deck/"
    params = {
        "pageSize": "100",
        "inclCards": "true",
        "username": "TMind"
    }
    response = requests.get(url, params=params)
    data = json.loads(response.content)
    #Write the JSON data to a file
    with open('decks_onl.json', 'w') as f:
        json.dump(data, f)

    decks = myUCL.load_decks_online('decks.json')    

    deck_data = [deck.to_json() for deck in decks]
    with open("decks_off.json", "w") as f:
        json.dump(deck_data, f)

decks = myUCL.load_decks('card_base.json')
if (0):
    DeckCollection = DeckLibrary(list(decks.values()))    
    DeckCollection.print_fusion_synergies()
    #DeckCollection.get_best_synergies()

if (0):
    forgeborn_abilities = defaultdict(list)
    for fusion in decks.values():
        forgeborn_abilities[fusion.forgeborn.title].append(fusion.forgeborn.abilities)

    with open('forgeborn.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Forgeborn Name', 'Ability Name', 'Ability Value'])
        for name, abilities_list in forgeborn_abilities.items():
            for abilities in abilities_list:
                for ability, value in abilities.items():
                    writer.writerow([name, ability, value])

if (1):

    SynergyGraph = Graph.create_synergy_graph(decks)
    #Graph.plot_synergy_graph(SynergyGraph)
    Graph.write_gephi_file(SynergyGraph,'mygraph')





