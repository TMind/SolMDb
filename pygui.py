import os, re
import ipywidgets as widgets
from pyvis.network import Network
import networkx as nx
import argparse

from GlobalVariables import global_vars as gv

# Ensure global_vars is initialized before using it
if gv is None:
    raise RuntimeError("global_vars was not initialized properly.")

from CardLibrary import Deck, FusionData, Fusion
from DeckLibrary import DeckLibrary
from MongoDB.DatabaseManager import DatabaseManager
from MyGraph import MyGraph
from NetApi import NetApi
from Synergy import SynergyTemplate

from IPython.display import display, HTML

import pandas as pd
from GridManager import GridManager, DynamicGridManager
from CustomGrids import TemplateGrid
from helptext import guide_text
from DisplayManager import get_count_display_widget, update_display_data, update_sheet_stats

from icecream import ic
ic.disable()

try:  
    # Try to set the option  
    pd.set_option('future.no_silent_downcasting', True)  
except KeyError:  
    # Handle the case where the option does not exist  
    print("Option 'future.no_silent_downcasting' is not neccessary in this version of pandas.")  

# Define Variables
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

synergy_template = SynergyTemplate()    

# Widget Variables
factionToggles = []
dropdowns = []
factionNames = ['Alloyin', 'Nekrium', 'Tempys', 'Uterra']
types = ['Decks', 'Fusions']
username_sff = os.getenv('SFF_USERNAME', 'sff')
username_jhub = os.getenv('JUPYTERHUB_USER', username_sff)
username_widget = widgets.Text(value=username_sff, description='Username:', disabled=False)

button_load = None
db_list = None 
cardTypes_names_widget = {}
deck_selection_widget = None

qgrid_widget_options = {}
data_generation_functions = {}

#central_frame_output = widgets.Output()
graph_output = widgets.Output()

net_api = None

# Manager Variables
grid_manager = None 
qm = GridManager(gv.out_debug)
tab = None 

# Widget original options for qgrid
qg_options ={ 'column_options' : {'defaultSortAsc': False}, 'column_definitions' : gv.all_column_definitions }   

######################
# Network Operations #
######################

from MagicEden import fetch_all_magiceden_listings

def fetch_network_decks(args, myApi):
    #print(f'Fetching Network Decks with args: {args}')
    
    if args.username == 'magiceden': 
        gv._myDB.set_database_name('magiceden')
        # Collect existing decknames from DB 
        deckCursor = gv._myDB.find('Deck', {}, {'name': 1})                
        deckNamesDatabase = [deck['name'] for deck in deckCursor]
        
        print(f'Fetching decks from Magic Eden') 
        args.type = 'deck'
        args.decklist = deckNamesDatabase
        # Fetch the listings from Magic Eden
        collection_symbol = 'sfgc'  # This could be dynamic based on args
        
        deck_data = fetch_all_magiceden_listings(collection_symbol, myApi, args)
        logging.info(f"{len(args.decklist)} remaining Listings : {args.decklist}")
        print(f"Total Magic Eden decks processed: {len(deck_data)}")                
        #gv.myDB.drop_database()
        # Remove old decks in args.decklist from the database 
        # for deck in args.decklist:
        #     if gv.myDB:
        #         logging.debug(f"Removing deck from DB: {deck}")
        #         gv.myDB.delete_one('Deck', {'name': deck})
        if args.decklist and gv._myDB:
            logging.info(f"Removing decks from DB: {args.decklist}")
            gv._myDB.delete_many('Deck', {'name': {'$in': args.decklist}})
        return deck_data     
    
    if args.id:
        urls = args.id.split('\n')
        pattern = r'\/([^\/]+)$'        
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

    myApi = NetApi()                   
    types = args.type.split(',')
    for type in types:
        if args.username == 'magiceden' and type == 'fuseddeck':
            args.mode = 'update'
            print(f"Skipping 'fuseddeck' for Magic Eden.")
            continue
        args.type = type
        net_results = fetch_network_decks(args, myApi)            
        
        if args.type == 'deck':     net_decks = net_results
        elif args.type == 'fuseddeck': net_fusions = net_results
        
    return DeckLibrary(net_decks, net_fusions, args.mode)

