from DeckLibrary    import DeckLibrary
from Card_Library   import UniversalCardLibrary
from CacheManager   import CacheManager
from Synergy        import SynergyTemplate
from NetApi         import NetApi
from Filter import Filter
import Evaluation as ev
import Graph
import argparse
from tqdm import tqdm 
import os, time, re
from appdirs import user_data_dir
from pathlib import Path


def main(args):

    #if we wanted to move stuff into app bundle on a mac we'd do this
    #if sys.platform == 'darwin':
    #    resourcePath =  os.path.join(os.environ['RESOURCEPATH'],"data")
    #else:

    resourcePath = os.path.dirname(__file__)

    cacheFolder = os.path.join(resourcePath,"cache")
    dataFolder = os.path.join(resourcePath,"csv")

    #make sure needed folders exist
    Path(cacheFolder).mkdir(parents=True, exist_ok=True)
    Path(dataFolder).mkdir(parents=True, exist_ok=True)


    deck_library_name = "deck_library"
    eval_graphs_name = "eval_graphs"

    if args.username:
        deck_library_name += f"_{args.username}"
        eval_graphs_name += f"_{args.username}"

    if args.filename:
        deck_library_name = f"{args.filename}_library"
        eval_graphs_name = f"{args.filename}_graphs"

    ucl = os.path.join(cacheFolder,'ucl.zpkl')
    deckLibrary = os.path.join(cacheFolder,deck_library_name + '.zpkl')
    graphFolder = os.path.join(cacheFolder,eval_graphs_name + '.zpkl')

    file_mappings = {
        ucl : [os.path.join(dataFolder,'sff.csv'), os.path.join(dataFolder,'forgeborn.csv')],
        deckLibrary : [ucl],
       graphFolder: [deckLibrary],
    }

    cache_manager = CacheManager(file_mappings)

    # Initialize synergy template singleton with optional file
    SynergyTemplate()
    
    myUCL = cache_manager.load_or_create(ucl, lambda: UniversalCardLibrary(file_mappings[ucl][0],file_mappings[ucl][1]))

    myApi = NetApi()
    net_decks = myApi.request_decks(
        id=args.id,
        type=args.type,
        username=args.username,
        filename=args.filename
    )

