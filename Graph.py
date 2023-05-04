from DeckLibrary import DeckEvaluator, DeckLibrary
from Synergy import SynergyCollection
import networkx as nx
import matplotlib.pyplot as plt

def create_synergy_graph(decks, min_level=1):
    G = nx.Graph()
    decks = list(decks.values())

    LibDeck = DeckLibrary(decks)
    eval_decks = LibDeck.evaluate_decks()

    for fusion in LibDeck.fusions:
        create_deck_graph(fusion)

    for deck_name, score in eval_decks.items():
        deck_name2 = deck_name.split('|')[1] + '|' + deck_name.split('|')[0] 
        if eval_decks[deck_name2] < score :
            #print(f"Score {deck_name2} :  {eval_decks[deck_name2]} < {score} ")
            G.add_edge(deck_name.split('|')[0], deck_name.split('|')[1], weight=score, label=deck_name.split('|')[0])

    # Remove nodes with no edges
    nodes_to_remove = [node for node, degree in dict(G.degree()).items() if degree == 0]
    G.remove_nodes_from(nodes_to_remove)

    return G

def create_deck_graph(deck):
    G = nx.Graph()
    
    card_traits = {}


    for card_name, card in deck.cards.items():
        G.add_node(card_name)
        
        synergy_collection = SynergyCollection.from_card(card)
        card_sources = synergy_collection.sources
        card_targets = synergy_collection.targets        

        card_traits[card_name] = synergy_collection
        print(f"Deck {deck.name} :: {card_name} = {card_sources} | {card_targets}")


    for card_name in card_traits:         
        card_targets = card_traits[card_name].synergy_collection.targets

        for card_name in card_traits:
            card_sources = card_traits[card_name].synergy_collection.Sources

            for target in card_targets:
                synergies = SynergyTemplate().get_synergies_by_target_tag(target)
                

    #    G.add_edge(deck_name.split('|')[0], deck_name.split('|')[1], weight=score, label=deck_name.split('|')[0])

    return G

def plot_synergy_graph(G):
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, font_weight="bold")
    labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
    #nx.draw_networkx_labels(G, pos, labels={node: node for node in G.nodes()}, font_size=10)
    plt.show()

def write_gephi_file(graph, filename):
    nx.write_gexf(graph, filename + '.gexf')