try:
    import qgridnext as qgrid
except ImportError:
    import qgrid
    
# Function to update the central data frame tab    
def update_central_frame_tab(central_df):
    #global central_frame_output
    # Update the content of the central_frame_tab
    gv.central_frame_output.clear_output()  # Clear existing content
    with gv.central_frame_output:
        grid = qgrid.show_grid(central_df, grid_options={'forceFitColumns': False}, column_definitions=gv.all_column_definitions)  # Create a qgrid grid from the DataFrame
        grid.add_class(gv.rotate_suffix)
        display(grid)  # Display the qgrid grid
    
    #print("Central DataFrame tab updated.")

##################
# Event Handling #
##################

# Function to handle changes to the debug toggle buttons
import logging
def handle_debug_toggle(change):
    """
    Handle changes in a ToggleButtons widget to set the logger level.

    Args:
        change (dict): A dictionary containing information about the change.
                       Keys typically include 'owner', 'new', 'old', and 'type'.
    """
    new_value = change['new']  # Get the new value of the ToggleButtons widget

    # Map button values to logging levels
    logging_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    # Set the logger level based on the selected value
    if new_value in logging_levels:
        logging.getLogger().setLevel(logging_levels[new_value])
        print(f"Logger level set to {new_value}")
    else:
        print(f"Unknown logger level: {new_value}")

def handle_db_list_change(event):
    """
    Handles changes in the database selection from the dropdown list.
    """
    global username_widget, grid_manager

    if gv.out_debug:
        with gv.out_debug:
            print(f'DB List Change: {event}')

    # Check if the selected database has changed
    if event['name'] == 'value' and event['old'] != event['new']:
        new_username = event['new']  # The new database selection

        if new_username:
            # Update the Global Username Variable
            gv.username = new_username

            # Update Username Widget
            username_widget.value = new_username  # Reflect change in username widget

            if grid_manager:
                # Set a flag indicating grids need to be refreshed
                grid_manager.set_refresh_needed(True)
                update_display_data(update_collection=True, update_dataframe=True)
                print("Grid Manager marked for refresh.")

        else:
            print('No valid database selected.')

operation_in_progress = False  # Add this global variable to track the in-progress state

def reload_data_on_click(button, event):
    global db_list, username_widget, operation_in_progress, grid_manager

    print(f'Reload Event: {event}')

    # Prevent multiple concurrent operations
    if operation_in_progress:
        print('Operation is already in progress. Please wait.')
        return

    # Set the flag to indicate that the operation is ongoing
    operation_in_progress = True
    value = event.get('new', 'unknown')
 
    try:
        username_value = username_widget.value if username_widget else gv.username
        if not username_value:
            print('Username cannot be empty.')
            return

        gv.username = username_value

        if not db_list:
            print('No database list found.')
            return

        # Set button to disabled, if button object exists
        if button:
            button.disabled = True

        if event.get('name') == 'value': 

            # Handle the different values
            if value == 'Load Decks/Fusions':
                arguments = ['--username', username_value,
                            '--mode', 'create',
                            '--type', 'deck,fuseddeck']
                args = parse_arguments(arguments)
            elif value == 'Update Decks/Fusions':
                arguments = ['--username', username_value,
                            '--mode', 'update',
                            '--type', 'deck,fuseddeck']
                args = parse_arguments(arguments)
            elif value == 'Create all Fusions':
                arguments = ['--username', username_value,
                            '--mode', 'fuse']
                args = parse_arguments(arguments)
            # elif value == 'Generate Dataframe':
            #     #generate_central_dataframe(force_new=True)
            #     #manage_central_dataframe(force_new=True)
            #     if grid_manager:
            #         grid_manager.handle_database_change(event)
            #     return
            elif value == 'Update CM Sheet':
                # Update the local CSV using CMManager
                if gv.commonDB:
                    gv.commonDB.drop_database()
                if gv.cm_manager:
                    gv.cm_manager.update_local_csv('Card Database')
                gv.reset_universal_library()
                # Update and display sheet statistics
                update_sheet_stats()
                return
            # elif value == 'Find Combos':
            #     combo_df = generate_combo_dataframe()
            #     return combo_df
            # elif value == 'Refresh Grid':
            #     if grid_manager:
            #         grid_manager.refresh_gridbox()
            #     return

        # Execute main task if other tasks are not returning early
        print(f'Executing task: {value} -> {args}')
        load_deck_data(args)
        # Update the Timestamp in the metadata of the database
        update_db_timestamp(username_value)
        
        # Refresh db_list widget
        db_names = []
        if not gv._myDB:
            gv.set_myDB()
        db_names = gv._myDB.mdb.client.list_database_names()
        valid_db_names = [db for db in db_names if db not in ['local', 'admin', 'common', 'config']]

        if valid_db_names:
            db_list.options = [''] + valid_db_names
            if username_value in valid_db_names:
                update_display_data(update_collection=True, update_dataframe=False)
                db_list.value = username_value
            else:
                db_list.value = valid_db_names[0]
        else:
            db_list.options = ['']
            db_list.value = ''  # Set to an empty string if no valid databases
    finally:
        # Ensure we reset the progress flag and button state
        if grid_manager: grid_manager.set_refresh_needed(True)
        operation_in_progress = False
        if button:
            button.disabled = False

