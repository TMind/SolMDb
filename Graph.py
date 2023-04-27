from DeckLibrary import DeckEvaluator
import networkx as nx
import matplotlib.pyplot as plt

def create_synergy_graph(decks, min_level=1):
    G = nx.Graph()
    decks = list(decks.values())
    for i in range(len(decks)):
        for j in range(i+1, len(decks)):
            if decks[i].faction != decks[j].faction:
                DeckEvaluation = DeckEvaluator([decks[i],decks[j]])                         
                for fb_name, score in DeckEvaluation.scores.items():
                    if score >= min_level:                        
                        G.add_edge(decks[i].name, decks[j].name, weight=score, label=fb_name)

    # Remove nodes with no edges
    nodes_to_remove = [node for node, degree in dict(G.degree()).items() if degree == 0]
    G.remove_nodes_from(nodes_to_remove)

    return G

def plot_synergy_graph(G):
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, font_weight="bold")
    labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
    #nx.draw_networkx_labels(G, pos, labels={node: node for node in G.nodes()}, font_size=10)
    plt.show()

def write_gephi_file(graph, filename):
    nx.write_gexf(graph, filename + '.gexf')