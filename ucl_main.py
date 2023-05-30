from stat import FILE_ATTRIBUTE_REPARSE_POINT
import csv
import Evaluation as ev
import Graph
from collections import defaultdict
from DeckLibrary import DeckLibrary
from Card_Library import UniversalCardLibrary
from Synergy import SynergyTemplate
from NetApi import NetApi



#rows = [ 'REPLACE' , 'WARRIOR', 'ACTIVATION', 'REDEPLOY', 'REACTIVATION' ,'AGGRO', 'FREE UPGRADE', 'FREE REPLACE', 'UPGRADE' ]
#synergy_template = SynergyTemplate()
#synergy_template.set_synergy_rows(rows)

decks = []

if (1) :
    myApi = NetApi()
        
    #decks = myApi.request_decks()
    decks = myApi.request_decks(type='fuseddeck', filename='fusions')
    #decks = myApi.request_decks(id='Fused_d7w2v8li1eyb45',filename='heartseeker')
    #decks = myApi.request_decks(id='d5zenofhekurl3sn7iotspbdqn3qrx' )

else:
    # Read entities from CSV and create universal card library
    myUCL = UniversalCardLibrary('csv/sff.csv')#, synergy_template)
    decks, incompletes = myUCL.load_decks_from_file('data/deck_base.json')

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
    DeckCollection = DeckLibrary(decks)    
    
    half_deck = 'The Fortelling Aggravating Ticklers'
    for fusion in DeckCollection.fusions:
        deck_name = fusion.name
        half_deck = 'The Raiders of Hound and Mask'
        deck_name = fusion.name        
        #deck_name = "The Mixing Figment Collectors|The People of Bearing"
        #if half_deck in fusion.name :
        if deck_name == fusion.name :
            mode = 0
            print(f"\nFusion: {fusion.name}\n")
            DeckGraph = Graph.create_deck_graph(fusion, ev.calculate_weight,mode=mode)        
            ev.evaluate_graph(DeckGraph)
            EvaluatedGraphs[DeckGraph.graph['name']] = DeckGraph              
            Graph.print_graph(DeckGraph)                  
            Graph.write_gephi_file(DeckGraph,deck_name.replace('|','_'))     
            print(f"\n========================================================\n")
            #Graph.edge_statistics(DeckGraph)   
            print(f"Provides: {fusion.provides}")
            print(f"Seeks: {fusion.seeks}")

    ev.find_best_pairs(EvaluatedGraphs)

if (1):
    ev.export_csv('fusion_metrics', EvaluatedGraphs)
   






