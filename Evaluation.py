from collections import defaultdict
from Interface import InterfaceCollection
from Synergy import SynergyTemplate
import networkx as nx
import infomap
import csv


# def evaluate_deck(deck):
#     # loop through each synergy in the deck
#     print(f"=====================================")
#     print(f"Evaluating Deck: {deck.name}")
#     evaluation = defaultdict(lambda: defaultdict(
#         lambda: {'IN': set(), 'OUT': set(), 'SELF': set()}))

#     for i, (card_name_1, card_1) in enumerate(deck.cards.items()):
#         for j, (card_name_2, card_2) in enumerate(deck.cards.items()):

#             if card_name_1 == card_name_2:

#                 synCC_matches = InterfaceCollection.match_synergies(card_1.ICollection, card_2.ICollection)
#                 synCF_matches = InterfaceCollection.match_synergies(card_1.ICollection, deck.forgeborn.ICollection)
#                 synFC_matches = InterfaceCollection.match_synergies(deck.forgeborn.ICollection, card_1.ICollection)

#                 if len(synCC_matches) > 0:
#                     for synergy, count in synCC_matches.items():
#                         if count > 0:
#                             ranges = []
#                             for cardname, interface in card_1.ICollection.interfaces[synergy].items():
#                                 # print(f"Adding Range for {synergy} :: {cardname} :: {interface.name} -> {interface.range}")
#                                 ranges.append(interface.range)
#                             for range in ranges:
#                                 if range == '+':
#                                     print(
#                                         f"Range not selfreferential! Omit synergy")
#                                     break
#                             # print(f"Synergy Match Dict:")
#                             # print(str(synCC_matches))
#                             evaluation[card_name_1][synergy]['SELF'].add(
#                                 card_name_2)

#                 if len(synCF_matches) > 0:
#                     for synergy, count in synCF_matches.items():
#                         if count > 0:
#                             evaluation[card_name_1][synergy]['OUT'].add(
#                                 deck.forgeborn.name)
#                             evaluation[deck.forgeborn.name][synergy]['IN'].add(
#                                 card_name_1)

#                 if len(synFC_matches) > 0:
#                     for synergy, count in synFC_matches.items():
#                         if count > 0:
#                             evaluation[deck.forgeborn.name][synergy]['OUT'].add(
#                                 card_name_1)
#                             evaluation[card_name_1][synergy]['IN'].add(
#                                 deck.forgeborn.name)

#             if i < j:
#                 # compare only cards whose indices are greater
#                 # Check if the cards have any synergies
#                 # print(f"Matching Cards: {card_1.title} ~ {card_2.title}")
#                 c12_matches = InterfaceCollection.match_synergies(
#                     card_1.ICollection, card_2.ICollection)
#                 # print(f"Matching Cards: {card_2.title} ~ {card_1.title}")
#                 c21_matches = InterfaceCollection.match_synergies(
#                     card_2.ICollection, card_1.ICollection)

#                 if len(c12_matches) > 0:
#                     for synergy, count in c12_matches.items():
#                         if count > 0:
#                             evaluation[card_name_1][synergy]['OUT'].add(
#                                 card_name_2)
#                             evaluation[card_name_2][synergy]['IN'].add(
#                                 card_name_1)

#                 if len(c21_matches) > 0:
#                     for synergy, count in c21_matches.items():
#                         if count > 0:
#                             evaluation[card_name_2][synergy]['OUT'].add(
#                                 card_name_1)
#                             evaluation[card_name_1][synergy]['IN'].add(
#                                 card_name_2)

#     arrows = {'IN': '->', 'OUT': '<-', 'SELF': '<=>'}

#     for card_name, card_eval in evaluation.items():
#         print(f"Card: {card_name}")
#         for direction in ['IN', 'OUT', 'SELF']:
#             card_sets_by_synergy = defaultdict(list)
#             for synergy_name, synergy_eval in card_eval.items():
#                 card_set = synergy_eval[direction]
#                 if len(card_set) > 0:
#                     for card in card_set:
#                         card_sets_by_synergy[synergy_name].append(card)
#             for synergy_name, card_list in card_sets_by_synergy.items():
#                 card_names = ", ".join(card for card in card_list)
#                 print(
#                     f"\t{arrows[direction]} [{synergy_name}] : {card_names}")

#     return

def find_best_pairs(graphs):

    deck_combinations = []
    for name, graph in graphs.items():
        deck1, deck2 = name.split('|')
        score = graph.graph['avglbl']
        deck_combinations.append((deck1, deck2, score))

    # sort deck combinations by score in decreasing order
    deck_combinations.sort(key=lambda x: x[2], reverse=True)

    chosen_combinations = []
    chosen_decks = set()
    total_score = 0

    for deck1, deck2, score in deck_combinations:
        if deck1 not in chosen_decks and deck2 not in chosen_decks:
            # neither deck has been chosen before, so choose this combination
            chosen_combinations.append((deck1, deck2, score))
            total_score += score
            chosen_decks.add(deck1)
            chosen_decks.add(deck2)

    print(f"Total score: {total_score}")
    for combo in chosen_combinations:
        print(
            f"Chosen combination: {combo[0]}, {combo[1]}, Score: {combo[2]}")