#   Evaluation type  
#   - collection / fusion / halfdeck 

    SelectionType = 'Collection'
    if args.id : 
        if args.type == 'deck':
            SelectionType = 'Deck'
        elif args.type == 'fuseddeck':
            SelectionType = 'Fusion'    
        
    local_decks = []

    if args.filename:
    #if not args.username and not args.id:
        local_decks, incompletes = myUCL.load_decks_from_file(f"data/{args.filename}.json")

    DeckCollection = DeckLibrary([])

    col_filter = None
    if args.filter:

        # Example usage:
        query = args.filter
        attribute_map = {
            'F'     : ('faction', str),
            'D'     : ('name', str),
            'FB'    : ('forgeborn.name', str),
            'C'     : ('cards', list),
            'A'     : ('forgeborn.abilities', list),
            'K'     : ('composition', dict),            
        }
        col_filter = Filter(query, attribute_map) 

        # To apply the filter:
       #filtered_objects = filter.apply(some_objects)
        local_decks = col_filter.apply(local_decks)    
        net_decks   = col_filter.apply(net_decks)

    elif SelectionType == 'Collection':
        DeckCollection = cache_manager.load_or_create(deckLibrary, lambda: DeckLibrary(local_decks))

    DeckCollection.update(net_decks)

    if SelectionType == 'Collection' and not col_filter:
        cache_manager.save_object_to_cache(deckLibrary, DeckCollection)


    eval_filename = None
    if args.eval:
        if args.eval is not True:
            eval_filename = args.eval

        egraphs = {}
        if SelectionType == 'Collection' and not col_filter:
            egraphs = cache_manager.load_object_from_cache(graphFolder) or {}

        new_graphs = 0
        
        total_fusions = len(DeckCollection.library['Fusion'])
        progress_bar = tqdm(total=total_fusions, desc="Creating Fusion Graphs",mininterval=0.1, colour='BLUE')

        for name, fusion in DeckCollection.library['Fusion'].items():
            if name not in egraphs:
                FusionGraph = Graph.create_deck_graph(fusion)
                ev.evaluate_graph(FusionGraph)
                egraphs[name] = FusionGraph                
            time.sleep(0.001)
            progress_bar.update(1)
            new_graphs += 1
        progress_bar.close()

        total_decks  = len(DeckCollection.library['Deck'])
        progress_bar = tqdm(total=total_decks, desc="Creating Fusion Graphs",mininterval=0.1, colour='CYAN')

        dgraphs = {}
        for name, deck in DeckCollection.library['Deck'].items():
            if name not in dgraphs:
                DeckGraph = Graph.create_deck_graph(deck)
                ev.evaluate_graph(DeckGraph)
                dgraphs[name] = DeckGraph                
            time.sleep(0.001)
            progress_bar.update(1)
            new_graphs += 1
        progress_bar.close()


        if new_graphs > 0:
            if SelectionType == 'Collection' and not col_filter:
                cache_manager.save_object_to_cache(graphFolder, egraphs)

        # if args.filter:
            
        #     eligible_graphs = {}
        #     for name, graph in egraphs.items():
        #         if Graph.is_eligible(graph,args.filter):
        #             eligible_graphs[name] = graph

        #     egraphs = eligible_graphs
        total_graphs  = len(egraphs)
        progress_bar = tqdm(total=total_graphs, desc="Printing Fusion Graphs",mininterval=0.1, colour='YELLOW')
        for name, EGraph in egraphs.items():            
            Graph.print_graph(EGraph, eval_filename)

            if args.graph:
                eval_path = Path(eval_filename)
                gefxFolder = os.path.join(eval_path.parent.absolute(),"gefx")
                Path(gefxFolder).mkdir(parents=True, exist_ok=True)

                Graph.write_gexf_file(EGraph, gefxFolder, name.replace('|', '_'))
            progress_bar.update(1)
        progress_bar.close()
        
        if eval_filename:
            #eval_filename = f"{dataFolder}/{eval_filename}"
            #print(f"Exporting evaluated fusions to csv: {eval_filename}.csv")            
            ev.export_csv(eval_filename + '_excl', egraphs, True)
            ev.export_csv(eval_filename, egraphs, False)
            ev.export_csv(eval_filename + '.hd', dgraphs, False)

        if args.select_pairs:
            ev.find_best_pairs(egraphs,eval_filename + '_top_pairs.txt')



if __name__ == "__main__":
    # Create an argument parser
    parser = argparse.ArgumentParser(description="Script description")

    # Add command-line arguments
    # Arguments for online use 
    parser.add_argument("--username", default="", help="Online account name or omit for offline use")
    parser.add_argument("--type", default="deck", choices=["deck", "fuseddeck"], help="Decktype for user collection , default=deck")
    parser.add_argument("--id", default="", help="Specific Deck ID from solforgefusion website")
    
    # Arguments for general use 
    # If both username and file is given, export deckbase to file.json 
    # If only file is given import deckbase from file.json 
    parser.add_argument("--filename",  default=None,  help="Offline Deck Database Name")
    parser.add_argument("--synergies", default=None, help="CSV Filename for synergy lookup")    

    # Arguments for Evaluation
    
    parser.add_argument("--eval", nargs='?', const=True, action="store",  help="Evaluate possible fusions. Optional filename for .csv export")    
    parser.add_argument("--graph", action="store_true",  help="Create Graph '.gefx'")
    parser.add_argument("--filter", default=None, help="Filter by card names. Syntax: \"<cardname>+'<card name>'-<cardname>\" + = AND, - = OR ")
    parser.add_argument("--select_pairs", action="store_true", help="Select top pairs")
    
    # Parse the command-line arguments
    args = parser.parse_args()

    main(args)



