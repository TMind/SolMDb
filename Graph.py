from Interface import InterfaceCollection
import networkx as nx
from collections import defaultdict
import os, re

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

@staticmethod
def handle_synergy_and_edges(G, source_entity, target_entity):
    syn_matches = InterfaceCollection.match_synergies(source_entity.ICollection, target_entity.ICollection)
    if syn_matches:
        label = ",".join(synergy for synergy, count in syn_matches.items() if count > 0)
        weight = sum(syn_matches.values())
        type = source_entity.faction == target_entity.faction
        G.add_edge(source_entity.name, target_entity.name, label=label, weight=weight, local=type)


def create_deck_graph(fusion):        
    G = nx.DiGraph(name = fusion.name, fusion=fusion , mod = 0, between = 0, avglbl = 0, community_labels = {})
        
    G.add_nodes_from(fusion.fused.cards)

    # Create a dictionary of whether any interface in the card has '*' or '+' in its range
    card_ranges = {}
    for card_name, card in fusion.fused.cards.items():
        max_ranges = card.ICollection.get_max_ranges()
        card_ranges[card_name] = ','.join(max_ranges)  # Convert list to a string

    # Add the card range flags as node attributes
    nx.set_node_attributes(G, card_ranges, "max_ranges")

    
    for i, (card_name_1, card_1) in enumerate(fusion.fused.cards.items()):
        for j, (card_name_2, card_2) in enumerate(fusion.fused.cards.items()):                
            if card_name_1 == card_name_2:

                for ability_name, ability in fusion.fused.forgeborn.abilities.items():
                    handle_synergy_and_edges(G, card_1, ability)
                    handle_synergy_and_edges(G, ability, card_2)
                        
                handle_synergy_and_edges(G, card_1, card_1)
                                                                                                                                                  
            if i < j:
                # compare only cards whose indices are greater        
                # Check if the cards have any synergies                
                handle_synergy_and_edges(G, card_1, card_2)
                handle_synergy_and_edges(G, card_2, card_1)
            
    return G


def print_graph(G, output_filename=None):
    """
    Print or write the graph information in a tabular format.

    Args:
        G (networkx.Graph): The graph object to print or write.
        output_file (str, optional): The file path to write the output. If not provided, the output is printed to stdout.

    Returns:
        None
    """    
    output_file = None if output_filename is None else "txt/{output_filename}" 
    
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

 
def load_gexf_file(filename):
    pathname = './gephi/' + filename + '.gexf'
    if not os.path.isfile(pathname):
        raise FileNotFoundError(f"File '{pathname}' not found.")
    
    # Load the graph from the GEXF file
    G = nx.read_gexf(pathname)
    
    return G


def write_gexf_file(graph, filename):
    nx.write_gexf(graph, './gephi/' + filename + '.gexf')


def is_eligible(graph, logical_expression):        
    translated_expression = translate_expression(graph, logical_expression)
    evaluated_expression = eval(translated_expression)    
    return evaluated_expression

def translate_expression(graph, logical_expression):
    translated_expression = logical_expression.replace('-', ' or ')
    translated_expression = translated_expression.replace('+', ' and ')

    # Replace variable names with their graph presence checks
    for variable_name in get_variable_names(logical_expression):
        # Remove single quotes around the variable name if they exist
        stripped_variable_name = variable_name.replace("'","") #strip("'")
        presence_check = str(any(stripped_variable_name in node for node in graph.nodes))
        # Replace the quoted or unquoted variable name with its presence check
        translated_expression = translated_expression.replace(f"'{variable_name}'", presence_check)
        translated_expression = translated_expression.replace(variable_name, presence_check)

    # Return the translated expression
    return translated_expression


def get_variable_names(logical_expression):
    variable_pattern = r"\b\w+\b"  # Regular expression pattern to match variable names
    variable_names = re.findall(variable_pattern, logical_expression)
    return variable_names

