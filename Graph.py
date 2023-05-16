from DeckLibrary import DeckLibrary
from Synergy import SynergyTemplate
from Interface import InterfaceCollection
from networkx.algorithms import community
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
    G = nx.DiGraph(name = deck.name, mod = 0, value = 0, cluster_coeff = 0, density = 0)
    #print(f"Card Synergies between decks: {deck.name}")    
    synergy_template = SynergyTemplate()
    
    G.add_nodes_from(deck.cards)

    for i, (card_name_1, card_1) in enumerate(deck.cards.items()):
        for j, (card_name_2, card_2) in enumerate(deck.cards.items()):                

            if card_name_1 == card_name_2:

                synCC_matches = InterfaceCollection.match_synergies(card_1.ICollection, card_2.ICollection)                                        
                synCF_matches = InterfaceCollection.match_synergies(card_1.ICollection, deck.forgeborn.ICollection)
                synFC_matches = InterfaceCollection.match_synergies(deck.forgeborn.ICollection, card_1.ICollection)

                if len(synCC_matches) > 0:                    
                    for synergy, count in synCC_matches.items(): 
                        if count > 0:
                            G.add_edge(card_name_1, card_name_1, label=synergy, weight = count)                              
                
                if len(synCF_matches) > 0:                    
                    for synergy, count in synCF_matches.items():                             
                        if count > 0:
                            G.add_edge(card_name_1, deck.forgeborn.name, label=synergy, weight = count) 

                if len(synFC_matches) > 0:                    
                    for synergy, count in synFC_matches.items():
                        if count > 0:
                            G.add_edge(deck.forgeborn.name, card_name_1, label=synergy, weight = count)                                                     
                
            if i < j:
                # compare only cards whose indices are greater        
                # Check if the cards have any synergies                

                c12_matches = InterfaceCollection.match_synergies(card_1.ICollection, card_2.ICollection)
                c21_matches = InterfaceCollection.match_synergies(card_2.ICollection, card_1.ICollection)

                if len(c12_matches) > 0 :                        
                    for synergy, count in c12_matches.items():
                        if count > 0:
                            G.add_edge(card_name_1, card_name_2, label=synergy, weight = count) 

                if len(c21_matches) > 0 :                        
                    for synergy, count in c21_matches.items():
                        if count > 0:
                            G.add_edge(card_name_2, card_name_1, label=synergy, weight = count)

    # Apply Girvan-Newman algorithm
    #comp = community.girvan_newman(G)

    # Extract the communities
    #communities = tuple(sorted(c) for c in next(comp))

    #print(communities)

    Metric = {}
   
    Metric['PageRank'] = nx.pagerank(G, alpha=0.85, personalization=None, max_iter=1000, tol=1e-06, nstart=None, dangling=None)
    Metric['degree'] = nx.degree_centrality(G)
    #Metric['eigenvector'] = nx.eigenvector_centrality(G,max_iter=1000)
    Metric['between']    = nx.betweenness_centrality(G)
    Metric['katz'] = nx.katz_centrality(G, alpha=0.1, beta=1.0)
    partition = community.greedy_modularity_communities(G)
    mod = community.modularity(G, partition)
    clustering_coefficients = nx.average_clustering(G)
    density = nx.density(G)
    
    G.graph['mod'] = mod    
    G.graph['cluster_coeff'] = clustering_coefficients    
    G.graph['density'] = density

    for name, metric in Metric.items():
        nx.set_node_attributes(G, metric, name)
    
    for node_name in G.nodes:       
        total = sum([ metric[node_name] for metric in Metric.values()]) 
        G.nodes[node_name]['total'] = total        
        G.graph['value'] += total     

    return G

def plot_synergy_graph(G):
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, font_weight="bold")
    labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
    #nx.draw_networkx_labels(G, pos, labels={node: node for node in G.nodes()}, font_size=10)
    plt.show()

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