def parse_arguments(arguments = None):
    # Create an argument parser
    parser = argparse.ArgumentParser(description="Script description")

    # Add command-line arguments
    # Arguments for online use 
    parser.add_argument("--username", default="", help="Online account name or omit for offline use")
    parser.add_argument("--type", default="deck", choices=["deck", "fuseddeck", "deck,fuseddeck"], help="Decktype for user collection , default=deck")
    parser.add_argument("--id", default="", help="Specific Deck ID from solforgefusion website")
    
    # Arguments for general use 
    # If both username and file is given, export deckbase to file.json 
    # If only file is given import deckbase from file.json 
    parser.add_argument("--filename",  default=None,  help="Offline Deck Database Name")
    parser.add_argument("--synergies", default=None, help="CSV Filename for synergy lookup")    
    parser.add_argument("--offline", default=None, help="Offline use only")    
    parser.add_argument("--mode", default='insert', help="Mode: insert, update, refresh, create")    

    # Arguments for Evaluation
    
    parser.add_argument("--eval", nargs='?', const=True, action="store",  help="Evaluate possible fusions. Optional filename for .csv export")    
    parser.add_argument("--graph", action="store_true",  help="Create Graph '.gefx'")
    parser.add_argument("--filter", default=None, help="Filter by card names. Syntax: \"<cardname>+'<card name>'-<cardname>\" + = AND, - = OR ")
    parser.add_argument("--select_pairs", action="store_true", help="Select top pairs")
    
    # Parse the command-line arguments
    args = parser.parse_args(arguments)

    return args

def display_graph_on_click(button):
    myDecks = []
    for dropdown in dropdowns:
        myDecks.append(Deck.lookup(dropdown.value))
    
    myDeckA = myDecks[0]
    myDeckB = myDecks[1]

    if myDeckA and myDeckB:
        fusionName = f'{myDeckA.name}_{myDeckB.name}'
        fusionCursor = None
        if gv._myDB:
            fusionCursor = gv._myDB.find('Fusion', {'name' : fusionName})
        if fusionCursor: 
            for fusion in fusionCursor:
                myFusion = Fusion.from_data(fusion)
                show_deck_graph(myFusion, out_main)
        else:
            # Create a new fusion based on the decknames
            newFusionData = FusionData(name=fusionName, myDecks=[myDeckA, myDeckB],tags=['forged'] )
            newFusion = Fusion(newFusionData)
            show_deck_graph(newFusion, out_main)
                
    else: 
        for deck in [myDeckA , myDeckB] :
            print(deck)
            if deck:
                myGraph = MyGraph()
                myGraph.create_graph_children(deck)
                net = visualize_network_graph(myGraph.G)
                display(net.show(f'{deck.name}.html'))

