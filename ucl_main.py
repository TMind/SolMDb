from stat import FILE_ATTRIBUTE_REPARSE_POINT
import requests
import json
import csv
import Evaluation as ev
import Graph
from collections import defaultdict
from DeckLibrary import DeckLibrary
from Card_Library import UniversalCardLibrary
from Synergy import SynergyTemplate
from NetApi import NetApi


rows = [ 'REPLACE' , 'AGGRO', 'FREE UPGRADE', 'ARMOR', 'FREE REPLACE', 'UPGRADE' ]
synergy_template = SynergyTemplate()
synergy_template.set_synergy_rows(rows)

decks = []

if (1) :
    myApi = NetApi()

    #params = {"username": "TMind"}        
    decks = myApi.request_decks("c9lfreiu5jkhnblp8tptvqaiqv3ter")

else:
    # Read entities from CSV and create universal card library
    myUCL = UniversalCardLibrary('sff.csv')#, synergy_template)
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

EvaluatedGraphs = {}

if (1):        
    DeckCollection = DeckLibrary(list(decks.values()), synergy_template)    
    
    for fusion in DeckCollection.fusions:
        deck_name = fusion.name
        #half_deck = 'The Aunts of Bleeding Brightsteel'
        #deck_name = "The Mixing Figment Collectors|The People of Bearing"
        #if half_deck in fusion.name :
        if deck_name == fusion.name :

            DeckGraph = Graph.create_deck_graph(fusion, ev.calculate_weight)        
            ev.evaluate_graph(DeckGraph)
            EvaluatedGraphs[DeckGraph.graph['name']] = DeckGraph  
            print(f"\nFusion: {fusion.name}\n")
            #Graph.print_graph(DeckGraph)                  
            #Graph.write_gephi_file(DeckGraph,deck_name.replace('|','_'))     
            #Graph.edge_statistics(DeckGraph)   

    ev.find_best_pairs(EvaluatedGraphs)

if (0):
    ev.export_csv('deck_metrics', EvaluatedGraphs)
   