def evaluate_graph(G):
    Metric = {}

    Metric['PageRank'] = nx.pagerank(G, alpha=0.85, personalization=None, max_iter=1000, tol=1e-06, nstart=None, dangling=None)
    Metric['degree'] = nx.degree_centrality(G)
    Metric['cluster_coeff'] = nx.clustering(G)
    Metric['between'] = nx.betweenness_centrality(G)
    Metric['katz'] = nx.katz_centrality(G, alpha=0.1, beta=1.0)

    # Create a mapping of nodes to integers
    node_to_int = {node: i for i, node in enumerate(G.nodes)}

    # Initialize Infomap
    infomap_wrapper = infomap.Infomap("--two-level")

    # Add nodes and edges to Infomap
    for node in node_to_int.values():
        infomap_wrapper.add_node(node)

    for edge in G.edges:
        infomap_wrapper.add_link(
            node_to_int[edge[0]], node_to_int[edge[1]])

    # Run Infomap
    infomap_wrapper.run()
        # create a dictionary to store labels in each community
    community_labels = defaultdict(list)

    # Iterate over the edges in the graph
    for edge in G.edges(data=True):
        # Get the label of the edge
        label = edge[2]['label']
        # Get the weight of the edge
        weight = edge[2]['weight']
        # Get the nodes of the edge
        nodeA, nodeB = edge[0], edge[1]
        # Get the community of the nodes
        communityA = infomap_wrapper.get_modules()[node_to_int[nodeA]]
        communityB = infomap_wrapper.get_modules()[node_to_int[nodeB]]
        # If the nodes belong to the same community, add the label and the weight to the corresponding community
        if communityA == communityB:
            community_labels[communityA].append((label, weight))

    # Calculate the total number of community labels and the average number of labels per community
    total_community_labels = sum(len(labels) for labels in community_labels.values())

    for community, labels in community_labels.items():
        print("Community: ", community)
        # Create a dictionary to accumulate the weights for each label
        label_weights = defaultdict(float)

        # Sum up the weights for each label
        for label, weight in labels:
            label_weights[label] += weight

        # Print the weights for each label
        for label, weight in label_weights.items():
            print(f"Label: {label}, Weight: {weight}")

    avg_lbl_com = total_community_labels / len(community_labels)
    print(f"Avg Labels: {total_community_labels} / {len(community_labels)} = {avg_lbl_com}")


    # G.graph('community_labels') = community_labels
    partition = nx.community.greedy_modularity_communities(G)
    mod = nx.community.modularity(G, partition)
    clustering_coefficients = nx.average_clustering(G)
    density = nx.density(G)

    G.graph['cluster_coeff'] = clustering_coefficients
    G.graph['density'] = density
    G.graph['avglbl'] = total_community_labels
    G.graph['community_labels'] = community_labels

    for name, metric in Metric.items():
        nx.set_node_attributes(G, metric, name)

    for node_name in G.nodes:
        combined_metric = Metric['between'][node_name] * Metric['cluster_coeff'][node_name]
        G.nodes[node_name]['total'] = combined_metric
        G.graph['value'] += combined_metric

def calculate_weight(synergy, count):

    syn = SynergyTemplate().get_synergy_by_name(synergy)
    return count * syn.weight


def export_csv(csvname, graphs):
    # Get all labels from the SynergyTemplate
    all_labels = list(SynergyTemplate().synergies.keys())

    # Define the fieldnames for the CSV
    fieldnames = ["deckname", "value", "avglbl"] + all_labels

    with open(f"{csvname}.csv", "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        for i, (key, EGraph) in enumerate(graphs.items()):         

            # Create a dictionary mapping labels to weights
            community_labels = EGraph.graph['community_labels']
            label_weights = defaultdict(float)
            for labels_and_weights in community_labels.values():
                for label, weight in labels_and_weights:
                    label_weights[label] += weight
            
            # Create a dictionary to hold the row data
            row = {
                "deckname": EGraph.graph['name'],
                "value": f"{EGraph.graph['value']:.4f}",            
                "avglbl": f"{EGraph.graph['avglbl']:.4f}",
            }

            # Add label weights to the row
            for label in all_labels:
                row[label] = label_weights.get(label, 0)  # use 0 if the label does not exist in this graph

            writer.writerow(row)




# def export_csv(csvname, graphs):

#     # Open the csv file in write mode and write the header row
#     with open(f"{csvname}.csv", "w", newline="") as csvfile:
#         writer = csv.DictWriter(csvfile, fieldnames=[
#                                 "deckname", "value", "katz", "degree", "density", "cluster_coeff", "between", "avglbl"], delimiter=';')
#         writer.writeheader()

#         for i, (key, EGraph) in enumerate(graphs.items()):

#             Metrics = {
#                 "katz": 0 ,
#                 "cluster_coeff": 0 ,
#                 "degree": 0 ,
#                 "between"   : 0
#             }

#             name = EGraph.graph['name']
#             # mod   = EGraph.graph['mod']
#             value = EGraph.graph['value']
#             density = EGraph.graph['density']
#             cluster_coeff = EGraph.graph['cluster_coeff']

#             for metric in Metrics:
#                 Metrics[metric] = sum([EGraph.nodes[node_name][metric] for node_name in EGraph.nodes]) 

#             writer.writerow({
#                 "deckname": name,
#                 #   "modularity": f"{mod:.4f}",
#                 "value": f"{value:.4f}",
#                 "katz": f"{Metrics['katz']:.4f}",
#                 "degree": f"{Metrics['degree']:.4f}",
#                 "density": f"{density:.4f}",
#                 "cluster_coeff": f"{cluster_coeff:.4f}",
#                 "between": f"{Metrics['between']:.4f}",
#                 "avglbl": f"{EGraph.graph['avglbl']:.4f}"
#             })
