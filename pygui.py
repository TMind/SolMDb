import os, time, re
from arrow import get
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
import qgrid

import icecream as ic

# Define Variables
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

logging.basicConfig(level=logging.INFO)
GlobalVariables.username = 'enterUsernameHere'
uri = "mongodb://localhost:27017"
#uri = "mongodb+srv://solDB:uHrpfYD1TXVzf3DR@soldb.fkq8rio.mongodb.net/?retryWrites=true&w=majority&appName=SolDB"
myDB = DatabaseManager(GlobalVariables.username)
commonDB = DatabaseManager('common')

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
username = None
db_list = None 
card_title_widget = None 

out = widgets.Output()
out_df = widgets.Output()


# Network Operations
def fetch_network_decks(args, myApi):
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
def load_deck_data(args):
    net_decks = []
    net_fusions = []

    myApi = NetApi(myUCL)                    
    net_results = fetch_network_decks(args, myApi)            
        
    if args.type == 'deck':     net_decks = net_results
    elif args.type == 'fuseddeck': net_fusions = net_results
        
    deckCollection = DeckLibrary(net_decks, net_fusions, args.mode)

# Data Handling and Transformation 
def generate_deck_statistics_dataframe():
    global card_title_widget

    def get_card_title(card_id):
        card = myDB.find_one('Card', {'_id': card_id})
        return card['title'] if card else None

    def get_forgeborn_name(forgeborn_id):
        forgeborn = commonDB.find_one('Forgeborn', {'_id': forgeborn_id})
        return forgeborn['name'] if forgeborn else None

    def filter_by_card_title(df, title):
        return df[df['cardTitles'].apply(lambda titles: title in titles)]

    # Get all Decks from the database
    deck_cursor = myDB.find('Deck', {})
    df_decks = pd.DataFrame(list(deck_cursor))
    df_decks_filtered = df_decks[[ 'registeredDate', 'name', 'cardSetNo', 'faction', 'forgebornId']].copy()
    df_decks_filtered['cardTitles'] = df_decks['cardIds'].apply(lambda card_ids: [get_card_title(card_id) for card_id in card_ids])

    additional_columns = ['A1', 'A2', 'A3', 'H1', 'H2', 'H3']
    for column in additional_columns:
        df_decks_filtered.loc[:,column] = 0.0

    df_decks_filtered.set_index('name', inplace=True)

    # Create a DataFrame from the 'stats' sub-dictionary

    for deck in myDB.find('Deck', {}):
        if 'stats' in deck:
            
            stats = deck.get('stats', {})
            # Convert the 'card_types' sub-dictionary into a DataFrame
            card_types_df = pd.DataFrame.from_dict(stats['card_types'], orient='index')
            creature_averages_df = pd.DataFrame.from_dict(stats['creature_averages'], orient='index')
            
            # Flatten the 'creature_averages' sub-dictionaries into a single-row DataFrame
            # Convert the dictionary into a DataFrame
            attack_dict = stats['creature_averages']['attack']
            attack_df = pd.DataFrame([attack_dict], columns=attack_dict.keys())
            attack_df.columns = ['A1', 'A2', 'A3']

            defense_dict = stats['creature_averages']['health']
            defense_df = pd.DataFrame([defense_dict], columns=defense_dict.keys())
            defense_df.columns = ['H1', 'H2', 'H3']
            
            # Combine the attack and defense DataFrames into a single DataFrame
            deck_stats_df = pd.concat([attack_df, defense_df], axis=1)
            deck_stats_df['name'] = deck['name']
            
            # Round each value in the DataFrame
            deck_stats_df = deck_stats_df.round(2)
                                            
            # Set the common column as the index in both dataframes
            deck_stats_df.set_index('name', inplace=True)

            # Update the corresponding row in df_decks_filtered with the stats from deck_stats_df
            df_decks_filtered.update(deck_stats_df)

        # Replace forgebornId with the forgeborn name from the database     
        forgeborn_name = get_forgeborn_name(deck['forgebornId'])
        #forgeborn = commonDB.find('Forgeborn', {'_id': deck['forgebornId']})
        
        if forgeborn_name:        
            df_decks_filtered.loc[deck['name'], 'forgebornId'] = forgeborn_name

    if card_title_widget and card_title_widget.value != '-':
        df_filter = filter_by_card_title(df_decks_filtered, card_title_widget.value)
        if not df_filter.empty:
            df_decks_filtered = df_filter    

    # Add the cardTitles back to the DataFrame
    #df_decks_filtered['cardTitles'] = cardTitles

    # Reset the index in df_decks_filtered
    df_decks_filtered.reset_index(inplace=True)
    return df_decks_filtered

