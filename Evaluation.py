from collections import defaultdict
from Interface import InterfaceCollection
from Synergy import SynergyTemplate
from itertools import chain
import networkx as nx
import infomap
import csv


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
    infomap_wrapper = infomap.Infomap("--two-level --silent")

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
        # Get the label(s) of the edge
        labels = edge[2]['label'].split(',')
        # Get the weight of the edge
        total_weight = edge[2]['weight']
         # Calculate weight for each label
        weight_per_label = total_weight / len(labels)
        # Get the nodes of the edge
        nodeA, nodeB = edge[0], edge[1]
        # Get the community of the nodes
        communityA = infomap_wrapper.get_modules()[node_to_int[nodeA]]
        communityB = infomap_wrapper.get_modules()[node_to_int[nodeB]]
        # If the nodes belong to the same community, add the label(s) and the weight to the corresponding community
        if communityA == communityB:
            for label in labels:
                community_labels[communityA].append((label.strip(), weight_per_label))


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

    avg_lbl_com = total_community_labels / len(community_labels) if community_labels else 0
    print(f"Avg Labels: {total_community_labels} / {len(community_labels)} = {avg_lbl_com}")


    # G.graph('community_labels') = community_labels
    #partition = nx.community.greedy_modularity_communities(G)
    #mod = nx.community.modularity(G, partition)
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
    fieldnames = ["deckname", "value", "avglbl", "range1", "range2", "range3"] + all_labels

    with open(f"csv/{csvname}.csv", "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        for i, (key, EGraph) in enumerate(graphs.items()):         

            # Create a dictionary mapping labels to weights
            community_labels = EGraph.graph['community_labels']
            label_weights = defaultdict(float)
            for labels_and_weights in community_labels.values():
                for label, weight in labels_and_weights:
                    label_weights[label] += weight
            
         
           # Gather max_ranges data
            max_node_ranges = {}
            for node, node_data in EGraph.nodes(data=True):
                if "max_ranges" in node_data:
                    max_node_ranges[node] = node_data["max_ranges"].split(',')
            # Flatten the lists and exclude empty strings
            max_graph_ranges = [syn for syn_list in max_node_ranges.values() for syn in syn_list if syn]

            # Ensure the list has at least 3 elements
            #max_graph_ranges += [''] * (3 - len(max_graph_ranges))

            range1 = max_graph_ranges[0] if len(max_graph_ranges) > 0 else ''
            range2 = max_graph_ranges[1] if len(max_graph_ranges) > 1 else ''
            range3 = ', '.join(max_graph_ranges[2:]) if len(max_graph_ranges) > 2 else ''



            # Assign values to range1, range2, and range3
#            range1, range2, range3 = max_graph_ranges[:3]
            # Now you can add these to your dictionary:

            row = {
                "deckname": EGraph.graph['name'],
                "value": f"{EGraph.graph['value']:.4f}",            
                "avglbl": f"{EGraph.graph['avglbl']:.4f}",
                "range1": range1,
                "range2": range2,
                "range3": range3,
            }

            # Add label weights to the row
            for label in all_labels:
                row[label] = label_weights.get(label, 0)  # use 0 if the label does not exist in this graph

            writer.writerow(row)