# your_module.py
from stat import FILE_ATTRIBUTE_REPARSE_POINT
import csv
import Evaluation as ev
import Graph
from collections import defaultdict
from DeckLibrary import DeckLibrary
from Card_Library import UniversalCardLibrary
from Synergy import SynergyTemplate
from NetApi import NetApi

def get_decks(username):
    decks = []
    myApi = NetApi()
    decks = myApi.request_decks(type='fuseddeck', username=username, filename='fusions')
    return decks

def process_decks(decks):
    EvaluatedGraphs = {}
    DeckCollection = DeckLibrary(decks)    
    half_deck = 'The Fire Breathers of the Heartseeker'
    for fusion in DeckCollection.fusions:
        deck_name = fusion.name        
        if deck_name == fusion.name :
            mode = None 
            DeckGraph = Graph.create_deck_graph(fusion, ev.calculate_weight,mode=mode)        
            ev.evaluate_graph(DeckGraph)
            EvaluatedGraphs[DeckGraph.graph['name']] = DeckGraph              
    ev.find_best_pairs(EvaluatedGraphs)
    return EvaluatedGraphs
