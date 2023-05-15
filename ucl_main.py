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
        deck_name = 'The Hurting Demons Larvae|The Omnivore Brutish Herders'
        if fusion.name == deck_name:
            DeckGraph = Graph.create_deck_graph(fusion)        
            EvaluatedGraphs[DeckGraph.graph['name']] = DeckGraph        
            Graph.write_gephi_file(DeckGraph,deck_name.replace('|','_'))        

if (0):
   # Open the csv file in write mode and write the header row
    with open("deck_metrics.csv", "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["deckname", "modularity", "value", "final", "katz", "PageRank", "degree", "between"], delimiter=';')
        writer.writeheader()

        for i, (key, EGraph) in enumerate(EvaluatedGraphs.items()):            

            Metrics = {
                "katz"      : 0 ,
                "PageRank"  : 0 ,
                "degree"    : 0 ,
                "between"   : 0 
            }

            name  = EGraph.graph['name']
            mod   = EGraph.graph['mod']
            value = EGraph.graph['value']            
            final = value / mod            


            for metric in Metrics:       
                Metrics[metric] = sum([ EGraph.nodes[node_name][metric] for node_name in EGraph.nodes]) 

          
            writer.writerow({
                "deckname": name,
                "modularity": f"{mod:.4f}",
                "value": f"{value:.4f}",
                "final": f"{final:.4f}",
                "katz": f"{Metrics['katz']:.4f}",
                "PageRank": f"{Metrics['PageRank']:.4f}",
                "degree": f"{Metrics['degree']:.4f}",
                "between": f"{Metrics['between']:.4f}"
            })






