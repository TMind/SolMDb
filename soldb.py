import argparse
from collections import defaultdict
from DeckLibrary import DeckLibrary
from Card_Library import UniversalCardLibrary
from NetApi import NetApi
import Evaluation as ev
import Graph

class EmptyStringDefault(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not values:
            values = 'fusions'  # define your default_value here
        setattr(namespace, self.dest, values)



def main(args, decks):
    EvaluatedGraphs = {}    
    DeckCollection = DeckLibrary(decks)

    if args.eval:

        filename = None
        if args.eval is not True:
            filename = args.eval

        for fusion in DeckCollection.fusions:        
            DeckGraph = Graph.create_deck_graph(fusion)
            ev.evaluate_graph(DeckGraph)
            EvaluatedGraphs[DeckGraph.graph['name']] = DeckGraph        
            Graph.print_graph(DeckGraph,filename)
            
            if args.graph:
                Graph.write_gephi_file(DeckGraph, fusion.name.replace('|', '_'))

        if filename: 
            print(f"Exporting evaluated fusions to csv: {filename}.csv")
            ev.export_csv(filename + '_excl', EvaluatedGraphs, True)
            ev.export_csv(filename, EvaluatedGraphs, False)

        if args.select_pairs:
            ev.find_best_pairs(EvaluatedGraphs)


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
    parser.add_argument("--filename",  default="deck_base",  help="Offline Deck Database Name, defaut=data/deck_base.json")
    
    #parser.add_argument("--filename", help="Filename for deck data for offline use")    

    # Arguments for Evaluation
    
    parser.add_argument("--eval", nargs='?', const=True, action="store",  help="Evaluate possible fusions. Optional filename for .csv export")    
    parser.add_argument("--graph", action="store_true",  help="Create Graph '.gefx'")
    parser.add_argument("--select_pairs", action="store_true", help="Select top pairs")
    
    # Parse the command-line arguments
    args = parser.parse_args()

    # Use the command-line arguments in the function
    decks = []
    if not args.username:
        # Read entities from CSV and create universal card library
        myUCL = UniversalCardLibrary('csv/sff.csv')#, synergy_template)
        decks, incompletes = myUCL.load_decks_from_file(f"data/{args.filename}.json")

    else:
        myApi = NetApi()
        decks = myApi.request_decks(
            id=args.id,
            type=args.type,
            username=args.username,
            filename=args.filename
        )

    main(args, decks)



