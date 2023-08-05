from DeckLibrary    import DeckLibrary
from Card_Library   import UniversalCardLibrary
from CacheManager   import CacheManager
from Synergy        import SynergyTemplate
from NetApi         import NetApi
import Evaluation as ev
import Graph
import argparse
import sys
import os
from appdirs import user_data_dir
from pathlib import Path
from CacheManager import CacheManager


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

    ucl = os.path.join(cacheFolder,'ucl.pkl')
    deckLibrary = os.path.join(cacheFolder,deck_library_name + '.pkl')
    graphFolder = os.path.join(cacheFolder,eval_graphs_name + '.pkl')

    file_mappings = {
        ucl : [os.path.join(dataFolder,'sff.csv'), os.path.join(dataFolder,'forgeborn.csv')],
        deckLibrary : [ucl],
       graphFolder: [deckLibrary],
    }

    cache_manager = CacheManager(file_mappings)

    # Initialize synergy template singleton with optional file
    SynergyTemplate(args.synergies)

    myUCL = cache_manager.load_or_create('cache/ucl.pkl', lambda: UniversalCardLibrary(file_mappings['cache/ucl.pkl'][0],file_mappings['cache/ucl.pkl'][1]))

    myApi = NetApi()
    net_decks = myApi.request_decks(
        id=args.id,
        type=args.type,
        username=args.username,
        filename=args.filename
    )

    local_decks = []
    if not args.username and not args.id:
        local_decks, incompletes = myUCL.load_decks_from_file(f"data/{args.filename}.json")

    DeckCollection = cache_manager.load_or_create(deckLibrary, lambda: DeckLibrary(local_decks))

    DeckCollection.update(net_decks)
    cache_manager.save_object_to_cache(deckLibrary, DeckCollection)

    if args.eval:
        eval_filename = None
        if args.eval is not True:
            eval_filename = args.eval

        egraphs = cache_manager.load_object_from_cache(graphFolder) or {}

        new_graphs = False
        
        for name, fusion in DeckCollection.library['Fusion'].items():
            if name not in egraphs:
                DeckGraph = Graph.create_deck_graph(fusion)
                ev.evaluate_graph(DeckGraph)
                egraphs[name] = DeckGraph
                new_graphs = True

        if new_graphs:
            cache_manager.save_object_to_cache(graphFolder, egraphs)

        if args.filter:
            
            eligible_graphs = {}
            for name, graph in egraphs.items():
                if Graph.is_eligible(graph,args.filter):
                    eligible_graphs[name] = graph

            egraphs = eligible_graphs

        for name, EGraph in egraphs.items():            
            Graph.print_graph(EGraph, eval_filename)

            if args.graph:
                eval_path = Path(eval_filename)
                gefxFolder = os.path.join(eval_path.parent.absolute(),"gefx")
                Path(gefxFolder).mkdir(parents=True, exist_ok=True)

                Graph.write_gexf_file(EGraph, gefxFolder, name.replace('|', '_'))

        if eval_filename:
            print(f"Exporting evaluated fusions to csv: {eval_filename}.csv")
            ev.export_csv(eval_filename + '_excl', egraphs, True)
            ev.export_csv(eval_filename, egraphs, False)

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



