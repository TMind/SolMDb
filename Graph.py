from traitlets import default
from Interface import InterfaceCollection
from collections import defaultdict
from itertools import combinations
import os
import networkx as nx
#from graphspace_python.api.client import GraphSpace
#from graphspace_python.graphs.classes.gsgraph import GSGraph

# Define a nested defaultdict
def default_int():
    return defaultdict(int) 

class MyGraph:

    def __init__(self, deck, forgeborn_name=None): 

        self.G      = nx.DiGraph()
        self.avglbl     = 0
        self.name       = deck.name
        self.faction    = deck.faction
        self.fusion     = deck        
        self.community_labels   =  {}
        self.max_ranges = {}        
        self.forgeborn_name     = forgeborn_name        
        if forgeborn_name: 
            deck.set_forgeborn(forgeborn_name)
        self.forgeborn  = deck.forgeborn        
        
        self.unmatched_synergies = defaultdict(default_int)
        self.matched_synergies   = defaultdict(int)

        self.create_deck_graph()
        self.cancel_non_matching_synergies()        
    

    def handle_synergy_and_edges(self, source_entity, target_entity):
        syn_matches, syn_misses = InterfaceCollection.match_synergies(source_entity.ICollection, target_entity.ICollection)
        if syn_matches:
            label = ",".join(synergy for synergy, count in syn_matches.items() if count > 0)
            weight = sum(syn_matches.values())
            type = source_entity.faction == target_entity.faction
            self.G.add_edge(source_entity.name, target_entity.name, label=label, weight=weight, local=type)

            for synergy, num in syn_matches.items():                
                self.matched_synergies[synergy] += num

        # Handle unmatched synergies and update miss count
        if syn_misses:
            for synergy, input_interfaces in syn_misses.items():                
                for input_interface in input_interfaces:
                    self.unmatched_synergies[synergy][input_interface.name] = input_interface.value
                


    def create_deck_graph(self):
        
        self.G = nx.DiGraph(nmod=0, between=0)
        self.G.add_nodes_from([card.title for card in self.fusion.cards.values()] + [name for name in self.forgeborn.abilities])

        # Create a dictionary of whether any interface in the card has '*' or '+' in its range
        self.card_ranges = {
            card_name: ','.join(card.ICollection.get_max_ranges())
            for (faction, card_name), card in self.fusion.cards.items()
        }

        cards_items = list(self.fusion.cards.items())

        # Handle self synergy and synergy with Forgeborn abilities for each card
        for ((faction, card_name), card) in cards_items:
            self.handle_synergy_and_edges(card, card)

            for ability_name, ability in self.forgeborn.abilities.items():
                self.handle_synergy_and_edges(card, ability)
                self.handle_synergy_and_edges(ability, card)

        # Create pairs of cards to check for synergies between them
        for ((faction1, card_name_1), card_1), ((faction2, card_name_2), card_2) in combinations(cards_items, 2):
            self.handle_synergy_and_edges(card_1, card_2)
            self.handle_synergy_and_edges(card_2, card_1)
        
    def cancel_non_matching_synergies(self):
        for synergy in self.matched_synergies:
            if synergy in self.unmatched_synergies:                
                del self.unmatched_synergies[synergy]



    def print_graph(self, output_file=None):
        """
        Print or write the graph information in a tabular format.

        Args:
            G (graphspace.Graph): The graph object to print or write.
            output_file (str, optional): The file path to write the output. If not provided, the output is printed to stdout.

        Returns:
            None
        """
        first_time = not output_file or not os.path.isfile(output_file)
        text = f"\n===============================================================\n"
        text += f"\nFusion: {self.name}\n"
        text += f"{'Node A':<30} {'Node B':<30} {'Weight':<5} {'Label':<30}\n"
        for nodeA, nodeB, data in self.G.edges(data=True):
            weight = data.get('weight', 'N/A')
            label = data.get('label', 'N/A')
            local = data.get('local', 'N/A')
            text += f"{nodeA:<30} {nodeB:<30} {str(weight):<5} {str(label):<30}\n"
        text += f"\n-------------------------------------------------------------\n"

        # Updated code using enhanced text strings
        #community_labelinfos = self.G.graph['community_labels']
        total_nr_community_labels = 0  # Assuming this variable is defined somewhere in the code

        for community, labels_infos in self.community_labels.items():
            text += f"Community: {community}\n"
            label_infos = {}
            for label, weight, loc_faction  in labels_infos:
                if label not in label_infos:
                    label_infos[label] = {'weight': 0, 'count': 0, 'loc_faction': 0}
                label_infos[label]['count'] += 1
                label_infos[label]['weight'] += weight
                label_infos[label]['loc_faction'] += 1 if loc_faction else 0
                #label_infos[label]['loc_comm'] += 1 if loc_comm else 0

            for label, label_info in label_infos.items():
                text += f"Label: {label:<30}, Weight: {label_info['weight']}\n"
                total_nr_community_labels += label_info['weight']

        avg_lbl_com = total_nr_community_labels / len(self.community_labels) if self.community_labels else 0
        text += f"\nAvg Labels: {total_nr_community_labels} / {len(self.community_labels)} = {avg_lbl_com}\n"

        if output_file:
            mode = 'w' if first_time else 'a'
            with open(output_file, mode) as file:
                file.write(text)
        else:
            print(text)

    def load_gexf_file(self,graphfolder, filename):
        pathname = os.path.join(graphfolder, filename + '.gexf')
        if not os.path.isfile(pathname):
            raise FileNotFoundError(f"File '{pathname}' not found.")

        # Load the graph from the GEXF file
        return nx.read_gexf(pathname)                

    def write_gexf_file(self, graphfolder, filename):
        nx.write_gexf(self.G, os.path.join(graphfolder,filename + '.gexf'))


