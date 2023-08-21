from collections import defaultdict
from Synergy import SynergyTemplate
import networkx as nx
import infomap
import csv
import time
import os
from tqdm import tqdm

def find_best_pairs(graphs,outpath):

    deck_combinations = []
    for name, graph in graphs.items():
        fusion = graph.graph['fusion']
        decknames = [ deck.name for deck in fusion.decks]
        deck1, deck2 = decknames[0], decknames[1]
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

    with open(outpath, "w") as select_pair_file:
        select_pair_file.write(f"Total score: {total_score}\n")
        for combo in chosen_combinations:
             select_pair_file.write( f"Chosen combination: {combo[0]}, {combo[1]}, Score: {combo[2]} \n")

def evaluate_graph(G):
    Metric = {}

    #Metric['PageRank'] = nx.pagerank(G, alpha=0.85, personalization=None, max_iter=1000, tol=1e-06, nstart=None, dangling=None)
    #Metric['degree'] = nx.degree_centrality(G)
    #Metric['cluster_coeff'] = nx.clustering(G)
    Metric['between'] = nx.betweenness_centrality(G)
    #Metric['katz'] = nx.katz_centrality(G, alpha=0.1, beta=1.0)

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
    community_labelinfos = defaultdict(list)

   # Iterate over the edges in the graph
    for edge in G.edges(data=True):
        # Get locality of edge
        local_faction = edge[2]['local']
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
        local_comm = False
        if communityA == communityB: local_comm = True 
        
        for label in labels:
            community_labelinfos[communityA].append((label.strip(), weight_per_label, local_faction, local_comm))


    # Calculate the total number of community labels and the average number of labels per community
    total_nr_community_labels = sum(len(labelinfos) for labelinfos in community_labelinfos.values())

    #partition = nx.community.greedy_modularity_communities(G)
    #mod = nx.community.modularity(G, partition)
    clustering_coefficients = nx.average_clustering(G)
    density = nx.density(G)

    G.graph['cluster_coeff'] = clustering_coefficients
    G.graph['density'] = density
    G.graph['avglbl'] = total_nr_community_labels
    G.graph['community_labels'] = community_labelinfos

    for name, metric in Metric.items():
        nx.set_node_attributes(G, metric, name)

    #for node_name in G.nodes:
    #    combined_metric = Metric['between'][node_name] * Metric['cluster_coeff'][node_name]
    #    G.nodes[node_name]['total'] = combined_metric
        #G.graph['value'] += combined_metric

def calculate_weight(synergy, count):

    syn = SynergyTemplate().get_synergy_by_name(synergy)
    return count * syn.weight


def export_csv(csvname, graphs, local_mode=False):
    # Get all labels from the SynergyTemplate
    synergy_template = SynergyTemplate()
    all_labels = list(synergy_template.synergies.keys())

    
    # Define the fieldnames for the CSV
    fieldnames = ["deckname1", "deckname2","forgeborn", "factions", "numlbl", "seeks1", "seeks2", "seeks3", "seeks4", "Creatures", "Spells"]
    # Add columns for each label before and after
    for label in all_labels:
        #fieldnames.append(f"{label}_1")
        fieldnames.append(f"{label}")
        #fieldnames.append(f"{label}_2")


    with open(f"{csvname}.csv", "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

         # Create a tqdm instance for the loop
        progress_bar = tqdm(graphs.items(), total=len(graphs), desc=f"Exporting CSV {os.path.basename(csvname)}", mininterval=0.1, colour='RED')


        for i, (key, EGraph) in enumerate(progress_bar):         

            #Fusion
            deck = EGraph.graph['fusion']
    
            #Composition of Fusion 
            composition = deck.composition
            #Determine decknames
            forgeborn_name = EGraph.graph['forgeborn']
            deck_names    = EGraph.graph['name'].split('_')
            deck_factions = EGraph.graph['faction']
            deckname1, *rest = deck_names
            deckname2 = rest[0] if rest else None

            num_creatures = composition['Creature']
            num_spells    = composition['Spell']

            # Create a dictionary mapping labels to weights
            community_labels = EGraph.graph['community_labels']
            label_weights = defaultdict(float)
            for label_info in community_labels.values():
                for label, weight, loc_comm, loc_faction in label_info:
                    if loc_comm and local_mode: continue
                    label_weights[label] += weight
            
         
           # Gather max_ranges data            
            max_ranges = EGraph.graph['max_ranges']
            max_graph_ranges = [syn for syn_list in max_ranges.values() for syn in syn_list.split(',') if syn]

            # Ensure the list has at least 3 elements
            #max_graph_ranges += [''] * (3 - len(max_graph_ranges))

            range1 = max_graph_ranges[0] if len(max_graph_ranges) > 0 else ''
            range2 = max_graph_ranges[1] if len(max_graph_ranges) > 1 else ''
            range3 = max_graph_ranges[2] if len(max_graph_ranges) > 2 else ''
            range4 = ', '.join(max_graph_ranges[3:]) if len(max_graph_ranges) > 3 else ''

            # Assign values to range1, range2, and range3
#            range1, range2, range3 = max_graph_ranges[:3]
            # Now you can add these to your dictionary:

            row = {
                "deckname1": deckname1,
                "deckname2": deckname2,
                "forgeborn": forgeborn_name,
                "factions":  deck_factions,
                "numlbl": f"{EGraph.graph['avglbl']:.4f}",
                "seeks1": range1,
                "seeks2": range2,
                "seeks3": range3,
                "seeks4": range4,
                "Creatures": num_creatures,
                "Spells": num_spells
            }

            # Add label weights to the row
            for label in all_labels:

                #output_tags = synergy_template.get_output_tags_by_synergy(label)
                #deck1_count = 0
                #deck2_count = 0

                #for tag in output_tags:
                #    deck1_count += compositions[deckname1].setdefault(tag,0) 
                #    deck2_count += compositions[deckname2].setdefault(tag,0)
                
                #row[f"{label}_1"] = deck1_count
                #row[f"{label}_2"] = deck2_count
                row[label] = label_weights.get(label, 0)  # use 0 if the label does not exist in this graph

            writer.writerow(row)
            time.sleep(0.001)

        progress_bar.close()