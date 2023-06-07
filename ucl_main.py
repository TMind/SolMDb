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
        Graph.print_graph(DeckGraph)
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
    parser.add_argument("--id", default="", help="Specific Deck ID from solforgefusion website")
    parser.add_argument("--type", default="deck", choices=["deck", "fuseddeck"], help="Decktype for user collection")
    parser.add_argument("--username", required=True, help="Account name")
    parser.add_argument("--filename", help="Filename for deck data for offline use")    
    parser.add_argument("--select_pairs", action="store_true", help="Select best pairs")
    parser.add_argument("--export_csv", default="",  help="Export CSV filename")
    
    # Parse the command-line arguments
    args = parser.parse_args()

    # Use the command-line arguments in the function
    myApi = NetApi()
    decks = myApi.request_decks(
        id=args.id,
        type=args.type,
        username=args.username,
        filename=args.filename
    )

    main(args, decks)
