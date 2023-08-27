from Interface import InterfaceCollection
from collections import defaultdict
from itertools import combinations
from Card_Library import Fusion
import networkx as nx
import os, re


@staticmethod
def handle_synergy_and_edges(G, source_entity, target_entity):
    syn_matches = InterfaceCollection.match_synergies(source_entity.ICollection, target_entity.ICollection)
    if syn_matches:
        label = ",".join(synergy for synergy, count in syn_matches.items() if count > 0)
        weight = sum(syn_matches.values())
        type = source_entity.faction == target_entity.faction
        G.add_edge(source_entity.name, target_entity.name, label=label, weight=weight, local=type)


def create_deck_graph(deck, forgeborn_name=None):        
    if forgeborn_name:
        deck.set_forgeborn(forgeborn_name)
    name = deck.name 
    faction = deck.faction 
    forgeborn = deck.forgeborn
    
    G = nx.DiGraph(name = name, faction = faction, forgeborn = forgeborn_name, fusion=deck, mod = 0, between = 0, avglbl = 0, community_labels = {}, max_ranges = {})

    G.add_nodes_from([card.title for card in deck.cards.values()] + [name for name in forgeborn.abilities])

    # Create a dictionary of whether any interface in the card has '*' or '+' in its range
    card_ranges = {
        card_name: ','.join(card.ICollection.get_max_ranges())
        for (faction, card_name), card in deck.cards.items()
    }
    
    # Add the card range flags as node attributes
    G.graph['max_ranges'] = card_ranges

    cards_items = list(deck.cards.items())

    # Handle self synergy and synergy with Forgeborn abilities for each card
    for ((faction, card_name), card) in cards_items:
        handle_synergy_and_edges(G, card, card)

        for ability_name, ability in deck.forgeborn.abilities.items():
            handle_synergy_and_edges(G, card, ability)
            handle_synergy_and_edges(G, ability, card)    

    # Create pairs of cards to check for synergies between them
    for ((faction1, card_name_1), card_1), ((faction2, card_name_2), card_2) in combinations(cards_items, 2):
        handle_synergy_and_edges(G, card_1, card_2)
        handle_synergy_and_edges(G, card_2, card_1)
            
    return G


def print_graph(G, output_file=None):
    """
    Print or write the graph information in a tabular format.

    Args:
        G (networkx.Graph): The graph object to print or write.
        output_file (str, optional): The file path to write the output. If not provided, the output is printed to stdout.

    Returns:
        None
    """        
    first_time = not output_file or not os.path.isfile(output_file)
    text = f"\n===============================================================\n"
    text += f"\nFusion: {G.graph['name']}\n"
    text += f"{'Node A':<30} {'Node B':<30} {'Weight':<5} {'Label':<30}\n"
    for nodeA, nodeB, data in G.edges(data=True):
        weight = data.get('weight', 'N/A')
        label = data.get('label', 'N/A')
        local = data.get('local', 'N/A')
        text += f"{nodeA:<30} {nodeB:<30} {str(weight):<5} {str(label):<30}\n"
    text += f"\n-------------------------------------------------------------\n"

    # Updated code using enhanced text strings
    community_labelinfos = G.graph['community_labels']
    total_nr_community_labels = 0  # Assuming this variable is defined somewhere in the code

    for community, labels_infos in community_labelinfos.items():
        text += f"Community: {community}\n"
        label_infos = defaultdict(float)
        for label, weight, loc_faction, loc_comm in labels_infos:
            if label not in label_infos:
                label_infos[label] = {'weight': 0, 'count': 0, 'loc_faction': 0, 'loc_comm': 0}
            label_infos[label]['count'] += 1
            label_infos[label]['weight'] += weight
            label_infos[label]['loc_faction'] += 1 if loc_faction else 0
            label_infos[label]['loc_comm'] += 1 if loc_comm else 0
        
        for label, label_info in label_infos.items():
            text += f"Label: {label:<30}, Weight: {label_info['weight']}\n"
            total_nr_community_labels += label_info['weight']

                  #, LocComm: {label_info['loc_comm']}, LocFact: {label_info['loc_faction']}")

    avg_lbl_com = total_nr_community_labels / len(community_labelinfos) if community_labelinfos else 0
    text += f"\nAvg Labels: {total_nr_community_labels} / {len(community_labelinfos)} = {avg_lbl_com}\n"
    

    if output_file:
        mode = 'w' if first_time else 'a'
        with open(output_file, mode) as file:
            file.write(text)
    else:
        print(text)

 
def load_gexf_file(graphfolder, filename):
    pathname = os.path.join(graphfolder,filename + '.gexf')
    if not os.path.isfile(pathname):
        raise FileNotFoundError(f"File '{pathname}' not found.")
    
    # Load the graph from the GEXF file
    G = nx.read_gexf(pathname)
    
    return G


def write_gexf_file(graph, graphfolder, filename):
    nx.write_gexf(graph, os.path.join(graphfolder,filename + '.gexf'))


