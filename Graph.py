from DeckLibrary import DeckEvaluator, DeckLibrary
from Synergy import SynergyCollection,SynergyTemplate
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
    G = nx.DiGraph(name = deck.name, mod = 0, hubs = 0, value = 0)
    #print(f"Card Synergies between decks: {deck.name}")    

    for i, (card_name_1, card_1) in enumerate(deck.cards.items()):
        for j, (card_name_2, card_2) in enumerate(deck.cards.items()):                

            if i == j:
                syn1 = SynergyCollection.from_card(card_1,SynergyTemplate())
                
                if len(syn1.synergies) > 0:
                    syn_str = ", ".join([f"{syn}" for syn in syn1.synergies])
                    for syn in syn1.synergies:
                        G.add_edge(card_name_1, card_name_1, label=syn)  
                     
            if i < j:
            # compare only cards whose indices are greater        
                # Check if the cards have any synergies                
                syn1 = SynergyCollection.from_card(card_1,SynergyTemplate())
                syn2 = SynergyCollection.from_card(card_2,SynergyTemplate())
                            
                c1_2 = SynergyCollection(syn1.sources, syn2.targets, SynergyTemplate())
                c2_1 = SynergyCollection(syn2.sources, syn1.targets, SynergyTemplate())

                if len(c1_2.synergies) > 0 :                    
                    syn_str = ", ".join([f"{syn}" for syn in c1_2.synergies])
                    for syn in c1_2.synergies:
                        G.add_edge(card_name_1, card_name_2, label=syn)            

                if len(c2_1.synergies) > 0:
                    syn_str = ", ".join([f"{syn}" for syn in c2_1.synergies])
                    for syn in c2_1.synergies:
                        G.add_edge(card_name_2, card_name_1, label=syn)            
    

    # Calculate personalized PageRank
    pr = nx.pagerank(G, alpha=0.85, personalization=None, max_iter=1000, tol=1e-06, nstart=None, dangling=None)
    for card_name, value in pr.items():
        G.nodes[card_name]['pagerank'] = value


    degree_centrality = nx.degree_centrality(G)
    #eigenvector_centrality = nx.eigenvector_centrality(G,max_iter=1000)
    betweenness_centrality = nx.betweenness_centrality(G)
    partition = community.greedy_modularity_communities(G)
    mod = community.modularity(G, partition)
    for node_name in G.nodes:
        #print(f"EigenVector_Centrality: {eigenvector_centrality[node_name]}")
        #print(f"Betweenness_Centrality: {betweenness_centrality[node_name]}")
        #print(f"Degree_Centrality:      {degree_centrality[node_name]}")
        total = betweenness_centrality[node_name] + degree_centrality[node_name] 
        G.nodes[node_name]['product'] = total + G.nodes[node_name]['pagerank']
        G.graph['value'] += total 

    # calculate the number of hubs in the graph
    #degree_dict = dict(G.degree(G.nodes()))
    #hub_dict = {k: v for k, v in sorted(degree_dict.items(), key=lambda item: item[1], reverse=True)}
    #num_hubs = len([k for k, v in hub_dict.items() if v > 2]) # change the threshold as needed
    
    return G

def count_cycles(G):
    cycles = list(nx.simple_cycles(G))
    num_cycles = len(cycles)
    cycle_lengths = [len(cycle) for cycle in cycles]
    avg_cycle_length = sum(cycle_lengths) / num_cycles if num_cycles > 0 else 0

    print(f"Detected {num_cycles} cycles in the deck graph.")
    if num_cycles > 0:
        print(f"Average cycle length: {avg_cycle_length:.2f} cards.")
        #print(f"Cycle lengths: {cycle_lengths}")

def plot_synergy_graph(G):
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, font_weight="bold")
    labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
    #nx.draw_networkx_labels(G, pos, labels={node: node for node in G.nodes()}, font_size=10)
    plt.show()

def write_gephi_file(graph, filename):
    nx.write_gexf(graph, filename + '.gexf')