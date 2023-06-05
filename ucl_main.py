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

fuse_ids = [
                "Fused_dqokp8lfim2phb" ,
                "Fused_j728lhp7bfn3",
                "Fused_3clxc8li57p672" ,
                "Fused_50ttb8lhr0bez6" ,
                "Fused_gdtqzr8liexxxfn" ,
                "Fused_1o56eez9lhxfp8ad" ,
                "Fused_3rmme9p8lhuffjk1" ,
                "Fused_49hs8208lif126jb" ,
                "Fused_49hs8208lif0uaey" ,
# ------------------------------------------
                "Fused_49hs8208lif0ny9b" ,
                "Fused_r695av8lhdvo0qv" ,
                "Fused_1nuxiwe8lg8d9t7v" ,
                "Fused_qru608lifpopix" ,
                "Fused_51xv8lia8iime" ,
                "Fused_49hs8208lif1hcbl" ,
                "Fused_3pnz7o8lgc8dl69" ,
                "Fused_49hs8208lif1cqad" ,
                "Fused_49hs8208lif13z45" 
]


decks = []

if (1) :
    myApi = NetApi()
        
    #decks = myApi.request_decks()
    decks = myApi.request_decks(type='fuseddeck', filename='fusions')
    
    #decks = myApi.request_decks(type='fuseddeck', id='Fused_heetw8lieyqwuq')
    #for id in fuse_ids:  decks.extend(myApi.request_decks(type='fuseddeck', id=id))
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
    
    half_deck = 'The Professing Watchdogs'
    for fusion in DeckCollection.fusions:
        deck_name = fusion.name
        #deck_name = "The Mixing Figment Collectors|The People of Bearing"
        #if half_deck in fusion.name :
        if deck_name == fusion.name :        
            print(f"\nFusion: {fusion.name}\n")
            DeckGraph = Graph.create_deck_graph(fusion)        
            ev.evaluate_graph(DeckGraph)
            EvaluatedGraphs[DeckGraph.graph['name']] = DeckGraph              
            Graph.print_graph(DeckGraph)                  
            #Graph.write_gephi_file(DeckGraph,deck_name.replace('|','_'))                 
            #Graph.edge_statistics(DeckGraph)   
            yesorno = all(key in fusion.provides for key in fusion.seeks)
            print(f"Provides: {fusion.provides}")
            print(f"{yesorno} Seeks: {fusion.seeks}")            
            print(f"Rarities: {fusion.get_rarities()}")
            
            print(f"\n========================================================\n")

    ev.find_best_pairs(EvaluatedGraphs)

if (0):
    ev.export_csv(half_deck + '_excl', EvaluatedGraphs, True)
    ev.export_csv(half_deck, EvaluatedGraphs, False)
   