# User Interface Management
def create_faction_selection_toggle(faction_names, initial_style='info'):
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
def create_deck_grid_view(dataframe):

    col_options =           { 'width': 50, }
    col_defs = {        
        'name':             { 'width': 250, },
        'registeredDate':   { 'width': 200, },
        'cardSetNo':        { 'width': 50,  },
        'faction':          { 'width': 100,  },
        'forgebornId':      { 'width': 100,  },
        'cardTitles':       { 'width': 200,  },
    }

    qgrid_df = qgrid.show_grid(dataframe,
                            column_options=col_options,
                            column_definitions=col_defs,
                            grid_options={'forceFitColumns': False},
                            show_toolbar=False)
    return qgrid_df
def initialize_widgets() :
    factionToggle = create_faction_selection_toggle(factionNames)
    dropdown = widgets.Dropdown()
    refresh_dropdown_options(factionToggle, dropdown)
    factionToggle.observe(lambda change: refresh_dropdown_options(factionToggle, dropdown), 'value')
    return factionToggle, dropdown
def create_database_selection_widget():
    global username
    db_names = myDB.mdb.client.list_database_names()
    db_names = [db for db in db_names if db not in ['local', 'admin', 'common', 'config']]
    db_list = widgets.RadioButtons(
        options=db_names,
        description='Databases:',
        disabled=False
    )
    # Set the username to the value of the selected database
    
    GlobalVariables.username = db_list.value or 'user'
    myDB.set_database_name(GlobalVariables.username)
    # Also set the value of the username widget
    username.value = GlobalVariables.username

    def on_db_list_change(change):    
        username.value = change['new']

    db_list.observe(on_db_list_change, 'value')

    return db_list
def initialize_card_title_dropdown(username):
    myDB.set_database_name(username)
    all_card_titles = myDB.distinct('Card', 'title')
    all_card_titles = ['-'] + all_card_titles 
    card_title_widget = widgets.Dropdown(
        options=all_card_titles,
        description='Card Title:',
        ensure_option=False,
        layout=widgets.Layout(width="200px"),
        value='-'
    )
    return card_title_widget

# Event Handling
def handle_username_change(change):    
    global card_title_widget
    new_username = change['new']
    if new_username:  
        GlobalVariables.username = new_username
        myDB.set_database_name(GlobalVariables.username)
        for factionToggle, dropdown in zip(factionToggles, dropdowns):
            refresh_dropdown_options(factionToggle, dropdown)
        update_decks_display(change)
    else:
        print("Username cannot be an empty string")
def reload_data_on_click(button, value):
    global db_list
    print(f"Reloading {value}")
    if value == 'Decks':
        arguments = ["--username" , GlobalVariables.username, 
                    "--mode", 'update' ]
                        #"--filter", "C~Biologist" 
                        #"--type", "fuseddeck"  
        print(f"Loading Decks with arguments {arguments}")
        args = parse_arguments(arguments)
        load_deck_data(args)    
    elif value == 'Fusions':
        arguments = ["--username" , GlobalVariables.username, 
                    "--mode", 'update',
                     "--type", 'fuseddeck'
                     ]
                        #"--filter", "C~Biologist" 
                        #"--type", "fuseddeck"  
        print(f"Loading Fusions with arguments {arguments}")
        args = parse_arguments(arguments)
        load_deck_data(args)
    elif value == 'Entities':
        myUCL._read_entities_from_csv(os.path.join('csv', 'sff.csv'))
    elif value == 'Forgeborns':
        myUCL._read_forgeborn_from_csv(os.path.join('csv', 'forgeborn.csv'))
    
    # Refresh db_list widget
    db_names = myDB.mdb.client.list_database_names()
    db_list.options = [db for db in db_names if db not in ['local', 'admin', 'common', 'config']]
    db_list.value = GlobalVariables.username

    # Call refresh function for dropdowns
    handle_username_change({'new': GlobalVariables.username})
