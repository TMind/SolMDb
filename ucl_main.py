from stat import FILE_ATTRIBUTE_REPARSE_POINT
import requests
import json
import csv
from Evaluation import Evaluation
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

    decks = myUCL.load_decks_online('decks_onl.json')    

    deck_data = [deck.to_json() for deck in decks]
    with open("deck_base.json", "w") as f:
        json.dump(deck_data, f)

decks = myUCL.load_decks('deck_base.json')
if (0):
    DeckCollection = DeckLibrary(list(decks.values())) 
    evaluator = Evaluation(None)
    for fusion in DeckCollection.fusions:
        evaluator.evaluate_deck(fusion) 
         
    #DeckCollection.print_fusion_synergies()
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
    #SynergyGraph = Graph.create_synergy_graph(decks)    
    EvaluatedGraphs = {}
    DeckCollection = DeckLibrary(list(decks.values()))    
    for fusion in DeckCollection.fusions:
        deck_name = fusion.name
        #deck_name = 'The Sorcerers of the Oratek Eruptor|The Hurting Demons Larvae'
        if fusion.name == deck_name:
            DeckGraph = Graph.create_deck_graph(fusion)        
            EvaluatedGraphs[DeckGraph.graph['name']] = DeckGraph
            Graph.write_gephi_file(DeckGraph,deck_name.replace('|','_'))        

if (1):
   # Open the csv file in write mode and write the header row
    with open("deck_metrics.csv", "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["deckname", "modularity", "value"])
        writer.writeheader()

        for i, (key, EGraph) in enumerate(EvaluatedGraphs.items()):
            filename = f"{EGraph.graph['name']}"
            #Graph.write_gephi_file(EvaluatedGraphs[key], filename.replace('|','_'))
           #print(f"{i+1}. {key} -> value: {EvaluatedGraphs[key].graph['value']}")
            writer.writerow({"deckname": EGraph.graph['name'], "modularity": EGraph.graph['mod'], "value": EGraph.graph['value']})
        





