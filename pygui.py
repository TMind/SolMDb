import os, time, re
from arrow import get
import ipywidgets as widgets
from networkx import combinatorial_embedding_to_pos
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

from Synergy import SynergyTemplate
import pandas as pd
import qgrid

from icecream import ic
ic.disable()

# Define Variables
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

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
cardTypes_names_widget = {}

out = widgets.Output()
out_df = widgets.Output()

######################
# Network Operations #
######################

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

def generate_synergy_statistics_dataframe(deck_df):
    global synergy_template
    #Start with an empty dataframe
    synergy_df = pd.DataFrame()

    #Get the tags from the synergy_template
    input_tags = list(synergy_template.get_input_tags())
    output_tags = list(synergy_template.get_output_tags())

    tags = input_tags + output_tags

    synergy_df['tag'] = tags

    # Now add columns for each deck from the statistics dataframe 
    if 'name' in deck_df.columns:
        decklist = deck_df['name']

        # Create a DataFrame with column names as keys and 0 as values
        new_columns_df = pd.DataFrame(0, columns=decklist, index=synergy_df.index, dtype=float)    
        # Assuming `df` is your DataFrame and `column` is the name of the column you want to downcast
        #synergy_df[column] = df[column].fillna(0).astype(int)
        # Concatenate the original DataFrame with the new columns DataFrame
        synergy_df = pd.concat([synergy_df, new_columns_df], axis=1)

    return synergy_df

# Data Handling and Transformation 
def generate_deck_statistics_dataframe():
    global cardTypes_names_widget

    def get_card_title(card_id):
        card = myDB.find_one('Card', {'_id': card_id})
        if card: 
            if 'title' in card:
                return card['title']
            elif 'name' in card:
                return card['name']
            else:
                print(f"Card {card_id} has no title/name")
                return ''
        else:
            print(f"Card {card_id} not found")
            return ''

    def get_forgeborn_name(forgeborn_id):
        forgeborn = commonDB.find_one('Forgeborn', {'_id': forgeborn_id})
        return forgeborn['name'] if forgeborn else None

    def get_forgeborn_abilities(forgeborn_id):
        forgeborn = commonDB.find_one('Forgeborn', {'_id': forgeborn_id})
        return forgeborn['abilities'] if forgeborn else None

    def get_card_titles(card_ids):
        card_titles = []
        for card_id in card_ids:
            card_title = get_card_title(card_id)
            card_titles.append(card_title)
        return card_titles

    # Get all Decks from the database
    try:
        deck_cursor = myDB.find('Deck', {})        
        df_decks = pd.DataFrame(list(deck_cursor))
        df_decks_filtered = df_decks[[ 'registeredDate', 'name', 'cardSetNo', 'faction', 'forgebornId']].copy()
        df_decks_filtered['cardTitles'] = df_decks['cardIds'].apply(get_card_titles)
    except:
        print("Error reading decks from the database. Try reloading the data.")
        return pd.DataFrame()

    # Add additional columns to the DataFrame -> FB
    additional_columns_fb = ['FB1', 'FB2', 'FB3']
    for column in additional_columns_fb:
        df_decks_filtered.loc[:,column] = ''

    # Add additional columns to the DataFrame -> Stats
    additional_columns_stats = ['A1', 'A2', 'A3', 'H1', 'H2', 'H3']
    for column in additional_columns_stats:
        df_decks_filtered.loc[:,column] = 0.0
            
    df_decks_filtered.set_index('name', inplace=True)

    # Create a DataFrame from the fb_abilities sub-dictionary
    for deck in myDB.find('Deck', {}):
        if 'forgebornId' in deck:
            forgeborn_id = deck['forgebornId']
            forgeborn_abilities = get_forgeborn_abilities(forgeborn_id)
            if forgeborn_abilities:
                for i in range(len(forgeborn_abilities)):
                    df_decks_filtered.loc[deck['name'], f'FB{i+1}'] = forgeborn_abilities[i]

            # Replace forgebornId with the forgeborn name from the database     
            forgeborn_name = get_forgeborn_name(forgeborn_id) 
            if forgeborn_name:
                df_decks_filtered.loc[deck['name'], 'forgebornId'] = forgeborn_name
                
    # Create a DataFrame from the 'stats' sub-dictionary
    for deck in myDB.find('Deck', {}):
        if 'stats' in deck:
            
            stats = deck.get('stats', {})
            # Convert the 'card_types' sub-dictionary into a DataFrame
            #card_types_df = pd.DataFrame.from_dict(stats['card_types'], orient='index')
            #creature_averages_df = pd.DataFrame.from_dict(stats['creature_averages'], orient='index')
            
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

    def check_substring_in_titles(titles, substring):
        if titles:
            for title in titles:
                if title:                    
                    if substring in title:
                        return True
                    #print(f"{substring} not in {titles}")        
                else:
                    print(f"Title is empty")
        else:
            print(f"Titles is empty")
        return False
        
    def filter_by_substring(df, substring): 
        if substring == '':      return df
        else:
            theDF = df['cardTitles'] 
            myDF = theDF.apply(check_substring_in_titles, substring=substring)
            ret_df = df[myDF]
        return ret_df

    df_filtered = df_decks_filtered
    for dropdown in cardTypes_names_widget.values():   
        if not df_filtered.empty:         
            df_filtered = filter_by_substring(df_filtered, dropdown.value)   
            ic(df_filtered)     
        else:
            print("Dataframe is empty")            

    df_decks_filtered = df_filtered

    # Reset the index in df_decks_filtered
    df_decks_filtered.reset_index(inplace=True)
    return df_decks_filtered

