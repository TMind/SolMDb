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
from queue import Queue
from concurrent.futures import ProcessPoolExecutor, as_completed

def main(args):

    #if we wanted to move stuff into app bundle on a mac we'd do this
    #if sys.platform == 'darwin':
    #    resourcePath =  os.path.join(os.environ['RESOURCEPATH'],"data")
    #else:

    # Initialize synergy template singleton with optional file
    SynergyTemplate()
    cache_manager = cache_init(args)

    card_dependencies = cache_manager.get_dependencies('CardLib')
    myUCL = cache_manager.load_or_create('CardLib', lambda: UniversalCardLibrary(*card_dependencies))


#   Evaluation type  
#   - collection / fusion / halfdeck 

    SelectionType = 'Collection'
    if args.id : 
        if args.type == 'deck':
            SelectionType = 'Deck'
        elif args.type == 'fuseddeck':
            SelectionType = 'Fusion'    

    
    DeckCollection = DeckLibrary([])
    net_decks = []

    if args.offline or SelectionType == 'Collection':
        DeckCollection = cache_manager.load_or_create('DeckLib', lambda: DeckLibrary([]))

    if not args.offline:

        myApi = NetApi(myUCL)
        net_decks = myApi.request_decks(
            id=args.id,
            type=args.type,
            username=args.username,
            filename=args.filename
        )
  

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

        # Apply the filter:      
        net_decks   = col_filter.apply(net_decks)

        DeckCollection.filter(col_filter)

   # elif SelectionType == 'Collection':
   #     DeckCollection = cache_manager.load_or_create(deckLibrary, lambda: DeckLibrary([]))

    DeckCollection.update(net_decks)

    if SelectionType == 'Collection' and not col_filter:
        cache_manager.save_object_to_cache("DeckLib", DeckCollection)


    eval_filename = None
    if args.eval:
        if args.eval is not True:
            eval_filename = args.eval

        egraphs = {}

        
        #if SelectionType == 'Collection' and not col_filter:
        local_graphs = cache_manager.load_object_from_cache('GraphLib') or {}

        # queue = Queue()
        new_graphs = 0
        
        # with ProcessPoolExecutor() as executor:
        #     futures = [executor.submit(process_fusion, name, fusion, idx, egraphs, queue)
        #             for name, fusion in DeckCollection.library['Fusion'].items()
        #             for idx in range(2)]
            
        #     progress_bar = tqdm(total=len(futures), desc="Creating Fusion Graphs", mininterval=0.1, colour='BLUE')
            
        #     for _ in as_completed(futures):
        #         new_graphs = queue.get()
        #         progress_bar.update(new_graphs)
            
        #     progress_bar.close()


        lib_fusions = DeckCollection.library['Fusion']

        if col_filter:
            lib_fusions   = col_filter.apply(lib_fusions)

        progress_bar = tqdm(total=len(lib_fusions)*2, desc="Creating Fusion Graphs", mininterval=0.1, colour='BLUE')
        for name, fusion in lib_fusions.items():
            for idx in range(2):  # since there are 2 forgeborn_options for each fusion
                
                # Set the active Forgeborn for this Fusion
                fusion.set_forgeborn(idx)
                
                # Create a unique name for each graph, based on the Fusion's name and the active Forgeborn's name               
                FusionGraph = local_graphs.get(fusion.name)

                if not FusionGraph:                                                                          
                    # Create and evaluate the graph
                    FusionGraph = Graph.create_deck_graph(fusion)
                    ev.evaluate_graph(FusionGraph)
                    
                    # Store the graph in the egraphs dictionary
                    local_graphs[FusionGraph.graph['name']] = FusionGraph
                    
                    # Update the progress bar and increment the new_graphs counter                                        
                    new_graphs += 1
                    progress_bar.update(1)

                #Store the Graph in the output dictionary
                egraphs[FusionGraph.graph['name']] = FusionGraph

            time.sleep(0.001)
        progress_bar.close()

        #Store the graph library if new graphs have been added 
        if new_graphs > 0 and SelectionType == 'Collection':
                cache_manager.save_object_to_cache('GraphLib', local_graphs)
        

        #Evaluate single decks 
        total_decks  = len(DeckCollection.library['Deck'])
        progress_bar = tqdm(total=total_decks, desc="Creating Deck Graphs",mininterval=0.1, colour='CYAN')
        dgraphs = {}
        for name, deck in DeckCollection.library['Deck'].items():
            if name not in dgraphs:
                DeckGraph = Graph.create_deck_graph(deck)
                ev.evaluate_graph(DeckGraph)
                dgraphs[name] = DeckGraph                
            time.sleep(0.001)
            progress_bar.update(1)            
        progress_bar.close()

        #Print Graph relations in file / gefx 
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
            ev.export_csv(eval_filename + '_excl', egraphs, True)
            ev.export_csv(eval_filename, egraphs, False)
            ev.export_csv(eval_filename + '.hd', dgraphs, False)

        if args.select_pairs:
            if not eval_filename: eval_filename = 'evaluation'
            print("Selecting top unique pairs\n")
            ev.find_best_pairs(egraphs,eval_filename + '_top_pairs.txt')

