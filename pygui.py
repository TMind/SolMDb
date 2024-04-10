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
import pandas as pd


# Define Variables
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

logging.basicConfig(level=logging.INFO)
GlobalVariables.username = 'enterUsernameHere'
#uri = "mongodb://localhost:27017"
uri = "mongodb+srv://solDB:uHrpfYD1TXVzf3DR@soldb.fkq8rio.mongodb.net/?retryWrites=true&w=majority&appName=SolDB"
myDB = DatabaseManager(GlobalVariables.username)

synergy_template = SynergyTemplate()    

ucl_paths = [os.path.join('csv', 'sff.csv'), os.path.join('csv', 'forgeborn.csv'), os.path.join('csv', 'synergies.csv')]

#Read Entities and Forgeborns from Files into Database
myUCL = UniversalLibrary(GlobalVariables.username, *ucl_paths)
deckCollection = None

# Widget Variables
factionToggles = []
dropdowns = []
factionNames = ['Alloyin', 'Nekrium', 'Tempys', 'Uterra']
types = ['Decks', 'Fusions', 'Entities', 'Forgeborns']
    
out = widgets.Output()
out_df = widgets.Output()


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
        description='',
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

        # Force a redraw of the widget
        faction_toggle.layout = widgets.Layout()

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
    
    # Call refresh function for dropdowns
    on_username_change({'new': GlobalVariables.username})

def button_show_graph(button):
    myDecks = []
    for dropdown in dropdowns:
        myDecks.append(Deck.lookup(dropdown.value))
    
    myDeckA = myDecks[0]
    myDeckB = myDecks[1]

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


#def on_username_change(change, factionToggle1, dropdown1, factionToggle2, dropdown2):    
def on_username_change(change):    
    new_username = change['new']
    if new_username:  # Check that the username is not empty
        #print(f"Changing username -> {new_username}")
        GlobalVariables.username = new_username
        myDB.set_database_name(GlobalVariables.username)
        for factionToggle, dropdown in zip(factionToggles, dropdowns):
            update_items(factionToggle, dropdown)            
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
    deckCursor = myDB.find('Deck', { 'faction' : faction_toggle.value })
    deckNames = []    
    deckNames = [deck['name'] for deck in deckCursor]
    dropdown.options = deckNames        

def create_widgets() :
    factionToggle = create_faction_toggle(factionNames)
    dropdown = widgets.Dropdown()
    update_items(factionToggle, dropdown)
    factionToggle.observe(lambda change: update_items(factionToggle, dropdown), 'value')
    return factionToggle, dropdown

def create_database_list_widget(username):
    db_names = myDB.mdb.client.list_database_names()
    db_names = [db for db in db_names if db not in ['local', 'admin', 'common', 'config']]
    db_list = widgets.RadioButtons(
        options=db_names,
        description='Databases:',
        disabled=False
    )
    # Set the username to the value of the selected database
    GlobalVariables.username = db_list.value
    myDB.set_database_name(GlobalVariables.username)
    # Also set the value of the username widget
    username.value = GlobalVariables.username

    def on_db_list_change(change):    
        username.value = change['new']

    db_list.observe(on_db_list_change, 'value')

    return db_list

def display_deck_stats(deck_name):
    deck = myDB.find_one('Deck', {'name': deck_name})
    print(f"Deck has been changed: {deck_name}")
    if deck:
        print(f"Deck has been found: {deck_name}")
        stats = deck.get('stats', {})
        #df = pd.DataFrame.from_dict(stats, orient='index', columns=['Value'])
        # Convert the 'card_types' sub-dictionary into a DataFrame
        card_types_df = pd.DataFrame.from_dict(stats['card_types'], orient='index')

        # Convert the 'creature_averages' sub-dictionary into a DataFrame
        creature_averages_df = pd.DataFrame.from_dict({k: v for k, v in stats['creature_averages'].items()}, orient='index')

        # Replace NaN values with an empty string
        card_types_df = card_types_df.fillna('')
        creature_averages_df = creature_averages_df.fillna('')

        # Create a lable for the Deck Stats
        deck_stats_label = widgets.Label(value=f"Deck Stats for '{deck_name}':")

        # Display the DataFrames
        with out_df:
          out_df.clear_output()
          display(deck_stats_label)
          display(card_types_df)
          display(creature_averages_df)
    else:
        print(f"Deck '{deck_name}' not found in the database.")

# Define a function to be called when the dropdown value changes
def on_deck_change(change):
    if change['type'] == 'change' and change['name'] == 'value':
        display_deck_stats(change['new'])
        print(f"Deck has been changed: {change['new']}")

def create_interface():

    for i in range(2):            
        factionToggle, dropdown = create_widgets()
        factionToggles.append(factionToggle)
        dropdowns.append(dropdown)
        dropdown.observe(on_deck_change)

    # Button to create network graph
    button_graph = widgets.Button(description="Show Graph")
    button_graph.on_click(lambda button: button_show_graph(button))

    # Toggle buttons to select load items
    loadToggle = widgets.ToggleButtons(
        options=types,
        description='Reload:',
        disabled=False,
        button_style='', # 'success', 'info', 'warning', 'danger' or ''
        tooltips=['Decks from the website', 'Fusions from the website', 'Entities from the Collection Manager Sheet sff.csv', 'Forgeborns from the forgeborns.csv', 'Synergies from the Synergys.csv'])

    # Button to load decks / fusions / forgborns 
    button_load = widgets.Button(description="Load" )
    button_load.on_click(lambda button: button_reload(button, loadToggle.value))

    username = widgets.Text(value=GlobalVariables.username, description='Username:', disabled=False)
    username.observe(lambda change: on_username_change(change), 'value')

    db_list = create_database_list_widget(username)
    db_list_box = widgets.HBox([db_list, out_df])
    
   # Create a list of HBoxes of factionToggles, Labels, and dropdowns
    toggle_dropdown_pairs = [widgets.HBox([factionToggles[i], dropdowns[i]]) for i in range(len(factionToggles))]

    # Create a VBox to arrange the HBoxes vertically
    toggle_box = widgets.VBox([username, db_list_box, loadToggle, button_load, *toggle_dropdown_pairs, button_graph])

    display(toggle_box)        
    display(out)    

