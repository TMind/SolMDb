import os, time, re
import ipywidgets as widgets
from pyvis.network import Network
import networkx as nx

import GlobalVariables
from CardLibrary import Deck, FusionData, Fusion
from UniversalLibrary import UniversalLibrary
from DeckLibrary import DeckLibrary
from MongoDB.DatabaseManager import DatabaseManager
from MyGraph import MyGraph
from NetApi import NetApi
from Filter import Filter

from soldb import main, parse_arguments
from IPython.display import display
import logging
from Synergy import SynergyTemplate


# Define Variables
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

logging.basicConfig(level=logging.INFO)
GlobalVariables.username = 'tmind'
#uri = "mongodb://localhost:27017"
uri = "mongodb+srv://solDB:uHrpfYD1TXVzf3DR@soldb.fkq8rio.mongodb.net/?retryWrites=true&w=majority&appName=SolDB"
myDB = DatabaseManager(GlobalVariables.username, uri=uri)

synergy_template = SynergyTemplate()    

ucl_paths = [os.path.join('csv', 'sff.csv'), os.path.join('csv', 'forgeborn.csv'), os.path.join('csv', 'synergies.csv')]

#Read Entities and Forgeborns from Files into Database
myUCL = UniversalLibrary(GlobalVariables.username, *ucl_paths)
deckCollection = None

def get_net_decks(args, myApi):
    if args.id:
        urls = args.id.split('\n')
        pattern = r"\/([^\/]+)$"        
        net_data  = []
        for url in urls:
            match = re.search(pattern, url)
            if match:
                id = match.group(1)
                url_data = myApi.request_decks(
                    id=id,
                    type=args.type,
                    username=args.username,
                    filename=args.filename
                )
                net_data  += url_data                
        return net_data
    else:
        net_data = myApi.request_decks(
            id=args.id,
            type=args.type,
            username=args.username,
            filename=args.filename
        )
        return net_data

def get_col_filter(args):
    if args.filter:
        query = args.filter
        attribute_map = {
            'F': ('faction', str, None),
            'D': ('name', str, None),
            'FB': ('forgeborn.name', str, None),
            'C': ('cards', dict, 'keys'),
            'A': ('abilities', dict, 'keys'),
            'K': ('composition', dict, None),
        }
        return Filter(query, attribute_map)
def load_decks(args):
    net_decks = []
    net_fusions = []

    myApi = NetApi(myUCL)                    
    net_results = get_net_decks(args, myApi)            
        
    if args.type == 'deck':     net_decks = net_results
    elif args.type == 'fuseddeck': net_fusions = net_results
        
    col_filter = get_col_filter(args)    
    deckCollection = DeckLibrary(net_decks, net_fusions, args.mode)

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

def button_reload(button, value):
    print(f"Reloading {value}")
    if value == 'Decks':
        arguments = ["--username" , GlobalVariables.username, 
                    "--mode", 'update' ]
                        #"--filter", "C~Biologist" 
                        #"--type", "fuseddeck"  
        print(f"Loading Decks with arguments {arguments}")
        args = parse_arguments(arguments)
        load_decks(args)    
    elif value == 'Fusions':
        arguments = ["--username" , GlobalVariables.username, 
                    "--mode", 'update',
                     "--type", 'fuseddeck'
                     ]
                        #"--filter", "C~Biologist" 
                        #"--type", "fuseddeck"  
        print(f"Loading Fusions with arguments {arguments}")
        args = parse_arguments(arguments)
        load_decks(args)
    elif value == 'Entities':
        myUCL._read_entities_from_csv(os.path.join('csv', 'sff.csv'))
    elif value == 'Forgeborns':
        myUCL._read_forgeborn_from_csv(os.path.join('csv', 'forgeborn.csv'))

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
    logging.info('on_username_change started')
    start_time = time.time()

    new_username = change['new']
    if new_username:  # Check that the username is not empty
        #print(f"Changing username -> {new_username}")
        GlobalVariables.username = new_username
        myDB.set_database_name(GlobalVariables.username)
        update_items(factionToggle1, dropdown1)
        update_items(factionToggle2, dropdown2)
    else:
        print("Username cannot be an empty string")
    
    end_time = time.time()
    logging.info('on_username_change finished, took %s seconds', end_time - start_time)

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
    deckCursor = myDB.find('Deck', { 'faction' : faction_toggle.value })
    deckNames = []    
    deckNames = [deck['name'] for deck in deckCursor]
    dropdown.options = deckNames        

def create_widgets(name, factionNames) :
    factionToggle = create_faction_toggle(factionNames)
    dropdown = widgets.Dropdown()
    update_items(factionToggle, dropdown)
    factionToggle.observe(lambda change: update_items(factionToggle, dropdown), 'value')
    return factionToggle, dropdown

def create_database_list_widget(username):
    db_names = myDB.mdb.client.list_database_names()
    db_names = [db for db in db_names if db not in ['local', 'admin', 'common']]
    db_list = widgets.Combobox(
        options=db_names,
        description='Databases:',
        disabled=False
    )

    def on_db_list_change(change):    
        username.value = change['new']

    db_list.observe(on_db_list_change, 'value')

    return db_list


def create_interface():

    factionNames = ['Alloyin', 'Nekrium', 'Tempys', 'Uterra']
    types = ['Decks', 'Fusions', 'Entities', 'Forgeborns']
        
    out = widgets.Output()

    
    factionToggle1, dropdown1 = create_widgets('First', factionNames)       
    factionToggle2, dropdown2 = create_widgets('Second', factionNames)       

    # Button to create network graph
    button_graph = widgets.Button(description="Show Graph")
    button_graph.on_click(lambda button: button_on_click(button, dropdown1, dropdown2, out))

    # Toggle buttons to select load items
    loadToggle = widgets.ToggleButtons(
        options=types,
        description='Reload:',
        disabled=False,
        button_style='', # 'success', 'info', 'warning', 'danger' or ''
        tooltips=['Decks from the website', 'Fusions from the website', 'Entities from the Collection Manager Sheet sff.csv', 'Forgeborns from the forgeborns.csv', 'Synergies from the Synergys.csv'])

    # Button to load decks / fusions / forgborns 
    button_load = widgets.Button(description="Load Decks" )
    button_load.on_click(lambda button: button_reload(button, loadToggle.value))

    username = widgets.Text(value=GlobalVariables.username, description='Username:', disabled=False)
    username.observe(lambda change: on_username_change(change, factionToggle1, dropdown1, factionToggle2, dropdown2), 'value')

    db_list = create_database_list_widget(username)

    display(username, db_list, loadToggle, button_load, factionToggle1, dropdown1, factionToggle2, dropdown2, button_graph)
    display(out)    

