import os
#from __future__ import print_function
import ipywidgets as widgets
from pyvis.network import Network
import networkx as nx

import GlobalVariables
from CardLibrary import Deck, FusionData, Fusion
from MongoDB.DatabaseManager import DatabaseManager
from MyGraph import MyGraph

from soldb import main, parse_arguments
from IPython.display import display

# Define Variables
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

GlobalVariables.username = 'tmind'
myDB = DatabaseManager(GlobalVariables.username)

def graphToNet(graph, size=10):
    # Modify the labels of the nodes to include the length of the parents list
    degree_centrality = nx.degree_centrality(graph)
    betweenness_centrality = nx.betweenness_centrality(graph)
    #partition = nx.community.label_propagation_communities(graph)

    metric = betweenness_centrality

    for node, value in metric.items() :
        decimal = value * size * 1000
        graph.nodes[node]['value'] = decimal
        graph.nodes[node]['label'] = node

    for node, data in graph.nodes(data=True):
        num_parents = len(data.get('parents', []))        
        graph.nodes[node]['label'] += f"[{num_parents}]"
        
    net = Network(notebook=True, directed=True, height="1500px", width="2000px", cdn_resources='in_line')    
    net.from_nx(graph)
    net.force_atlas_2based()
    net.show_buttons()
    print("Displaying Graph!")
    #display(net.show('graph.html'))
    return net

def create_faction_toggle(faction_names, initial_style='info'):
    faction_toggle = widgets.ToggleButtons(
        options=faction_names,
        description='Faction:',
        disabled=False,
        button_style=initial_style,
        tooltips=['Description of slow', 'Description of regular', 'Description of fast'],
    )

    def update_button_style(change):
        if change['new'] == 'Alloyin':
            faction_toggle.button_style = 'info'
        elif change['new'] == 'Nekrium':
            faction_toggle.button_style = 'warning'
        elif change['new'] == 'Tempys':
            faction_toggle.button_style = 'danger'
        elif change['new'] == 'Uterra':
            faction_toggle.button_style = 'success'

    faction_toggle.observe(update_button_style, 'value')

    return faction_toggle

def button_load_decks(button):
    arguments = ["--username" , GlobalVariables.username, 
                 "--mode", 'update' ]
                    #"--filter", "C~Biologist" 
                    #"--type", "fuseddeck"  
                    
    args = parse_arguments(arguments)
    main(args)    

def button_on_click(button, dropdown1, dropdown2, out):
    myDeckA = Deck.lookup(dropdown1.value)
    myDeckB = Deck.lookup(dropdown2.value)

    if myDeckA and myDeckB:
        fusionName = f"{myDeckA.name}_{myDeckB.name}"
        fusionCursor = myDB.find('Fusion', {'name' : fusionName})
        if fusionCursor: 
            for fusion in fusionCursor:
                myFusion = Fusion.from_data(fusion)
                display_graph(myFusion, out)
        else:
            # Create a new fusion based on the decknames
            newFusionData = FusionData(name=fusionName, myDecks=[myDeckA, myDeckB],tags=['forged'] )
            newFusion = Fusion(newFusionData)
            display_graph(newFusion, out)
                
    else: 
        for deck in [myDeckA , myDeckB] :
            print(deck)
            if deck:
                myGraph = MyGraph()
                myGraph.create_graph_children(deck)
                net = graphToNet(myGraph.G)
                display(net.show(f"{deck.name}.html"))

def on_username_change(change, factionToggle1, dropdown1, factionToggle2, dropdown2):
    new_username = change['new']
    if new_username:  # Check that the username is not empty
        #print(f"Changing username -> {new_username}")
        GlobalVariables.username = new_username
        myDB.set_database_name(GlobalVariables.username)
        update_items(factionToggle1, dropdown1)
        update_items(factionToggle2, dropdown2)
    else:
        print("Username cannot be an empty string")

def display_graph(deck, out):
    myGraph = MyGraph()
    myGraph.create_graph_children(deck)
    net = graphToNet(myGraph.G)
    with out:
        out.clear_output() 
        display(net.show(f"{deck.name}.html"))

def update_items(faction_toggle, dropdown):
    #print(f"Updating items for {faction_toggle.value} , username = {GlobalVariables.username}")
    myDB.set_database_name(GlobalVariables.username)
    deckCursor = myDB.find('Deck', {'faction' : faction_toggle.value})
    deckNames = [deck['name'] for deck in deckCursor]
    dropdown.options = deckNames        

def create_widgets(name, factionNames) :
    factionToggle = create_faction_toggle(factionNames)
    dropdown = widgets.Dropdown()
    update_items(factionToggle, dropdown)
    factionToggle.observe(lambda change: update_items(factionToggle, dropdown), 'value')
    return factionToggle, dropdown

def create_interface():

    factionNames = ['Alloyin', 'Nekrium', 'Tempys', 'Uterra']
    deckNames = []

    out = widgets.Output()

    factionToggle1, dropdown1 = create_widgets('First', factionNames)       
    factionToggle2, dropdown2 = create_widgets('Second', factionNames)       

    button_graph = widgets.Button(description="Show Graph")
    button_graph.on_click(lambda button: button_on_click(button, dropdown1, dropdown2, out))

    button_load = widgets.Button(description="Load Decks" )
    button_load.on_click(lambda button: button_load_decks(button))

    username = widgets.Text(value='tmind', description='Username:', disabled=False)
    username.observe(lambda change: on_username_change(change, factionToggle1, dropdown1, factionToggle2, dropdown2), 'value')

    display(username, button_load, factionToggle1, dropdown1, factionToggle2, dropdown2, button_graph)
    display(out)    