##################
# Event Handling #
##################

# Function to handle changes to the checkbox
def handle_debug_toggle(change):
    if change.new:
        ic.enable()
    else:
        ic.disable()

def handle_username_change(change):    
    global cardTypes_names_widget

    new_username = change['new']
    if new_username:  
        GlobalVariables.username = new_username
        myDB.set_database_name(GlobalVariables.username)
        for factionToggle, dropdown in zip(factionToggles, dropdowns):
            refresh_faction_deck_options(factionToggle, dropdown)
        update_filter_widget()    
        update_decks_display(change)          
    else:
        print("Username cannot be an empty string")

def reload_data_on_click(button, value):
    global db_list
    print(f"Reloading {value}")
    if value == 'Decks':
        arguments = ["--username" , GlobalVariables.username, 
                    "--mode", 'update' ]                        
        print(f"Loading Decks with arguments {arguments}")
        args = parse_arguments(arguments)
        load_deck_data(args)    
    elif value == 'Fusions':
        arguments = ["--username" , GlobalVariables.username, 
                    "--mode", 'update',
                     "--type", 'fuseddeck'
                     ]                        
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
    if change['new'] or change['new'] == '':
        with out_df:
            out_df.clear_output()
            deck_df = generate_deck_statistics_dataframe()
            syn_df  = generate_synergy_statistics_dataframe(deck_df)
            
            if not deck_df.empty:
                qgrid_widget = create_deck_grid_view(deck_df)
                display(qgrid_widget)            

            if not syn_df.empty:
                            qgrid_widget = create_syn_grid_view(syn_df)
                            display(qgrid_widget)            

