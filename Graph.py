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
    G = nx.DiGraph(name = deck.name, mod = 0, value = 0)
    #print(f"Card Synergies between decks: {deck.name}")    
    synergy_template = SynergyTemplate()
    
    G.add_nodes_from(deck.cards)

    for i, (card_name_1, card_1) in enumerate(deck.cards.items()):
        for j, (card_name_2, card_2) in enumerate(deck.cards.items()):                

            if i == j:
                synC = SynergyCollection.from_card(card_1,)
                synF = SynergyCollection.from_forgeborn(deck.forgeborn, synergy_template)
                
                if len(synC.synergies) > 0:
                   syn_str = ", ".join([f"{syn}" for syn in synC.synergies])
                   for name, syn in synC.synergies.items():
                       G.add_edge(card_name_1, card_name_1, label=name, weight = syn.weight)  

                synCF = SynergyCollection(synC.sources, synF.targets)
                synFC = SynergyCollection(synF.sources, synC.targets)

                if len(synCF.synergies) > 0:
                    for name, syn in synCF.synergies.items():
                        G.add_edge(card_name_1, deck.forgeborn.name, label=name, weight = syn.weight)            

                if len(synFC.synergies) > 0:
                    for name, syn in synFC.synergies.items():
                        G.add_edge(deck.forgeborn.name, card_name_1, label=name, weight = syn.weight)            

                     
            if i < j:
            # compare only cards whose indices are greater        
                # Check if the cards have any synergies                
                syn1 = SynergyCollection.from_card(card_1,synergy_template)
                syn2 = SynergyCollection.from_card(card_2,synergy_template)
                            
                c1_2 = SynergyCollection(syn1.sources, syn2.targets, synergy_template)
                c2_1 = SynergyCollection(syn2.sources, syn1.targets, synergy_template)

                if len(c1_2.synergies) > 0 :                    
                    syn_str = ", ".join([f"{syn}" for syn in c1_2.synergies])
                    for name, syn in c1_2.synergies.items():
                        G.add_edge(card_name_1, card_name_2, label=name, weight = syn.weight)            

                if len(c2_1.synergies) > 0:
                    syn_str = ", ".join([f"{syn}" for syn in c2_1.synergies])
                    for name, syn in c2_1.synergies.items():
                        G.add_edge(card_name_2, card_name_1, label=name, weight = syn.weight)            
    
    Metric = { "katz" : 0,
               "between" : 0,               
               "degree" : 0,
               "PageRank" : 0
    }

    # Apply Girvan-Newman algorithm
    comp = community.girvan_newman(G)

    # Extract the communities
    communities = tuple(sorted(c) for c in next(comp))

    print(communities)

    
    Metric['PageRank'] = nx.pagerank(G, alpha=0.85, personalization=None, max_iter=1000, tol=1e-06, nstart=None, dangling=None)
    Metric['degree'] = nx.degree_centrality(G)
    #Metric['eigenvector'] = nx.eigenvector_centrality(G,max_iter=1000)
    Metric['between']    = nx.betweenness_centrality(G)
    Metric['katz'] = nx.katz_centrality(G, alpha=0.1, beta=1.0)
    partition = community.greedy_modularity_communities(G)
    mod = community.modularity(G, partition)
    

       
    G.graph['mod'] = mod    

    for name, metric in Metric.items():
        nx.set_node_attributes(G, metric, name)
    
    for node_name in G.nodes:       
        total = sum([ metric[node_name] for metric in Metric.values()]) 
        G.nodes[node_name]['total'] = total        
        G.graph['value'] += total     
    
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
    nx.write_gexf(graph, './gephi/' + filename + '.gexf')