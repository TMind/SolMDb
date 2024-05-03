import os, time, re
import ipywidgets as widgets
from pyvis.network import Network
import networkx as nx
import numpy as np

import GlobalVariables
from CardLibrary import Deck, FusionData, Fusion
from UniversalLibrary import UniversalLibrary
from DeckLibrary import DeckLibrary
from MongoDB.DatabaseManager import DatabaseManager
from MyGraph import MyGraph
from NetApi import NetApi

from soldb import parse_arguments
from IPython.display import display

from Synergy import SynergyTemplate
import pandas as pd
import qgrid

from icecream import ic
ic.disable()

# Enable qgrid to automatically display all DataFrame and Series instances
qgrid.enable(dataframe=True, series=True)
qgrid.set_grid_option('forceFitColumns', False)


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
button_load = None
db_list = None 
cardTypes_names_widget = {}

qgrid_deck_data  = None
qgrid_count_data = None
qgrid_syn_data   = None

qgrid_widget_options = {}
global_df = None

out = widgets.Output()
out_df = widgets.Output()

# Widget original options for qgrid
qg_syn_options = {
    'col_options' :   { 'defaultColumnWidth' : 700}, 
    'col_defs' : {                
        'tag':              { 'width': 175, },
        'name':            { 'width': 50,  },
    },
    'grid_options' : { 'forceFitColumns': False, }        
}


