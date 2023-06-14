from DeckLibrary import DeckLibrary
from Card_Library import UniversalCardLibrary
from NetApi import NetApi
import Evaluation as ev
import Graph
import argparse
import json
import os
import pickle

def load_object_from_pickle(pickle_file):
    obj = None
    if os.path.exists(pickle_file):
        # Load the object from the pickle file
        with open(pickle_file, "rb") as file:
            obj = pickle.load(file)
        print(f"Object loaded from pickle file: {pickle_file}")
    return obj

def save_object_to_pickle(pickle_file, obj):
    # Save the object to the pickle file
    with open(pickle_file, "wb") as file:
        pickle.dump(obj, file)
    print(f"Object saved to pickle file: {pickle_file}")


def main(args):

    deck_library_name = "deck_library"
    eval_graphs_name  = "eval_graphs"

    if args.filename:
        deck_library_name = f"{args.filename}_library"
        eval_graphs_name  = f"{args.filename}_graphs"

    if args.username:
        deck_library_name += f"_{args.username}"
        eval_graphs_name  += f"_{args.username}"

    myUCL = UniversalCardLibrary('csv/sff.csv')

    # Load DeckCollection from JSON file
    print(f"Loading DeckCollection from pickle: data/{deck_library_name}.pkl")
    DeckCollection = load_object_from_pickle(f"data/{deck_library_name}.pkl")
    
    if DeckCollection == None:    

        decks = []
        if not args.username:
            # Rad entities from CSV and create universal card library        
            decks, incompletes = myUCL.load_decks_from_file(f"data/{args.filename}.json")

        else:
            myApi = NetApi()
            decks = myApi.request_decks(
                id=args.id,
                type=args.type,
                username=args.username,
                filename=args.filename
            )  

        DeckCollection = DeckLibrary(decks)
        save_object_to_pickle(f"data/{deck_library_name}.pkl", DeckCollection)
    
    if args.eval:

        eval_filename = None
        if args.eval is not True:
            eval_filename = args.eval

        EvaluatedGraphs = load_object_from_pickle(f"data/{eval_graphs_name}.pkl")

        if EvaluatedGraphs == None:
            EvaluatedGraphs = {}

            for fusion in DeckCollection.fusions:        
                DeckGraph = Graph.create_deck_graph(fusion)
                ev.evaluate_graph(DeckGraph)
                EvaluatedGraphs[DeckGraph.graph['name']] = DeckGraph      

            save_object_to_pickle(f"data/{eval_graphs_name}.pkl", EvaluatedGraphs)  
                                
        for EGraph in EvaluatedGraphs.values():    
            Graph.print_graph(EGraph,eval_filename)
                
            if args.graph:
                Graph.write_gexf_file(EGraph, EGraph.graph['name'].replace('|', '_'))

        
        if eval_filename: 
            print(f"Exporting evaluated fusions to csv: {eval_filename}.csv")
            ev.export_csv(eval_filename + '_excl', EvaluatedGraphs, True)
            ev.export_csv(eval_filename, EvaluatedGraphs, False)

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

    main(args)



