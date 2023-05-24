from Interface import InterfaceCollection
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict

# def create_synergy_graph(decks, min_level=1):
#     G = nx.Graph()
#     decks = list(decks.values())

#     LibDeck = DeckLibrary(decks)
#     eval_decks = LibDeck.evaluate_decks()

#     for fusion in LibDeck.fusions:
#         create_deck_graph(fusion)

#     for deck_name, score in eval_decks.items():
#         deck_name2 = deck_name.split('|')[1] + '|' + deck_name.split('|')[0] 
#         if eval_decks[deck_name2] < score :
#             #print(f"Score {deck_name2} :  {eval_decks[deck_name2]} < {score} ")
#             G.add_edge(deck_name.split('|')[0], deck_name.split('|')[1], weight=score, label=deck_name.split('|')[0])

#     # Remove nodes with no edges
#     nodes_to_remove = [node for node, degree in dict(G.degree()).items() if degree == 0]
#     G.remove_nodes_from(nodes_to_remove)

#     return G

def create_deck_graph(deck, eval_func, mode=None):
    G = nx.DiGraph(name = deck.name, mod = 0, value = 0, cluster_coeff = 0, density = 0, avglbl = 0, community_labels = {})
    #print(f"Card Synergies between decks: {deck.name}")        
    
    G.add_nodes_from(deck.cards)
    
    for i, (card_name_1, card_1) in enumerate(deck.cards.items()):
        for j, (card_name_2, card_2) in enumerate(deck.cards.items()):                

            if mode and card_1.faction == card_2.faction:
                continue

            if card_name_1 == card_name_2:

                synCC_matches = InterfaceCollection.match_synergies(card_1.ICollection, card_2.ICollection)                                       

                for ability_name, ability in deck.forgeborn.abilities.items():
                    synCA_matches = InterfaceCollection.match_synergies(ability.ICollection,  card_1.ICollection)
                    synAC_matches = InterfaceCollection.match_synergies(card_1.ICollection , ability.ICollection)
                    
                    if len(synCA_matches) > 0:                    
                        for synergy, count in synCA_matches.items(): 
                            if count > 0:
                                G.add_edge(card_name_1, ability.name , label=synergy, weight = eval_func(synergy,count))
                    
                    if len(synAC_matches) > 0:                    
                        for synergy, count in synAC_matches.items(): 
                            if count > 0:
                                G.add_edge(ability.name , card_name_1, label=synergy, weight = eval_func(synergy,count))

                if len(synCC_matches) > 0:                    
                    for synergy, count in synCC_matches.items(): 
                        if count > 0:
                            G.add_edge(card_name_1, card_name_1, label=synergy, weight = eval_func(synergy,count))                                                                                               
                
            if i < j:
                # compare only cards whose indices are greater        
                # Check if the cards have any synergies                

                c12_matches = InterfaceCollection.match_synergies(card_1.ICollection, card_2.ICollection)
                c21_matches = InterfaceCollection.match_synergies(card_2.ICollection, card_1.ICollection)

                if len(c12_matches) > 0 :                        
                    for synergy, count in c12_matches.items():
                        if count > 0:
                            G.add_edge(card_name_1, card_name_2, label=synergy, weight = eval_func(synergy,count)) 

                if len(c21_matches) > 0 :                        
                    for synergy, count in c21_matches.items():
                        if count > 0:
                            G.add_edge(card_name_2, card_name_1, label=synergy, weight = eval_func(synergy,count))

    return G



def edge_statistics(G):
    # Edge Statistics
    edge_statistics = defaultdict(lambda: defaultdict(int))
    edge_nodes = defaultdict(set)
    edge_details = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for node in G.nodes:
        # Get incoming edges
        for edge in G.in_edges(node, data=True):
            label = edge[2]['label']
            edge_statistics[label]['incoming'] += 1
            edge_nodes[label].add(edge[1]) # Add the destination node
            edge_details[label][node]['incoming'].append(edge[0]) # Add the source node of the incoming edge

        # Get outgoing edges
        for edge in G.out_edges(node, data=True):
            label = edge[2]['label']
            edge_statistics[label]['outgoing'] += 1
            edge_nodes[label].add(edge[0]) # Add the source node
            edge_details[label][node]['outgoing'].append(edge[1]) # Add the destination node of the outgoing edge

    for label, data in edge_statistics.items():
        average_incoming = data['incoming'] / len(edge_nodes[label]) if edge_nodes[label] else 0
        average_outgoing = data['outgoing'] / len(edge_nodes[label]) if edge_nodes[label] else 0
        print(f"Label: {label}")
        print(f"\tAverage incoming edges per node: {average_incoming}")
        print(f"\tAverage outgoing edges per node: {average_outgoing}")

        for node, edge_info in edge_details[label].items():
            print(f"\tNode: {node}")
            print(f"\t\tIncoming edges from nodes: {edge_info['incoming']}")
            print(f"\t\tOutgoing edges to nodes: {edge_info['outgoing']}")
    return edge_statistics

def normalize_dict_values(d):
    max_value = max(d.values())
    min_value = min(d.values())
    if max_value == min_value:  # if all values are the same
        return {k: 0 for k in d}  # or whatever value you think is appropriate
    else:
        interval = max_value - min_value
        return {k: (v - min_value) / interval for k, v in d.items()}

def print_graph(G):
    # Print header
    print(f"{'Node A':<30} {'Node B':<30} {'Weight':<5} {'Label':<15}")

    # Iterate through edges and print in a tabular format
    for nodeA, nodeB, data in G.edges(data=True):
        weight = data.get('weight', 'N/A')
        label = data.get('label', 'N/A')
        print(f"{nodeA:<30} {nodeB:<30} {str(weight):<5} {str(label):<15}")


def write_gephi_file(graph, filename):
    nx.write_gexf(graph, './gephi/' + filename + '.gexf')