def update_filter_widget(change=None):
    global cardTypes_names_widget
    
    # Get values of both widgets
    widget_values = {cardTypesString: cardType_widget.value for cardTypesString, cardType_widget in cardTypes_names_widget.items()}

    if not change or all(value == '' for value in widget_values.values()):    
        # If no change is passed or both values are '' , update both widgets
        for cardTypesString, cardType_widget in cardTypes_names_widget.items():
            if cardType_widget:
                new_options = []
                for cardType in cardTypesString.split('/'):
                    new_options = new_options + get_cardType_entity_names(cardType)                
                cardType_widget.options = [''] + new_options
    else:
        # If a change is passed, update the other widget
        changed_widget = change['owner']  
        if change['new'] == '':             
            # Get the value of the other widget from the already fetched values
            for cardTypesString, cardType_widget in cardTypes_names_widget.items():
                if cardType_widget and cardType_widget != changed_widget:                    
                    change['new'] = widget_values[cardTypesString]
                    change['owner'] = cardType_widget                        
            update_filter_widget(change)            
        else:
            for cardTypesString, cardType_widget in cardTypes_names_widget.items():
                if cardType_widget and cardType_widget != changed_widget and cardType_widget.value == '':                
                    new_options = []
                    for cardType in cardTypesString.split('/'):
                        new_options = new_options + get_cardType_entity_names(cardType)           
                    new_options = filter_options(change['new'], new_options)  # Filter the options                         
                    cardType_widget.options = [''] + new_options    
    

def filter_options(value, options):
    # First get all card names from the database
    cards = myDB.find('Card', {})
    cardNames = [card['name'] for card in cards]

    # Filter all cardnames where value is a substring of 
    filtered_cardNames = [cardName for cardName in cardNames if value in cardName]

    # Filter all filtered_options that are a substring of any card name
    filtered_options = [option for option in options if any(option in cardName for cardName in filtered_cardNames)]
    
    # That should leave us with the options that are a substring of any card name and contain the value as a substring
    
    #print(f"Filtered options for {value}: {filtered_options}")
    return filtered_options
    


def refresh_faction_deck_options(faction_toggle, dropdown):    
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

#############################
# User Interface Management #
#############################

def create_debug_toggle():
    debug_toggle = widgets.ToggleButton(
        value=False,
        description='Debug',
        disabled=False,
        button_style='info', # 'success', 'info', 'warning', 'danger' or ''
        tooltip='Enable or disable debugging',
        icon='check'
    )
    debug_toggle.observe(handle_debug_toggle, 'value')
    return debug_toggle

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

def create_syn_grid_view(dataframe):

    col_options =   {                                                 
                        'defaultColumnWidth' : 700,
                    }
    col_defs = {                
        'tag':              { 'width': 175, },
        'index':            { 'width': 50,  },
    }

    qgrid_df = qgrid.show_grid(dataframe,
                            column_options=col_options,
                            column_definitions=col_defs,
                            grid_options={'forceFitColumns': False},
                            show_toolbar=False)
    return qgrid_df


