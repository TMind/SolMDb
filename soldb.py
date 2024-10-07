from DeckLibrary    import DeckLibrary
from UniversalLibrary import UniversalLibrary
from Synergy        import SynergyTemplate
from NetApi         import NetApi
import argparse 
import os, re
from MongoDB.DatabaseManager import DatabaseManager
from GlobalVariables import global_vars as gv

def main(args):
    os.environ['SFF_USERNAME'] = args.username    

    #uri = "mongodb+srv://solDB:uHrpfYD1TXVzf3DR@soldb.fkq8rio.mongodb.net/?retryWrites=true&w=majority&appName=SolDB"
    gv.myDB = DatabaseManager(gv.username, uri=gv.uri)
    gv.commonDB = DatabaseManager('common', uri=gv.uri)

    synergy_template = SynergyTemplate()    
    
    ucl_paths = [os.path.join('csv', 'sff.csv'), os.path.join('csv', 'forgeborn.csv'), os.path.join('csv', 'synergies.csv')]

    #Read Entities and Forgeborns from Files into Database
    myUCL = UniversalLibrary(args.username, *ucl_paths)
    
        
    net_decks = []
    net_fusions = []

    if not args.offline:
        myApi = NetApi()
                
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
        #return Filter(query, attribute_map)
        return None

def parse_arguments(arguments = None):
    # Create an argument parser
    parser = argparse.ArgumentParser(description="Script description")

    # Add command-line arguments
    # Arguments for online use 
    parser.add_argument("--username", default="", help="Online account name or omit for offline use")
    parser.add_argument("--type", default="deck", choices=["deck", "fuseddeck", "deck,fuseddeck"], help="Decktype for user collection , default=deck")
    parser.add_argument("--id", default="", help="Specific Deck ID from solforgefusion website")
    
    # Arguments for general use 
    # If both username and file is given, export deckbase to file.json 
    # If only file is given import deckbase from file.json 
    parser.add_argument("--filename",  default=None,  help="Offline Deck Database Name")
    parser.add_argument("--synergies", default=None, help="CSV Filename for synergy lookup")    
    parser.add_argument("--offline", default=None, help="Offline use only")    
    parser.add_argument("--mode", default='insert', help="Mode: insert, update, refresh, create")    

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