import webbrowser
def display_graph():
    global selected_items_label
    
    selected_items_string = selected_items_label.value.split(':')
    selected_items = selected_items_string[1].split(',')
    
     # Clear previous graph output
    graph_output.clear_output()

    # Ensure the 'html' subfolder exists
    os.makedirs('html', exist_ok=True)
    
    with graph_output:
        name = ''
        graph = {}
        for item in selected_items:            
            for item_type in ['Deck', 'Fusion']:
                print(f"Searching {item_type} with name: {item.strip()}")
                item_cursor = gv._myDB.find_one(item_type, {'name': item.strip()})
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
                net = Network(notebook=True, directed=True, height='1500px', width='2000px', cdn_resources='in_line')    
                net.from_nx(graph)
                net.force_atlas_2based()
                net.show_buttons(True)
                                        
                filename = f'html/{name}.html'
                net.show(filename)
                
                # Read HTML file content and display using IPython HTML
                filepath = os.path.join(os.getcwd(), filename)
                if os.path.exists(filepath):
                    webbrowser.open(f'file://{filepath}')
                    display(HTML(filename))
                else:
                    print(f"File {filename} not found.")
            else:
                print(f"No graph found for item: {item}")


def refresh_faction_deck_options(faction_toggle, dropdown):    
    #global_vars.myDB.set_database_name(global_vars.username)   
    deckCursor = []
    if gv._myDB: 
        deckCursor = gv._myDB.find('Deck', { 'faction' : faction_toggle.value })
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
        graph.nodes[node]['label'] += f'[{num_parents}]'
        
    net = Network(notebook=True, directed=True, height='1500px', width='2000px', cdn_resources='in_line')    
    net.from_nx(graph)
    net.force_atlas_2based()
    net.show_buttons()
    #print('Displaying Graph!')
    #display(net.show('graph.html'))
    return net

def show_deck_graph(deck, out):
    myGraph = MyGraph()
    myGraph.create_graph_children(deck)
    net = visualize_network_graph(myGraph.G)
    with out:
        out.clear_output() 
        display(net.show(f'{deck.name}.html'))

#############################
# User Interface Management #
#############################