def display_graph_on_click(button):
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
                show_deck_graph(myFusion, out)
        else:
            # Create a new fusion based on the decknames
            newFusionData = FusionData(name=fusionName, myDecks=[myDeckA, myDeckB],tags=['forged'] )
            newFusion = Fusion(newFusionData)
            show_deck_graph(newFusion, out)
                
    else: 
        for deck in [myDeckA , myDeckB] :
            print(deck)
            if deck:
                myGraph = MyGraph()
                myGraph.create_graph_children(deck)
                net = visualize_network_graph(myGraph.G)
                display(net.show(f"{deck.name}.html"))
def update_decks_display(change):
    if change['new']:
        with out_df:
            out_df.clear_output()
            deck_df = generate_deck_statistics_dataframe()
            qgrid_widget = create_deck_grid_view(deck_df)
            display(qgrid_widget)
def refresh_dropdown_options(faction_toggle, dropdown):
    #print(f"Updating items for {faction_toggle.value} , username = {GlobalVariables.username}")
    myDB.set_database_name(GlobalVariables.username)    
    deckCursor = myDB.find('Deck', { 'faction' : faction_toggle.value })
    deckNames = []    
    deckNames = [deck['name'] for deck in deckCursor]
    dropdown.options = deckNames        

# Visualization
def visualize_network_graph(graph, size=10):
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
def show_deck_graph(deck, out):
    myGraph = MyGraph()
    myGraph.create_graph_children(deck)
    net = visualize_network_graph(myGraph.G)
    with out:
        out.clear_output() 
        display(net.show(f"{deck.name}.html"))

# Setup and Initialization
def setup_interface():
    global db_list, username, card_title_widget
    for i in range(2):            
        factionToggle, dropdown = initialize_widgets()
        factionToggles.append(factionToggle)
        dropdowns.append(dropdown)
        #dropdown.observe(on_deck_change)

    # Button to create network graph
    button_graph = widgets.Button(description="Show Graph")
    button_graph.on_click(lambda button: display_graph_on_click(button))

    # Toggle buttons to select load items
    loadToggle = widgets.ToggleButtons(
        options=types,
        description='Reload:',
        disabled=False,
        button_style='', # 'success', 'info', 'warning', 'danger' or ''
        tooltips=['Decks from the website', 'Fusions from the website', 'Entities from the Collection Manager Sheet sff.csv', 'Forgeborns from the forgeborns.csv', 'Synergies from the Synergys.csv'])


    username = widgets.Text(value=GlobalVariables.username, description='Username:', disabled=False)
    username.observe(lambda change: handle_username_change(change), 'value')

    db_list = create_database_selection_widget()
    db_list_box = widgets.VBox([db_list, out_df])

    card_title_widget = initialize_card_title_dropdown(GlobalVariables.username)
    card_title_widget.observe(update_decks_display, 'value')
    
    # Button to load decks / fusions / forgborns 
    button_load = widgets.Button(description="Load" )
    button_load.on_click(lambda button: reload_data_on_click(button, loadToggle.value))
    
    # Create a list of HBoxes of factionToggles, Labels, and dropdowns
    toggle_dropdown_pairs = [widgets.HBox([factionToggles[i], dropdowns[i]]) for i in range(len(factionToggles))]

    # Create a VBox to arrange the HBoxes vertically
    toggle_box = widgets.VBox([username, db_list_box, loadToggle, button_load, *toggle_dropdown_pairs, button_graph])

    display(card_title_widget)
    update_decks_display({'new': GlobalVariables.username})
    display(toggle_box)        
    display(out)    

