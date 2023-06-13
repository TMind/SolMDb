from DeckLibrary import DeckLibrary
from Card_Library import UniversalCardLibrary
from NetApi import NetApi
import Evaluation as ev
import Graph
import argparse
import json
import os
import pickle

def load_deck_library(deck_library_pickle_file):

    deck_library = None 
    if os.path.exists(deck_library_pickle_file):
        # Load the DeckLibrary from the pickle file
        with open(deck_library_pickle_file, "rb") as file:
            deck_library = pickle.load(file)
        print("DeckLibrary loaded from pickle file.")
    
    return deck_library


def save_deck_library(deck_library_pickle_file, deck_library):

    # Save the DeckLibrary to the pickle file
    with open(deck_library_pickle_file, "wb") as file:
        pickle.dump(deck_library, file)
    print("DeckLibrary saved to pickle file.")


def main(args):

    myUCL = UniversalCardLibrary('csv/sff.csv')

    # Load DeckCollection from JSON file
    print(f"Loading DeckCollection from pickle: data/deck_library.pkl")
    DeckCollection = load_deck_library("data/deck_library.pkl")
    
    if DeckCollection == None:    

        decks = []
        if not args.username:
            # Read entities from CSV and create universal card library        
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
        save_deck_library("data/deck_library.pkl", DeckCollection)

    EvaluatedGraphs = {}    
    
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
                Graph.write_gexf_file(DeckGraph, fusion.name.replace('|', '_'))

        # Export DeckCollection to JSON
        print(f"Exporting DeckCollection to JSON file: deck_collection.json")
        with open("data/deck_collection.json", "w") as file:
            json.dump(DeckCollection.to_json(), file)

        
        if filename: 
            print(f"Exporting evaluated fusions to csv: {filename}.csv")
            ev.export_csv(filename + '_excl', EvaluatedGraphs, True)
            ev.export_csv(filename, EvaluatedGraphs, False)

        if args.select_pairs:
            ev.find_best_pairs(EvaluatedGraphs)

    #TODO: EvaluatedGraphs 


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