def create_deck_grid_view(dataframe):

    col_options =           { 'width': 50, }
    col_defs = {        
        'name':             { 'width': 250, },
        'registeredDate':   { 'width': 200, },
        'cardSetNo':        { 'width': 50,  },
        'faction':          { 'width': 100,  },
        'forgebornId':      { 'width': 100,  },
        'cardTitles':       { 'width': 200,  },
        'FB1':              { 'width': 150,  },
        'FB2':              { 'width': 150,  },
        'FB3':              { 'width': 150,  },
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
    refresh_faction_deck_options(factionToggle, dropdown)
    factionToggle.observe(lambda change: refresh_faction_deck_options(factionToggle, dropdown), 'value')
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
    if username:
        username.value = GlobalVariables.username

    def on_db_list_change(change):    
        if username:
            username.value = change['new']

    db_list.observe(on_db_list_change, 'value')

    return db_list

def create_cardType_names_dropdown(cardTypes):
    cardType_entity_names = []
    for cardType in cardTypes.split('/'):
        cardType_entity_names = cardType_entity_names + get_cardType_entity_names(cardType)

    cardType_entity_names = [''] + cardType_entity_names 

    cardType_name_widget = widgets.Dropdown(
        options=cardType_entity_names,
        description='',
        ensure_option=False,
        layout=widgets.Layout(width="200px"),
        value=''
    )
    return cardType_name_widget

def get_cardType_entity_names(cardType):

    #print(f"Getting entity names for {cardType}")

    cardType_entities  = commonDB.find('Entity', {"attributes.cardType": cardType})       
    cardType_entities_names = [cardType_entity['name'] for cardType_entity in cardType_entities]    
    ic(cardType_entities_names)

    # Get cardnames from the database
    def get_card_title(card):
        if card: 
            if 'title' in card:
                return card['title']
            elif 'name' in card:
                return card['name']
            else:
                print(f"Card {card} has no title/name")
                return ''
        else:
            print(f"Card {card} not found")
            return ''

    cards = myDB.find('Card', {})
    cardNames = [get_card_title(card) for card in cards]

    # Filter all strings where the entity name is a substring of any card name
    cardType_entities_names = [cardType_entity for cardType_entity in cardType_entities_names if any(cardType_entity in cardName for cardName in cardNames)]

    #Sort cardType_entities_names
    cardType_entities_names.sort()

    #print(f"Entity names for {cardType}: {cardType_entities_names}")
    return cardType_entities_names

def create_filter_widgets():
    global cardTypes_names_widget

    # Initialize two empty lists to hold the labels and widgets
    label_items = []
    widget_items = []

    for cardTypesString in ['Modifier', 'Creature/Spell' ] :
        cardType_names_widget = create_cardType_names_dropdown(cardTypesString)        
        #print(f"Adding {cardTypesString} widget")
        cardTypes_names_widget[cardTypesString] = cardType_names_widget
        cardType_names_widget.observe(update_decks_display, 'value')
        cardType_names_widget.observe(update_filter_widget, names='value')
        
        # Create a label for the widget with the same layout
        label = widgets.Label(value=f'{cardTypesString} Names:', layout=cardType_names_widget.layout)

        # Add the label to the label_items list and the widget to the widget_items list
        label_items.append(label)
        widget_items.append(cardType_names_widget)

    # Combine the label_items and widget_items lists
    grid_items = label_items + widget_items

    # Create HBoxes for the labels and widgets
    label_box = widgets.HBox(label_items)
    widget_box = widgets.HBox(widget_items)
    
    # Create a caption for the grid with bold text
    caption = widgets.HTML(value='<b>Filter:</b>')

    # Create a VBox to arrange the caption, labels, and widgets vertically
    grid = widgets.VBox([caption, label_box, widget_box])
    return grid

############################
# Setup and Initialization #
############################

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

    # Text widget to enter the username
    username = widgets.Text(value=GlobalVariables.username, description='Username:', disabled=False)
    username.observe(lambda change: handle_username_change(change), 'value')

    # Database selection widget
    db_list = create_database_selection_widget()
    #db_list_box = widgets.VBox([db_list])

    # Filter widget
    grid_filter = create_filter_widgets()
 
    # Button to load decks / fusions / forgborns 
    button_load = widgets.Button(description="Load" )
    button_load.on_click(lambda button: reload_data_on_click(button, loadToggle.value))
    
    # Create a list of HBoxes of factionToggles, Labels, and dropdowns
    toggle_dropdown_pairs = [widgets.HBox([factionToggles[i], dropdowns[i]]) for i in range(len(factionToggles))]

    # Create a Checkbox widget to toggle debugging
    debug_toggle = widgets.Checkbox(value=False, description='Debugging', disabled=False)    
    debug_toggle.observe(handle_debug_toggle, 'value')

    # Toggle Box 
    toggle_box = widgets.VBox([loadToggle,  button_load, username, db_list, grid_filter, debug_toggle])    

    if GlobalVariables.username != 'user': update_decks_display({'new': GlobalVariables.username})

    # Display the widgets    
    display(toggle_box)            
    display(out, out_df) 
    display(*toggle_dropdown_pairs, button_graph)