qg_deck_options = {
    'col_options' :           { 'width': 50, } ,
    'col_defs' : {        
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
}

qg_count_options = {    
    'col_options' :   { },
    'col_defs' : {                
      #  'name': {'width': 250},
        'faction': {'width': 75},
        'count': {'width': 50},
    }    
}

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

def generate_cardType_count_dataframe(existing_df=None):
    # Get the cardTypes from the stats array in the database
    deck_cursor = myDB.find('Deck', {})        
    df_decks = pd.DataFrame(list(deck_cursor)) 

    # Initialize a list to accumulate the DataFrames for each deck
    all_decks_list = []

    for deck in myDB.find('Deck', {}):
        if 'stats' in deck:
            stats = deck.get('stats', {})
            card_types = stats.get('card_types', {})                        
            cardType_df = pd.DataFrame(card_types['Creature'], index=[deck['name']])
            
            # Add 'faction' column to cardType_df
            cardType_df['faction'] = deck.get('faction', 'None')  # Replace 'Unknown' with a default value if 'faction' is not in deck

            # Append cardType_df to all_decks_list
            all_decks_list.append(cardType_df)

    # Concatenate all the DataFrames in all_decks_list, keeping the original index    
    if all_decks_list : 
        all_decks_df = pd.concat(all_decks_list)
    else:
        print("No decks found in the database")
        all_decks_df = pd.DataFrame()

    # Filter all_decks_df to only include rows that exist in existing_df
    if existing_df is not None:
        all_decks_df = all_decks_df[all_decks_df.index.isin(existing_df.index)]        

    #all_decks_df.reset_index(inplace=True)            

    # Separate the 'faction' column from the rest of the DataFrame
    if 'faction' in all_decks_df.columns:
        faction_df = all_decks_df['faction']
        #all_decks_df = all_decks_df.drop(columns=['faction'])
    else:
        faction_df = pd.Series()

    # Select only the numeric columns
    numeric_df = all_decks_df.select_dtypes(include='number')

    # Replace NaN values with 0 and convert to integer for only numeric columns
    numeric_df = numeric_df.fillna(0).astype(int)

    # Drop columns where all values in specific rows are 0 or less
    numeric_df = numeric_df.loc[:, ~(numeric_df <= 0).all(axis=0)]

    # Reorder the columns by their total, highest first
    numeric_df = numeric_df.reindex(numeric_df.sum().sort_values(ascending=False).index, axis=1)

    # Convert the DataFrame to strings, replacing '0' with ''
    numeric_df = numeric_df.astype(str).replace('0', '')

    # Make the index a row in the DataFrame with the name 'name'
    # numeric_df.insert(0, 'name',numeric_df.index)

    # Reset the index and create a new column with the old index
    # numeric_df.reset_index(inplace=True)

    # Rename the new column to 'name'
    # numeric_df.rename(columns={'index': 'name'}, inplace=True)

    # Insert the 'faction' column to the second position
    numeric_df.insert(1, 'faction', faction_df)

    #display(numeric_df)
    return numeric_df
    
    #return all_decks_df

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

    # For column 'cardSetNo' replace the number 99 with 0 
    df_decks_filtered['cardSetNo'] = df_decks_filtered['cardSetNo'].replace(99, 0)

    # Add additional columns to the DataFrame -> Count
    additional_columns_count = ['Creatures', 'Spells']
    for column in additional_columns_count:
        df_decks_filtered.loc[:,column] = 0

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

            # Create a DataFrame with the 'Creatures' and 'Spells' columns
            creature_count = stats['card_types']['Creature']['count']
            spell_count = stats['card_types']['Spell']['count']
            card_type_count_dict = {'Creatures': creature_count, 'Spells': spell_count}
            card_type_count_df = pd.DataFrame([card_type_count_dict], columns=card_type_count_dict.keys())

            # Flatten the 'creature_averages' sub-dictionaries into a single-row DataFrame
            attack_dict = stats['creature_averages']['attack']
            attack_df = pd.DataFrame([attack_dict], columns=attack_dict.keys())
            attack_df.columns = ['A1', 'A2', 'A3']

            defense_dict = stats['creature_averages']['health']
            defense_df = pd.DataFrame([defense_dict], columns=defense_dict.keys())
            defense_df.columns = ['H1', 'H2', 'H3']

            # Combine the new DataFrame with the attack and defense DataFrames
            deck_stats_df = pd.concat([card_type_count_df, attack_df, defense_df], axis=1)

            # Round each value in the DataFrame
            deck_stats_df = deck_stats_df.round(2)

            # Set the 'name' index for deck_stats_df
            deck_stats_df['name'] = deck['name']

            # Print out the columns of df_decks_filtered for debugging
            ic(df_decks_filtered.columns)

            # Set the common column as the index in both dataframes            
            deck_stats_df.set_index('name', inplace=True)

            # Update the corresponding row in df_decks_filtered with the stats from deck_stats_df
            df_decks_filtered.update(deck_stats_df)

    return df_decks_filtered


def apply_cardname_filter_to_deck_dataframe(df_decks):
    global cardTypes_names_widget
    
    def check_substring_in_titles(titles, substring):
        if titles:
            for title in titles:
                if title:                    
                    if substring in title:
                        return True
                else:
                    print(f"Title is empty")
        else:
            print(f"Titles is empty")
        return False
        
    def filter_by_substring(df, substring): 
        if substring == '':      
            return df
        else:
            theDF = df['cardTitles'] 
            myDF = theDF.apply(check_substring_in_titles, substring=substring)
            ret_df = df[myDF]
        return ret_df

    df_filtered = df_decks
    for dropdown in cardTypes_names_widget.values():   
        if not df_filtered.empty:         
            df_filtered = filter_by_substring(df_filtered, dropdown.value)   
        else:
            print("Dataframe is empty")            

    return df_filtered


##################
# Event Handling #
##################

def on_filter_changed(widget):
    update_visible_rows(widget)
    update_visible_columns(widget)

def update_visible_rows(widget):
    global global_df
    # Get the common index across all widgets
    source_widget = qgrid_deck_data
    target_widget = qgrid_count_data

    # Update the widget's DataFrame     
    df = global_df[id(target_widget)] if global_df else pd.DataFrame()
    target_widget.df = get_dataframe_apply_index_filter(source = source_widget.get_changed_df(), target = df)  
    
def get_dataframe_apply_index_filter(source, target):
    # Initialize a list to store the filtered rows
    filtered_rows = []

    # Iterate over the indices of the source DataFrame
    for idx in source.index:
        # Check if the index exists in the target DataFrame
        if idx in target.index:
            # Filter the target DataFrame for each index and add the result to the list
            filtered_rows.append(target.loc[[idx]])

    # Concatenate all the filtered rows into a DataFrame
    filtered_df = pd.concat(filtered_rows) if filtered_rows else pd.DataFrame()

    return filtered_df

# Function to check if any value in the column is not an empty string with regards to the changed_df of the qgrid widget
def check_column_values(column, changed_df):
    # Check if the column exists in the DataFrame
    if column in changed_df.columns:
        # Check if any value in the column is not an empty string
        result = changed_df[column].ne('').any()
        # Print all rows that contain values other than empty strings in the column
        #if result:
            #print(changed_df[changed_df[column].ne('')])
        return result
    else:
        print(f"Column '{column}' does not exist in the DataFrame.")
        return False
# Goal of this function :
# 1. Update the column definitions of the qgrid widget to set the width of each column to 0 if all values in the column are empty strings
#    Where to get the original column definitions from? global_df[id(qgrid_widget)]
#    Where to get the current column definitions from? qgrid_widget.column_definitions

def update_visible_columns(qgrid_widget):
    global global_df
    # Ensure original DataFrame is retained without alterations
    original_df = global_df[id(qgrid_widget)].copy() if id(qgrid_widget) in global_df else pd.DataFrame()

    print("Setting column visibility for")
    print(original_df.columns)

    # Access the current and original column definitions
    qg_column_defs = qgrid_widget.column_definitions.copy()
    original_column_definitions = qgrid_widget_options.get(id(qgrid_widget), {}).get('col_defs', {}).copy()

    print("Original Column Definitions:", original_column_definitions)
    print("Current Column Definitions:", qg_column_defs)

    # Lists to store the columns with 0 width and non-0 width
    zero_width_columns = []
    non_zero_width_columns = []

    # Analyze changed DataFrame for updates
    changed_df = qgrid_widget.get_changed_df()
    print(f"Columns : {changed_df.columns}")
    for column in changed_df.columns:  # Iterate over a copy of the keys
        # Check if column values are not just empty strings
        if check_column_values(column, changed_df):
            # Restore original column width if possible
            if column in original_column_definitions:
                qg_column_defs[column].update(original_column_definitions[column])
            else:
                if column in qg_column_defs:
                    print(f"Original settings for {column} not found, removing from current settings.")
                    del qg_column_defs[column]  # Remove the column from the current definitions
            non_zero_width_columns.append(column)
        else:
            # Set column width to 0 if all values are empty
            zero_width_columns.append(column)
            qg_column_defs[column] = {'width': 0, 'minWidth': 0, 'maxWidth': 0}

    # Assign the updated definitions back to the widget (if necessary)
    qgrid_widget.column_definitions = qg_column_defs

    # Print summary of adjustments
    print("Columns with 0 width:", zero_width_columns)
    print("Columns with non-0 width:", non_zero_width_columns)
    print("Finished setting column visibility")
    
    # Optionally, refresh the widget display if significant changes were made
    changed_df.reset_index(inplace=True)
    qgrid_widget.column_definitions['index'] = {'width' : 250 }
    qgrid_widget.df = changed_df
    #display(changed_df)

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
    global db_list, username
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
    handle_username_change({'new': GlobalVariables.username, 'owner': username})

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
    ic(update_decks_display, change)
    global username, qgrid_deck_data, qgrid_count_data, qgrid_syn_data, global_df

    if global_df is None:
        global_df = {}
        global_df[id(qgrid_deck_data)] = generate_deck_statistics_dataframe()

    if change['new'] or change['new'] == '':                       

        if change['owner'] == username:
        
            # Generate new DataFrame with new database             
            global_df[id(qgrid_deck_data)] = generate_deck_statistics_dataframe()
            global_df[id(qgrid_count_data)] = generate_cardType_count_dataframe(global_df[id(qgrid_deck_data)])
            global_df[id(qgrid_syn_data)] = generate_synergy_statistics_dataframe(global_df[id(qgrid_deck_data)])

            # Assign the new DataFrame to the qgrid widgets
            if qgrid_deck_data:
                qgrid_deck_data.df = global_df[id(qgrid_deck_data)]

            if qgrid_count_data:
                qgrid_count_data.df = global_df[id(qgrid_count_data)]

            #if qgrid_syn_data:
            #    qgrid_syn_data.df = global_df[id(qgrid_syn_data)]

        global_deck_df = global_df[id(qgrid_deck_data)]
        global_count_df = global_df[id(qgrid_count_data)]
        global_syn_df = global_df[id(qgrid_syn_data)]


        # Apply Filter to the DataFrame                
        deck_df_filtered = apply_cardname_filter_to_deck_dataframe(global_deck_df)

        if qgrid_deck_data:
            qgrid_deck_data.df = deck_df_filtered

        if qgrid_count_data:                  
            on_filter_changed(qgrid_count_data)            
            ic(qgrid_count_data.df)

        #if qgrid_syn_data:
        #    qgrid_syn_data.df =  generate_synergy_statistics_dataframe(deck_df_filtered)

        

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

def create_qgrid_view_options(qg_options):
    global qgrid_widget_options
    qg = qgrid.show_grid(pd.DataFrame(), 
                        column_options=qg_options['col_options'],
                        column_definitions=qg_options['col_defs'],
                        grid_options={'forceFitColumns': False},
                        show_toolbar=False)    
    # Store the options in the dictionary using the widget's ID as the key
    qgrid_widget_options[id(qg)] = qg_options
    return qg

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
    global db_list, username, button_load, card_title_widget, \
        qgrid_deck_data, qgrid_count_data, qgrid_syn_data,    \
        qg_deck_options, qg_count_options, qg_syn_options, out
    
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


    # Create qgrid widgets for the deck data, count data, and synergy data
    qgrid_deck_data = create_qgrid_view_options(qg_deck_options)
    qgrid_count_data = create_qgrid_view_options(qg_count_options)
    qgrid_syn_data  = create_qgrid_view_options(qg_syn_options)
    

    # Attach the event handler to each qgrid widget
    qgrid_deck_data.on('filter_changed', on_filter_changed)    
    
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

    # Display the widgets    
    display(toggle_box)  
    display(qgrid_deck_data, qgrid_count_data, qgrid_syn_data)          
    display(out)     
    display(*toggle_dropdown_pairs, button_graph)



