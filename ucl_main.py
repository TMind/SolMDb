from stat import FILE_ATTRIBUTE_REPARSE_POINT
import requests
import json
import csv
from Evaluation import Evaluation
import Graph
from collections import defaultdict
from DeckLibrary import DeckLibrary
from Card_Library import UniversalCardLibrary
from Synergy import SynergyTemplate


synergy_template = SynergyTemplate()

rows = [ 'MAGE', 'SPELL', 'FREE', 'FREE SPELL' ]
synergy_template.set_synergy_rows(rows)

# Read entities from CSV and create universal card library
myUCL = UniversalCardLibrary('sff.csv', synergy_template)

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
    EvaluatedGraphs = {}
    DeckCollection = DeckLibrary(list(decks.values()), synergy_template)    
    for fusion in DeckCollection.fusions:
        deck_name = fusion.name
        #half_deck = 'Vindicators of Sobbing and Baking'
        deck_name = "The Hurting Demons Larvae|Doctors of Tatoo and Comparing"
        #if half_deck in fusion.name :
        if deck_name == fusion.name :

            DeckGraph = Graph.create_deck_graph(fusion)        
            EvaluatedGraphs[DeckGraph.graph['name']] = DeckGraph  
            print(f"\nFusion: {fusion.name}\n")
            Graph.print_graph(DeckGraph)                  
            Graph.write_gephi_file(DeckGraph,deck_name.replace('|','_'))        

if (0):
   # Open the csv file in write mode and write the header row
    with open("deck_metrics.csv", "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["deckname", "value", "katz", "degree", "density", "cluster_coeff", "between"], delimiter=';')
        writer.writeheader()

        for i, (key, EGraph) in enumerate(EvaluatedGraphs.items()):            

            Metrics = {
                "katz"      : 0 ,
#                "PageRank"  : 0 ,
                "degree"    : 0 ,
                "between"   : 0 
            }

            name  = EGraph.graph['name']
            #mod   = EGraph.graph['mod']
            value = EGraph.graph['value']            
            density = EGraph.graph['density'] 
            cluster_coeff = EGraph.graph['cluster_coeff']
            #final = value / mod            


            for metric in Metrics:       
                Metrics[metric] = sum([ EGraph.nodes[node_name][metric] for node_name in EGraph.nodes]) 

          
            writer.writerow({
                "deckname": name,
             #   "modularity": f"{mod:.4f}",
                "value": f"{value:.4f}",
                #"final": f"{final:.4f}",
                "katz": f"{Metrics['katz']:.4f}",
             #   "PageRank": f"{Metrics['PageRank']:.4f}",
                "degree": f"{Metrics['degree']:.4f}",
                "density": f"{density:.4f}",
                "cluster_coeff": f"{cluster_coeff:.4f}",
                "between": f"{Metrics['between']:.4f}"
            })






