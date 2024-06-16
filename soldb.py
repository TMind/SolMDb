from DeckLibrary    import DeckLibrary
from UniversalLibrary import UniversalLibrary
#from CacheManager   import CacheManager
from Synergy        import SynergyTemplate
from NetApi         import NetApi
from Filter import Filter
import Evaluation as ev
from Graph import MyGraph
import argparse
from tqdm import tqdm 
import os, time, re
from pathlib import Path
from multiprocessing import Pool, cpu_count,Event
from MongoDB.DatabaseManager import DatabaseManager
import GlobalVariables as gv

def main(args):    
    gv.username = args.username or 'Default'

    uri = "mongodb+srv://solDB:uHrpfYD1TXVzf3DR@soldb.fkq8rio.mongodb.net/?retryWrites=true&w=majority&appName=SolDB"
    gv.myDB = DatabaseManager(gv.username, uri=gv.uri)
    gv.commonDB = DatabaseManager('common', uri=gv.uri)

    synergy_template = SynergyTemplate()    
    
    ucl_paths = [os.path.join('csv', 'sff.csv'), os.path.join('csv', 'forgeborn.csv'), os.path.join('csv', 'synergies.csv')]

    #Read Entities and Forgeborns from Files into Database
    myUCL = UniversalLibrary(args.username, *ucl_paths)
    
        
    net_decks = []
    net_fusions = []

    if not args.offline:
        myApi = NetApi(myUCL)
                
        net_decks = get_net_decks(args, myApi)
        
        args.id = ''
        args.type = 'fuseddeck'
        net_fusions = get_net_decks(args, myApi)

    col_filter = get_col_filter(args)
    #DeckCollection.filter(col_filter) if col_filter else None

    DeckCollection = DeckLibrary(net_decks, net_fusions, args.mode)

    #eval_filename, egraphs, local_graphs = evaluate_fusions(args, DeckCollection)

    #evaluate_single_decks(DeckCollection, eval_filename, egraphs, local_graphs, args)

def get_net_decks(args, myApi):
    if args.id:
        urls = args.id.split('\n')
        pattern = r"\/([^\/]+)$"        
        net_data  = []
        for url in urls:
            match = re.search(pattern, url)
            if match:
                id = match.group(1)
                url_data = myApi.request_decks(
                    id=id,
                    type=args.type,
                    username=args.username,
                    filename=args.filename
                )
                net_data  += url_data                
        return net_data
    else:
        net_data = myApi.request_decks(
            id=args.id,
            type=args.type,
            username=args.username,
            filename=args.filename
        )
        return net_data

def get_col_filter(args):
    if args.filter:
        query = args.filter
        attribute_map = {
            'F': ('faction', str, None),
            'D': ('name', str, None),
            'FB': ('forgeborn.name', str, None),
            'C': ('cards', dict, 'keys'),
            'A': ('abilities', dict, 'keys'),
            'K': ('composition', dict, None),
        }
        return Filter(query, attribute_map)

# def evaluate_fusions(args, DeckCollection):
#     eval_filename = None
#     if args.eval:
#         eval_filename = args.eval if args.eval is not True else None
#         egraphs = {}
#         fusions_without_graphs = {}

#         local_graphs = cache_manager.load_or_create('GraphLib', lambda: dict())
#         lib_fusions = DeckCollection.library['Fusion']

#         pbar = tqdm(total=len(lib_fusions) * 2, desc="Checking Fusions", mininterval=0.1, colour='GREEN')
#         for fusion in lib_fusions.values():
#             for idx in range(2):
#                 final_fusion = fusion.copyset_forgeborn(idx)
#                 FusionGraph = local_graphs.get(final_fusion.name)

#                 if col_filter and not col_filter.apply([final_fusion]):
#                     continue

#                 if not FusionGraph:
#                     forgeborn_name = final_fusion.get_forgeborn(idx).name
#                     fusions_without_graphs[final_fusion.name] = (final_fusion, forgeborn_name)
#                 else:
#                     egraphs[final_fusion.name] = FusionGraph
#                 pbar.update()
#         pbar.close()