def create_debug_widget():
    debug_toggle = widgets.ToggleButtons(
        value='CRITICAL',
        options=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        description='Debug',
        disabled=False,
        button_style='info', # 'success', 'info', 'warning', 'danger' or ''
        tooltip='Set level of logging messages',
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

def initialize_widgets() :
    factionToggle = create_faction_selection_toggle(factionNames)
    dropdown = widgets.Dropdown()
    #refresh_faction_deck_options(factionToggle, dropdown)
    factionToggle.observe(lambda change: refresh_faction_deck_options(factionToggle, dropdown), 'value')
    return factionToggle, dropdown

def create_database_selection_widget():
    global username_widget
    DB = DatabaseManager('common')
    db_names = DB.mdb.client.list_database_names()
    db_names = [db for db in db_names if db not in ['local', 'admin', 'common', 'config']]
    db_list = widgets.RadioButtons(
        options= [''] + db_names ,
        description='Databases:',
        disabled=False
    )
    # Set the username to the value of the selected database
    
    #global_vars.username = db_list.value or 'user'
    #global_vars.myDB.set_database_name(global_vars.username)
    # Also set the value of the username widget
    if username_widget:
        username_widget.value = os.getenv('SFF_USERNAME', 'sff')

    def on_db_list_change(change):    
        if username_widget:
            username_widget.value = change['new']

    db_list.observe(on_db_list_change, 'value')

    return db_list

def update_db_timestamp(username):
    """
    Updates the timestamp of the DataFrame in the MongoDB metadata.
    """
    if gv._myDB:
        # Retrieve the file record from GridFS
        file_record = gv._myDB.find_one('fs.files', {'filename': f'central_df_{username}'})
        
        if file_record:
            # Prepare the update data
            update_data = {'metadata.Collection_Timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            # Perform the update
            result = gv._myDB.update_one(
                'fs.files',  # Collection name
                {'_id': file_record['_id']},  # Query by unique file ID
                update_data  # Update data
            )
            
            if result.modified_count > 0:
                logging.info(f"Successfully updated DataFrame timestamp for username: {username}")
            else:
                logging.warning(f"Timestamp update failed or was unnecessary for username: {username}")
        else:
            logging.warning(f"No file record found in GridFS for username: {username}")
    else:
        logging.error("MongoDB connection is not initialized.")

# Function to update the options in loadSelected
def update_selectable_options(widget):
    global display_data
    """
    Update the available options in the loadSelected widget based on the rules.
    """
    options = ['Update CM Sheet']  # Start with no options

    try:

        # Extract data for clarity
        cm_sheet_exists = bool(gv.display_data['CM Sheet']['Timestamp'])
        collection_decks = gv.display_data['Collection']['Decks']

        # Rule 1: CM Sheet must be updated if not existent
        if cm_sheet_exists:

            # Rule 2: Load Decks if no decks in the database
            if collection_decks == 0:
                options.append('Load Decks/Fusions')
                
            # Rule 2 continued: Update Decks if decks exist in the database
            if collection_decks > 0:
                options.append('Update Decks/Fusions')
                
    except KeyError as e:
        logging.error(f"Key doesn't exist: {e}")

    finally:
        # Update the options in the Select widget
        widget.options = options

            
# Function to create a styled HTML widget with a background color
def create_styled_html(text, text_color, bg_color, border_color):
    html = widgets.HTML(
        value=f"<div style='padding:10px; color:{text_color}; background-color:{bg_color};"
            f" border:solid 2px {border_color}; border-radius:5px;'>"
            f"<strong>{text}</strong></div>"
    )
    return html            
            
############################
# Setup and Initialization #
############################
import markdown as md
from CustomGrids import TemplateGrid
action_toolbar = None
selected_db_label = widgets.Label(value='Selected Database: None')
selected_items_label = widgets.Label(value='Selected Items: None')
text_box = widgets.Text(  
    value='',  
    placeholder='Enter data here',  
    description='Data:',  
    disabled=False  
)  

def setup_restricted_interface():
    global db_list, button_load, card_title_widget, grid_manager, tab, net_api
    global action_toolbar, selected_db_label, selected_items_label, text_box, graph_output, username_jhub


    for i in range(2):            
        factionToggle, dropdown = initialize_widgets()
        factionToggles.append(factionToggle)
        dropdowns.append(dropdown)

    # Button to create network graph
    button_graph = widgets.Button(description='Show Graph')
    button_graph.on_click(lambda button: display_graph()) #display_graph_on_click(button))

    # Toggle buttons to select load items
    loadToggle = widgets.ToggleButtons(
        options=['Load Decks/Fusions', 'Update CM Sheet'],
        description='Action:',
        disabled=False,
        button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
        tooltips=['Load Decks and Fusions from the website', 'Get the latest version from Collection Manager'])

    # Button to load decks / fusions / forgborns 
    button_load = widgets.Button(description='Execute', button_style='info', tooltip='Execute the selected action')
    button_load.on_click(lambda button: reload_data_on_click(button, {
        'name': 'value',
        'new': loadToggle.value,
        'source': loadToggle
    }))
    
    

    # Database selection widget
    db_list = create_database_selection_widget()
    db_list.observe(handle_db_list_change, names='value')
    
    # Create a Checkbox widget to toggle debugging
    debug_toggle = widgets.Checkbox(value=False, description='Debugging', disabled=False)    
    debug_toggle.observe(handle_debug_toggle, 'value')
    
    # Create an instance of the manager
    grid_manager = DynamicGridManager(qg_options, gv.out_debug)

    # Update the filter grid on db change
    db_list.observe(grid_manager.filterGridObject.update_selection_content, names='value')
    db_list.observe(lambda: update_selectable_options(loadToggle))

    # Create styled HTML widgets with background colors
    db_helper = create_styled_html(
        "Database Tab: This tab allows you to load and manage a database for a username on Solforge Fusion.",
        text_color='white', bg_color='blue', border_color='blue'
    )

    # Convert Markdown to HTML using the markdown module
    guide_html_content = md.markdown(guide_text['db'])
    # Create an HTML widget to display the converted Markdown
    guide_html = widgets.HTML(value=guide_html_content)
    # Create an Accordion widget with the guidance text
    db_accordion = widgets.Accordion(children=[guide_html], selected_index=None)
    db_accordion.set_title(0, 'Guide: How to Create and Manage your Database')

    deck_helper = create_styled_html(
        "Decks Tab: Manage and view decks in this section.",
        text_color='white', bg_color='#3D2B56', border_color='#4A3E6D'  # Slightly lighter purple to match the background
    )

    deck_filter_bar = create_styled_html(
        "Filter Selection: Set custom filters to your deck base.",
        text_color='white', bg_color='#2E86AB', border_color='#205E86'  # Darker blue for contrast
    )

    # Convert Markdown to HTML using the markdown module
    guide_html_content = md.markdown(guide_text['deck'])
    # Create an HTML widget to display the converted Markdown
    guide_html = widgets.HTML(value=guide_html_content)
    # Create an Accordion widget with the guidance text
    deck_accordion = widgets.Accordion(children=[guide_html], selected_index=None)
    deck_accordion.set_title(0, 'Guide: How to filter Decks and Fusions')
    
    central_frame_helper = create_styled_html(
        "Central Dataframe Tab: View and manage the central dataframe.",
        text_color='white', bg_color='teal', border_color='teal'
    )
    
    progressbar_header = create_styled_html(
        "Progress Bars Section",
        text_color='white', bg_color='#2E86AB', border_color='#205E86'  # Darker blue for contrast
    )
              
    # Updated Tab content with styled text boxes
    db_tab = widgets.VBox([db_helper, db_accordion, loadToggle, button_load, count_display, username_widget, db_list])
    deck_tab = widgets.VBox([deck_helper, deck_accordion, *grid_manager.get_ui()])    
    central_frame_tab = widgets.VBox([central_frame_helper, gv.central_frame_output])

    # Create the Tab widget with children
    tab = widgets.Tab(children=[db_tab, deck_tab, central_frame_tab])
    tab.set_title(0, 'Database')
    tab.set_title(1, 'Decks')
    tab.set_title(2, 'CentralDataframe')

    # Set the default selected tab
    tab.selected_index = 1


    # Layout: Progress bars at the top, then the tab widget below
    layout = widgets.VBox([progressbar_header,gv.progress_manager.progressbar_container,tab])
    display(layout)

    update_sheet_stats()
    
    if db_list and 'magiceden' in db_list.options:
        db_list.value = 'magiceden'
    else:
        username_widget.value = 'magiceden'
        reload_data_on_click(None, 'Load Decks/Fusions')
    
    username_widget.disabled = True 
    db_list.disabled = True 
    
saved_event = {'name': 'value', 'new': 'Load Decks/Fusions', 'source': None}
def setup_interface():
    global db_list, button_load, card_title_widget, grid_manager, tab, net_api
    global action_toolbar, selected_db_label, selected_items_label, text_box, graph_output, username_jhub

    if username_jhub == 'magiceden' : 
        return setup_restricted_interface()
             
    for i in range(2):            
        factionToggle, dropdown = initialize_widgets()
        factionToggles.append(factionToggle)
        dropdowns.append(dropdown)

    # Toggle buttons to select load items
    loadSelected = widgets.Select(        
        options=['Load Decks/Fusions', 'Update CM Sheet'],
        description='DB Action:',
        disabled=False,
        #button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
        tooltips=['Load Decks and Fusions from the website', 'Get the latest version from Collection Manager'])
    
    loadSelected.observe(lambda event: on_menu_selection_change(event), names='value')
    
    #'Generate Dataframe','Refresh Grid'
    # Button to load decks / fusions / forgborns 
    button_load = widgets.Button(description='Execute', button_style='info', tooltip='Execute the selected action')
    button_load.on_click(lambda button: reload_data_on_click(button, saved_event))

    # Database selection widget
    db_list = create_database_selection_widget()
    db_list.observe(handle_db_list_change, names='value')
    
    # Create a list of HBoxes of factionToggles, Labels, and dropdowns
    toggle_dropdown_pairs = [widgets.HBox([factionToggles[i], dropdowns[i]]) for i in range(len(factionToggles))]

    # Create a Checkbox widget to toggle debugging
    debug_toggle = create_debug_widget()
    debug_toggle.observe(handle_debug_toggle, 'value')
    
    # Create an instance of the manager
    grid_manager = DynamicGridManager(qg_options, gv.out_debug)

    def on_menu_selection_change(event):
        global saved_event
        saved_event = event

    # Attach observer to db_list
    #db_list.observe(on_db_selection_change, names='value')
    #db_list.observe(grid_manager.filterGridObject.update_selection_content, names='value')

    templateGrid = TemplateGrid()

    # Create styled HTML widgets with background colors
    db_helper = create_styled_html(
        "Database Tab: This tab allows you to load and manage a database for a username on Solforge Fusion.",
        text_color='white', bg_color='blue', border_color='blue'
    )

    # Convert Markdown to HTML using the markdown module
    guide_html_content = md.markdown(guide_text['db'])
    # Create an HTML widget to display the converted Markdown
    guide_html = widgets.HTML(value=guide_html_content)
    # Create an Accordion widget with the guidance text
    db_accordion = widgets.Accordion(children=[guide_html], selected_index=None)
    db_accordion.set_title(0, 'Guide: How to Create and Manage your Database')

    deck_helper = create_styled_html(
        "Decks Tab: Manage and view decks in this section.",
        text_color='white', bg_color='#3D2B56', border_color='#4A3E6D'  # Slightly lighter purple to match the background
    )

    # Convert Markdown to HTML using the markdown module
    guide_html_content = md.markdown(guide_text['deck'])
    # Create an HTML widget to display the converted Markdown
    guide_html = widgets.HTML(value=guide_html_content)
    # Create an Accordion widget with the guidance text
    deck_accordion = widgets.Accordion(children=[guide_html], selected_index=None)
    deck_accordion.set_title(0, 'Guide: How to filter Decks and Fusions')
    
    template_helper = create_styled_html(
        "Templates Tab: Manage templates in this section.",
        text_color='white', bg_color='purple', border_color='purple'
    )

    fusions_helper = create_styled_html(
        "Graphs Tab: Create and view graphs based on your data.",
        text_color='white', bg_color='orange', border_color='orange'
    )

    debug_helper = create_styled_html(
        "Debug Tab: Debug and monitor the system output here.",
        text_color='white', bg_color='red', border_color='red'
    )

    central_frame_helper = create_styled_html(
        "Central Dataframe Tab: View and manage the central dataframe.",
        text_color='white', bg_color='teal', border_color='teal'
    )
    
    progressbar_header = create_styled_html(
        "Progress Bars Section",
        text_color='white', bg_color='#2E86AB', border_color='#205E86'  # Darker blue for contrast
    )
        
    # Updated Tab content with styled text boxes
    db_tab = widgets.VBox([db_helper, db_accordion, get_count_display_widget(), username_widget, loadSelected, button_load, db_list])
    deck_tab = widgets.VBox([deck_helper, deck_accordion, *grid_manager.get_ui()])
    template_tab = widgets.VBox([template_helper, templateGrid.get_ui()])
    debug_tab = widgets.VBox([debug_helper, debug_toggle, gv.out_debug])
    central_frame_tab = widgets.VBox([central_frame_helper, gv.central_frame_output])

    # Create the Tab widget with children    
    def on_tab_change(event):
        logging.info(f"Tab changed to index: {event['new']}")
        if event['new'] == 1 and grid_manager and grid_manager.refresh_needed:
            grid_manager.handle_database_change(event)
    
    tab = widgets.Tab(children=[db_tab, deck_tab, template_tab, debug_tab, central_frame_tab])
    tab.set_title(0, 'Database')
    tab.set_title(1, 'Decks')
    tab.set_title(2, 'Templates')
    tab.set_title(3, 'Debug')
    tab.set_title(4, 'CentralDataframe')

    # Set the default selected tab
    tab.selected_index = 0
    tab.observe(on_tab_change, names='selected_index')
    
    # Create the labels that will be updated
    selected_db_label = widgets.Label(value="Selected Database: None")
    selected_items_label = widgets.Label(value="Selected Items: None")        

    # Layout: Progress bars at the top, then the tab widget below
    layout = widgets.VBox([progressbar_header,gv.progress_manager.progressbar_container, tab])
    display(layout)

    update_sheet_stats()
    


        
