import os
import networkx as nx
import webbrowser
from pyvis.network import Network
from IPython.display import display

from MyGraph import MyGraph
from GlobalVariables import global_vars as gv

def display_graph(selected_items_list):
    """
    Function to display a graph based on selected items.
    
    Parameters:
    - grid_manager: Instance of GridManager.
    - gv: GlobalVariables instance.
    - graph_output: Output widget to display the graph.
    - selected_items_label: Label widget containing selected items.
    - user_dataframes: Dictionary mapping usernames to their dataframes.
    """
    # Clear previous graph output
    #graph_output.clear_output()

    # Ensure the 'html' subfolder exists
    os.makedirs('html', exist_ok=True)
    
    #with graph_output:
    name = ''
    graph = {}
    for item in selected_items_list:            
        for item_type in ['Deck', 'Fusion']:
            print(f"Searching {item_type} with name: {item.strip()}")
            item_cursor = gv.myDB.find_one(item_type, {'name': item.strip()})
            if item_cursor:                    
                name = item_cursor.get('name', '')
                graph = item_cursor.get('graph', {})                    
                break
            else:
                print(f"No {item_type} found with name: {item.strip()}")
                                        
        if graph:
            myGraph = MyGraph()
            myGraph.from_dict(graph)
                        
            # Create a NetworkX graph from the dictionary                
            graph = myGraph.G
            #net = visualize_network_graph(graph)
            net = Network(notebook=True, directed=True, height='1500px', width='2000px', cdn_resources='in_line')    
            net.from_nx(graph)
            net.force_atlas_2based()
            #net.show_buttons(True)
                                    
            filename = f'html/{name}.html'
            net.show(filename)
            
            # Read HTML file content and display using IPython HTML
            filepath = os.path.join(os.getcwd(), filename)
            if os.path.exists(filepath):
                webbrowser.open(f'file://{filepath}')
                #display(HTML(filename))
            else:
                print(f"File {filename} not found.")
        else:
            print(f"No graph found for item: {item}")
            
                
                
# Visualization
def visualize_network_graph(graph, size=10):
    # Modify the labels of the nodes to include the length of the parents list
    degree_centrality = nx.degree_centrality(graph)
    betweenness_centrality = nx.betweenness_centrality(graph)
    #partition = nx.community.label_propagation_communities(graph)

    metric = betweenness_centrality

    # for node, value in metric.items() :
    #     decimal = value * size * 1000
    #     graph.nodes[node]['value'] = decimal
    #     graph.nodes[node]['label'] = node

    # for node, data in graph.nodes(data=True):
    #     num_parents = len(data.get('parents', []))        
    #     graph.nodes[node]['label'] += f'[{num_parents}]'
        
    net = Network(notebook=True, directed=True, height='1500px', width='2000px', cdn_resources='in_line')    
    net.from_nx(graph)
    net.force_atlas_2based()
    #net.show_buttons()
    #print('Displaying Graph!')
    #display(net.show('graph.html'))
    return net