def cache_init(args):
    """
    Initialize the cache system based on the given arguments.

    Parameters:
    - args: Arguments containing username, filename, eval, and other potential configurations.

    Returns:
    - CacheManager instance initialized with the correct file mappings.
    """
    resourcePath = os.path.dirname(__file__)
    cacheFolder = os.path.join(resourcePath, "cache")
    dataFolder = os.path.join(resourcePath, "csv")
    
    # ensure folders exist
    Path(cacheFolder).mkdir(parents=True, exist_ok=True)
    Path(dataFolder).mkdir(parents=True, exist_ok=True)

    deck_library_name = "deck_library"
    eval_graphs_name = "eval_graphs"

    if args.username:
        deck_library_name += f"_{args.username}"
        eval_graphs_name  += f"_{args.username}"
        args.eval         += f"_{args.username}"

    if args.filename:
        deck_library_name = f"{args.filename}_library"
        eval_graphs_name = f"{args.filename}_graphs"
    
    ucl_path = os.path.join(cacheFolder,'ucl.zpkl')
    deckLibrary_path = os.path.join(cacheFolder,deck_library_name + '.zpkl')
    graphFolder_path = os.path.join(cacheFolder,eval_graphs_name + '.zpkl')

    # File paths mapping
    file_paths = {
        "CardLib": ucl_path,
        "DeckLib": deckLibrary_path,
        "GraphLib": graphFolder_path,
    }

    # Dependencies mapping
    dependencies = {
        "CardLib": [os.path.join(dataFolder, 'sff.csv'), os.path.join(dataFolder, 'forgeborn.csv')],
        "DeckLib": ["CardLib"],
        "GraphLib": ["DeckLib"],
    }

    return CacheManager(file_paths, dependencies)

# Parallelization Code

def process_fusion(name, fusion, idx, egraphs, queue):
    fusion.set_forgeborn(idx)
    graph_name = f"{name}_{fusion.active_forgeborn.name}"
    
    if egraphs.get(graph_name) is None:
        FusionGraph = Graph.create_deck_graph(fusion)
        ev.evaluate_graph(FusionGraph)
        egraphs[graph_name] = FusionGraph
        queue.put(1)
    else:
        queue.put(0)

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
    parser.add_argument("--offline", default=None, help="Offline use only")    

    # Arguments for Evaluation
    
    parser.add_argument("--eval", nargs='?', const=True, action="store",  help="Evaluate possible fusions. Optional filename for .csv export")    
    parser.add_argument("--graph", action="store_true",  help="Create Graph '.gefx'")
    parser.add_argument("--filter", default=None, help="Filter by card names. Syntax: \"<cardname>+'<card name>'-<cardname>\" + = AND, - = OR ")
    parser.add_argument("--select_pairs", action="store_true", help="Select top pairs")
    
    # Parse the command-line arguments
    args = parser.parse_args()

    main(args)



