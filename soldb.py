import argparse
from collections import defaultdict
from DeckLibrary import DeckLibrary
from Card_Library import UniversalCardLibrary
from NetApi import NetApi
import Evaluation as ev
import Graph

def main(args, decks):
    EvaluatedGraphs = {}    
    DeckCollection = DeckLibrary(decks)

    for fusion in DeckCollection.fusions:
        print(f"\nFusion: {fusion.name}\n")
        DeckGraph = Graph.create_deck_graph(fusion)
        ev.evaluate_graph(DeckGraph)
        EvaluatedGraphs[DeckGraph.graph['name']] = DeckGraph
        if args.eval:
            Graph.print_graph(DeckGraph)
        if args.graph :
            Graph.write_gephi_file(DeckGraph, fusion.name.replace('|', '_'))
        print(f"\n========================================================\n")
    if args.select_pairs:
        ev.find_best_pairs(EvaluatedGraphs)

    if args.export_csv:        
        ev.export_csv(args.export_csv + '_excl', EvaluatedGraphs, True)
        ev.export_csv(args.export_csv, EvaluatedGraphs, False)


if __name__ == "__main__":
    # Create an argument parser
    parser = argparse.ArgumentParser(description="Script description")

    # Add command-line arguments
    parser.add_argument("--username", default="", help="Account name or blank for offline use")
    parser.add_argument("--id", default="", help="Specific Deck ID from solforgefusion website")
    parser.add_argument("--type", default="deck", choices=["deck", "fuseddeck"], help="Decktype for user collection , default=deck")
    parser.add_argument("--filename", help="Filename for deck data for offline use")    
    parser.add_argument("--select_pairs", action="store_true", help="Select top pairs")
    parser.add_argument("--export_csv", default="",  help="Export CSV filename")
    parser.add_argument("--base", default="data/deck_base.json",  help="Offline Deck Database, defaut=data/deck_base.json")
    parser.add_argument("--graph", action="store_true",  help="Create Graph '.gefx'")
    parser.add_argument("--eval",  action="store_true",  help="Evaluate possible fusions")

    # Parse the command-line arguments
    args = parser.parse_args()

    # Use the command-line arguments in the function
    decks = []
    if args.base and not args.username:
        # Read entities from CSV and create universal card library
        myUCL = UniversalCardLibrary('csv/sff.csv')#, synergy_template)
        decks, incompletes = myUCL.load_decks_from_file(args.base)

    else:
        myApi = NetApi()
        decks = myApi.request_decks(
            id=args.id,
            type=args.type,
            username=args.username,
            filename=args.filename
        )

    main(args, decks)