#         if fusions_without_graphs:
#             fusion_results = evaluate_fusions_multiprocess(fusions_without_graphs)
#             for graph_name, FusionGraph in fusion_results.items():
#                 if local_graphs.get(graph_name) is not None:
#                     print(f"{graph_name} already exists locally !")
#                 local_graphs[graph_name] = FusionGraph
#                 egraphs[graph_name] = FusionGraph

#         if len(fusions_without_graphs) > 0 and SelectionType == 'Collection':
#             cache_manager.save_object_to_cache('GraphLib', local_graphs)

#         return eval_filename, egraphs, local_graphs

# def evaluate_fusions_multiprocess(fusions_without_graphs):
#     with Pool(processes=cpu_count()) as pool:
#         terminate_event = Event()
#         fusion_results = {}
#         args_list = [(fb_name, fusion) for name, (fusion, fb_name) in fusions_without_graphs.items()]
#         pbar = tqdm(total=len(args_list), desc="Create Graphs", mininterval=0.1, colour='BLUE')
#         try:
#             for FusionGraph in pool.imap_unordered(process_fusion, args_list, chunksize=1):
#                 if terminate_event.is_set():
#                     print("Parent Process signaled termination. Exiting child processes!")
#                     pool.terminate()
#                     break

#                 if FusionGraph:
#                     fusion_results[FusionGraph.name] = FusionGraph
#                     pbar.update()

#         except KeyboardInterrupt:
#             print("Interrupted! Terminating processes...")
#             terminate_event.set()
#             pool.terminate()
#             pool.join()
#         pbar.close()

#     return fusion_results

# def evaluate_single_decks(DeckCollection, eval_filename, egraphs, local_graphs, args):
#     total_decks = len(DeckCollection.library['Deck'])
#     progress_bar = tqdm(total=total_decks, desc="Creating Deck Graphs", mininterval=0.1, colour='CYAN')
#     dgraphs = {}
#     for name, deck in DeckCollection.library['Deck'].items():
#         if name not in dgraphs:
#             DeckGraph = MyGraph(deck)
#             ev.evaluate_graph(DeckGraph)
#             dgraphs[name] = DeckGraph
#         time.sleep(0.001)
#         progress_bar.update(1)
#     progress_bar.close()

#     total_graphs = len(egraphs)
#     progress_bar = tqdm(total=total_graphs, desc="Printing Fusion Graphs", mininterval=0.1, colour='YELLOW')
#     for name, myGraph in egraphs.items():
#         myGraph.print_graph(eval_filename)

#         if args.graph:
#             eval_path = Path(eval_filename)
#             gefxFolder = os.path.join(eval_path.parent.absolute(), "gefx")
#             Path(gefxFolder).mkdir(parents=True, exist_ok=True)

#             myGraph.write_gexf_file(gefxFolder, name.replace('|', '_'))
#         progress_bar.update(1)
#     progress_bar.close()

#     if eval_filename:
#         ev.export_csv(eval_filename + '_interfaction_only', egraphs, True)
#         ev.export_csv(eval_filename, egraphs, False)
#         ev.export_csv(eval_filename + '.halfdecks_only', dgraphs, False)

#     if args.select_pairs:
#         if not eval_filename:
#             eval_filename = 'evaluation'
#         print("Selecting top unique pairs\n")
#         ev.find_best_pairs(egraphs, eval_filename + '_top_pairs.txt')


def parse_arguments(arguments = None):
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
    parser.add_argument("--mode", default='insert', help="Mode: insert, update, refresh")    

    # Arguments for Evaluation
    
    parser.add_argument("--eval", nargs='?', const=True, action="store",  help="Evaluate possible fusions. Optional filename for .csv export")    
    parser.add_argument("--graph", action="store_true",  help="Create Graph '.gefx'")
    parser.add_argument("--filter", default=None, help="Filter by card names. Syntax: \"<cardname>+'<card name>'-<cardname>\" + = AND, - = OR ")
    parser.add_argument("--select_pairs", action="store_true", help="Select top pairs")
    
    # Parse the command-line arguments
    args = parser.parse_args(arguments)

    return args

if __name__ == "__main__":

    args = parse_arguments()
    main(args)



