from enum import unique
import os, time, re
import ipywidgets as widgets
from pyvis.network import Network
import networkx as nx
import numpy as np
#import qgrid

import GlobalVariables
from CardLibrary import Deck, FusionData, Fusion
from UniversalLibrary import UniversalLibrary
from DeckLibrary import DeckLibrary
from MongoDB.DatabaseManager import DatabaseManager
from MyGraph import MyGraph
from NetApi import NetApi

from soldb import parse_arguments
from IPython.display import display, HTML

from Synergy import SynergyTemplate
import pandas as pd
from GridManager import GridManager, FilterGrid, get_cardType_entity_names

from icecream import ic
ic.disable()


# Custom CSS style

custom_css = """
<style>
/* Customizes the scrollbar within qgrid */
.q-grid ::-webkit-scrollbar {
    width: 5px;  /* Smaller width for vertical scrollbar */
    height: 5px; /* Smaller height for horizontal scrollbar */
}

.q-grid ::-webkit-scrollbar-track {
    border-radius: 10px;
    background: rgba(0,0,0,0.1); /* Light background for the track */
}

.q-grid ::-webkit-scrollbar-thumb {
    border-radius: 10px;
    background: rgba(128,128,128,0.8); /* Lighter gray color for the thumb */
}

.q-grid ::-webkit-scrollbar-thumb:hover {
    background: rgba(90,90,90,0.8); /* Slightly darker gray on hover */
}
</style>
"""
display(HTML(custom_css))  


# Enable qgrid to automatically display all DataFrame and Series instances
#qgrid.enable(dataframe=True, series=True)
#qgrid.set_grid_option('forceFitColumns', False)


# Define Variables
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

GlobalVariables.myDB = DatabaseManager(GlobalVariables.username, uri=GlobalVariables.uri)
GlobalVariables.commonDB = DatabaseManager('common', uri=GlobalVariables.uri)

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
username = widgets.Text(value=GlobalVariables.username, description='Username:', disabled=False)
button_load = None
db_list = None 
cardTypes_names_widget = {}

qgrid_widget_options = {}
filter_grid = None 
global_df = None

out_main = widgets.Output()
out_qm = widgets.Output()
out_debug = widgets.Output()

qm = GridManager(out_qm)

# Widget original options for qgrid
qg_syn_options = {
    'col_options' :   { 'defaultColumnWidth' : 700}, 
    'col_defs' : {                
        'tag':              { 'width': 175, },
        'name':            { 'width': 50,  },
    },
    'grid_options' : { 'forceFitColumns': False, }        
}


qg_coll_options = {
    'col_options' :         { 'width': 50, } ,
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
    'col_options' :         { 'width': 85, } ,
    'col_defs' : {                
        'index': {'width': 250},
        'faction': {'width': 75},
        'count': {'width': 50},
    }    
}

qg_deck_options = {
    'col_options' :         { 'width': 100, } ,
    'col_defs' : {                   
        'DeckName':         { 'width': 250, }, 
        'name':             { 'width': 200, },     
        'rarity':           { 'width': 125,  },        
        'cardType':         { 'width': 90,  },
        'cardSubType':      { 'width': 110,  },
        'A1':               { 'width': 50,  },
        'A2':               { 'width': 50,  },
        'A3':               { 'width': 50,  },
        'H1':               { 'width': 50,  },
        'H2':               { 'width': 50,  },
        'H3':               { 'width': 50,  }
    }
}

######################
# Network Operations #
######################

def fetch_network_decks(args, myApi):
    print(f"Fetching Network Decks with args: {args}")
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

def generate_deck_content_dataframe(event, widget):
    ic(generate_deck_content_dataframe, event, widget)
    #print(f"Generating Deck Content DataFrame : {event}")
    with out_debug:
        print(f"DeckEvent: {event}, Widget: {widget}")

        #Get the selection from the deck widget
        desired_fields = ['name', 'cardType', 'cardSubType', 'levels']    
        if widget:            
            all_decks_df_list = []
            old_selection = set(event['old'])
            new_selection = set(event['new'])
            deselected_rows = old_selection - new_selection

            # Get the selected rows from the DataFrame based on the indices
            changed_df = widget.get_changed_df()
            selectList = changed_df.iloc[list(new_selection)].index        
            deselectList = changed_df.iloc[list(deselected_rows)].index
            old_df = qm.get_grid_df('deck')            
            # Ensure old_df is not None before proceeding
            if old_df is None:
                print("No previous data found in the deck grid.")
                unique_deckNames = []
            else:
                # Get the unique values from the deckName column in old_df
                unique_deckNames = old_df['DeckName'].unique().tolist()
        
            # Add the deckList to the unique_deckNames and remove the deselectList
            print(f"Select: {selectList} \nDeselect: {deselectList}\nUnique: {unique_deckNames}")
            union_set = set(unique_deckNames) | set(selectList)
            deckList =  list(union_set - set(deselectList))            
            #deckList = ['The Reeves of Loss', 'The People of Bearing']                
            card_dfs_list = []  # List to store DataFrames for each card
            for deckName in deckList:
                print(f'DeckName: {deckName}')
                #Get the Deck from the Database 
                deck = GlobalVariables.myDB.find_one('Deck', {'name': deckName})
                if deck:
                    #print(f'Found deck: {deck}')
                    #Get the cardIds from the Deck
                    cardIds = deck['cardIds']
                    deck_df_list = pd.DataFrame([deck])  # Create a single row DataFrame from deck                    
                    for cardId in cardIds:
                        card = GlobalVariables.myDB.find_one('Card', {'_id': cardId})
                        if card:
                            fullCard = card 
                            # Select only the desired fields from the card document
                            card = {field: card[field] for field in desired_fields if field in card}

                            # Add 'provides' and 'seeks' information
                            providers = re.split(', |,', fullCard.get('provides', ''))
                            seekers = re.split(', |,', fullCard.get('seeks', ''))

                            # Create a dictionary with keys as item and values as True
                            provides_dict = {item: ['provides'] for item in providers if item}
                            seeks_dict = {item: ['seeks'] for item in seekers if item}
                            
                            # Create a DataFrame from the dictionary
                            #single_card_data_row = pd.DataFrame(card_dict, index=card['name'])

                            # Flatten the 'levels' dictionary
                            if 'levels' in card and card['levels']:
                                levels = card.pop('levels')
                                for level, level_data in levels.items():
                                    card[f'A{level}'] = int(level_data['attack']) if 'attack' in level_data else ''
                                    card[f'H{level}'] = int(level_data['health']) if 'health' in level_data else ''

                            # Merge the dictionaries dictionaries
                            card_dict = {**card, **provides_dict, **seeks_dict}
                            
                            # Insert 'DeckName' at the beginning of the card dictionary
                            card = {'DeckName': deckName, **card_dict}

                            # Create a DataFrame from the remaining card fields      
                            card_df = pd.DataFrame([card])                                             
                            card_dfs_list.append(card_df)  # Add full_card_df to the list                            
                    
            # Concatenate the header DataFrame with the deck DataFrames
            final_df = pd.concat(card_dfs_list, ignore_index=True, axis=0)        

            # Replace empty values in the 'cardSubType' column with 'Spell'
            if 'cardSubType' in final_df.columns:
                final_df['cardSubType'] = final_df['cardSubType'].replace(['', '0', 0], 'Spell')
                final_df['cardSubType'] = final_df['cardSubType'].replace(['Exalt'], 'Spell Exalt')

            return final_df.fillna('')
        

def generate_cardType_count_dataframe(existing_df=None):
    # Initialize a list to accumulate the DataFrames for each deck
    all_decks_list = []

    # Get interface ids from the database 
    #interface_ids = GlobalVariables.commonDB.find('Interface', {})
    #interface_ids = [interface['_id'] for interface in interface_ids]
    #print(f"Interface IDs: {interface_ids}")
    
    # Get the cardTypes from the stats array in the database
    for deck in GlobalVariables.myDB.find('Deck', {}):

        deckName = deck['name']
        myDeck = Deck.load(deckName)
        myGraph = MyGraph()
        myGraph.create_graph_children(myDeck)

        interface_ids_df = pd.DataFrame(columns=['interface_ids'], index=[deckName])

        interface_ids = {}
        for interface_id in myGraph.node_data:
            #print(f"Tag: {interface_id}")
            #print(f"Node Data: {myGraph.node_data[interface_id]}")
            
            if 'input' in myGraph.node_data[interface_id]:
                interface_length = len(myGraph.node_data[interface_id]['input'])
            elif 'output' in myGraph.node_data[interface_id]:
                interface_length = len(myGraph.node_data[interface_id]['output'])

            interface_ids[interface_id] = interface_length

        # Add a new row to the interface_ids_df DataFrame with the index of deckName and the column of interface_id
        interface_ids_df = pd.DataFrame(interface_ids, index=[deckName])

        #display(interface_ids_df)
        if 'stats' in deck:
            stats = deck.get('stats', {})
            card_types = stats.get('card_types', {})                        
            cardType_df = pd.DataFrame(card_types['Creature'], index=[deckName])
            
            # Combine interface_ids_df and cardType_df
            #cardType_df = cardType_df.combine_first(interface_ids_df)

            # Sort the columns by their names
            #cardType_df = cardType_df.sort_index(axis=1)

            # Add 'faction' column to cardType_df
            cardType_df['faction'] = deck.get('faction', 'None')  # Replace 'Unknown' with a default value if 'faction' is not in deck

            # Append cardType_df to all_decks_list
            all_decks_list.append(cardType_df)

    # Concatenate all the DataFrames in all_decks_list, keeping the original index    
    if all_decks_list : 
        all_decks_df = pd.concat(all_decks_list)
        all_decks_df.sort_index(axis=1, inplace=True)
    else:
        print("No decks found in the database")
        all_decks_df = pd.DataFrame()

    # Filter all_decks_df to only include rows that exist in existing_df
    if existing_df is not None:
        all_decks_df = all_decks_df[all_decks_df.index.isin(existing_df.index)]        

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

    # Insert the 'faction' column to the second position
    numeric_df.insert(0, 'faction', faction_df)

    #display(numeric_df)
    return numeric_df


# Data Handling and Transformation 
def generate_deck_statistics_dataframe():
    global cardTypes_names_widget

    def get_card_title(card_id):
        card = GlobalVariables.myDB.find_one('Card', {'_id': card_id})
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
        forgeborn = GlobalVariables.commonDB.find_one('Forgeborn', {'_id': forgeborn_id})
        return forgeborn['name'] if forgeborn else None

    def get_forgeborn_abilities(forgeborn_id):
        forgeborn = GlobalVariables.commonDB.find_one('Forgeborn', {'_id': forgeborn_id})
        return forgeborn['abilities'] if forgeborn else None

    def get_card_titles(card_ids):
        card_titles = []
        for card_id in card_ids:
            card_title = get_card_title(card_id)
            if card_title:  # Check if card_title is not empty
                card_titles.append(card_title)
        # Join the list of titles into a single string separated by commas
        return ', '.join(sorted(card_titles))

    # Get all Decks from the database
    try:
        deck_cursor = GlobalVariables.myDB.find('Deck', {})        
        df_decks = pd.DataFrame(list(deck_cursor))
        df_decks_filtered = df_decks[[ 'registeredDate', 'name', 'xp', 'elo', 'cardSetNo', 'faction', 'forgebornId']].copy()
        df_decks_filtered['cardTitles'] = df_decks['cardIds'].apply(get_card_titles)
    except:
        print("Error reading decks from the database. Try reloading the data.")
        return pd.DataFrame()

    # For column 'cardSetNo' replace the number 99 with 0 
    df_decks_filtered['cardSetNo'] = df_decks_filtered['cardSetNo'].replace(99, 0)
    df_decks_filtered['xp'] = df_decks_filtered['xp'].astype(int)
    df_decks_filtered['elo'] = df_decks_filtered['elo'].astype(float)

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
    for deck in GlobalVariables.myDB.find('Deck', {}):
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
    for deck in GlobalVariables.myDB.find('Deck', {}):
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

def apply_cardname_filter_to_dataframe(df_to_filter, filter_df):
    def filter_by_substring(df, filter_row):       
        def apply_filter(df, substrings):
            substring_check_results = []

            if not substrings:
                return df

            #print(f"Applying filter {substrings} to DataFrame")
            #display(df)
            # Iterate over the 'cardTitles' column            
            substring_check_results = [any(substring in title for substring in substrings) for title in df['cardTitles']]
            
            # Convert the list to a pandas Series
            substring_check_results = pd.Series(substring_check_results, index=df.index)

            # Assign the results to filtered_indices
            #filtered_indices = substring_check_results
            #true_indices = filtered_indices[filtered_indices].index
            #print(f"True indices for filter {substrings}: {list(true_indices)}")

            current_filter_results = df[substring_check_results].copy()

            return current_filter_results

        # Apply the first filter outside the loop
        df_filtered = df_to_filter
        substrings = re.split(r'\s*,\s*', filter_row['Modifier']) if filter_row['Modifier'] else []
        if substrings:
            df_filtered = apply_filter(df, substrings)

        # Apply the remaining filters in the loop
        for i, filter_type in enumerate(['Creature', 'Spell'], start=1):
            operator = filter_row[f'op{i}']
            previous_substrings = substrings
            substrings = re.split(r'\s*,\s*', filter_row[filter_type]) if filter_row[filter_type] else []
            #print(f"Substrings = '{substrings}'")
            if operator == '+':                
                substrings = [f"{s1} {s2}" for s1 in previous_substrings for s2 in substrings]
            
            # If previous_substrings is empty treat the operator as ''
            if not previous_substrings:
                operator = ''

            # If substrings is empty, skip this iteration
            if not substrings:
                substrings = previous_substrings
                continue

            # Apply the filter to the DataFrame
            current_filter_results = apply_filter(df, substrings)

            # Handle the operator logic in the outer loop
            if operator == 'AND':
                df_filtered = df_filtered[df_filtered.index.isin(current_filter_results.index)]
            elif operator == 'OR' :
                df_filtered = pd.concat([df_filtered, current_filter_results]).drop_duplicates()
            elif operator == '+' or operator == '':
                df_filtered = current_filter_results
            else:
                print(f"Operator '{operator}' not recognized")

        return df_filtered

    df_filtered = df_to_filter
    active_filters = filter_df[filter_df['Active'] == True]  # Get only the active filters

    #print(f"Active filters: ")
    #display(active_filters)

    for _, filter_row in active_filters.iterrows():
        #print(f"Applying filter: {filter_row}")
        df_filtered = filter_by_substring(df_filtered, filter_row)

    return df_filtered


# This function will filter the DataFrame df_to_filter based on the active filters in filter_df. 
# For each active filter, it applies the filter to df_filtered using filter_by_substring. 
# If df_filtered becomes empty after filtering, it breaks out of the loop. 
# The function filter_by_substring applies the filters of type 'Modifier' and 'Creature' to df_filtered 
# successively using apply_filter with logical_and=True. 
# If df_filtered is not empty, it applies the filter of type 'Spell' to df_filtered using apply_filter with logical_and=False.

##################
# Event Handling #
##################

def coll_data_on_selection_changed(event, widget):
    global qm
    # Generate a DataFrame from the selected rows
    print(f"Selection changed: {event}")
    deck_df = generate_deck_content_dataframe(event, widget)    
    qm.replace_grid('deck', deck_df)    
    qm.set_default_data('deck', deck_df)
        
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
        return result
    else:
        print(f"Column '{column}' does not exist in the DataFrame.")
        return False

# Goal of this function :
# 1. Update the column definitions of the qgrid widget to set the width of each column to 0 if all values in the column are empty strings
#    Where to get the original column definitions from? global_df[id(qgrid_widget)]
#    Where to get the current column definitions from? qgrid_widget.column_definitions

def update_visible_columns_on_count():
    global qm 

    zero_width_columns = []   
    # Analyze changed DataFrame for updates
    qgrid_widget = qm.grids['count']['main_widget']
    changed_df = qgrid_widget.get_changed_df()
    #print(f"Columns : {changed_df.columns}")
    for column in changed_df.columns:  
        # Check if column values are not just empty strings
        if not check_column_values(column, changed_df):
            zero_width_columns.append(column)
            changed_df.drop(column, axis=1, inplace=True)
        
    qgrid_widget.column_definitions['index'] = {'width' : 250 }
    qgrid_widget.df = changed_df    

# Function to handle changes to the checkbox
def handle_debug_toggle(change):
    if change.new:
        ic.enable()
    else:
        ic.disable()

def handle_db_list_change(change):
    global username

    print(f"DB List Change: {change}")

    if change['name'] == 'value' and change['old'] != change['new']:
        new_username = change['new'] #or ""  # Ensure new_username is a string

        if new_username:

            # Update the Global Username Variable
            GlobalVariables.username = new_username
            GlobalVariables.myDB.set_database_name(new_username)

            # Update Username Widget
            username.value = new_username  # Reflect change in username widget

            # Update Interface for New Username
            update_filter_widget()
            update_decks_display(change)
        else:
            print("No valid database selected.")

def reload_data_on_click(button, value):
    global db_list, username
    username_value = username.value if username else GlobalVariables.username
    GlobalVariables.username = username_value

    if not db_list:
        print("No database list found.")
        return

    print(f"Reloading {value} for username: {username_value}")
    if value == 'Decks':
        arguments = ["--username", username_value,
                     "--mode", 'update']
        print(f"Loading Decks with arguments {arguments}")
        args = parse_arguments(arguments)
        load_deck_data(args)
    elif value == 'Fusions':
        arguments = ["--username", username_value,
                     "--mode", 'update',
                     "--type", 'fuseddeck']
        print(f"Loading Fusions with arguments {arguments}")
        args = parse_arguments(arguments)
        load_deck_data(args)
    elif value == 'Entities':
        myUCL._read_entities_from_csv(os.path.join('csv', 'sff.csv'))

    # Refresh db_list widget
    db_names = GlobalVariables.myDB.mdb.client.list_database_names()
    valid_db_names = [db for db in db_names if db not in ['local', 'admin', 'common', 'config']]

    if valid_db_names:
        db_list.options = valid_db_names
        db_list.value = username_value if username_value in valid_db_names else valid_db_names[0]
    else:
        db_list.options = ['']
        db_list.value = ''  # Set to an empty string if no valid databases


    # Call refresh function for dropdowns
    #handle_username_change({'new': username_value, 'owner': db_list})

def display_graph_on_click(button):
    myDecks = []
    for dropdown in dropdowns:
        myDecks.append(Deck.lookup(dropdown.value))
    
    myDeckA = myDecks[0]
    myDeckB = myDecks[1]

    if myDeckA and myDeckB:
        fusionName = f"{myDeckA.name}_{myDeckB.name}"
        fusionCursor = GlobalVariables.myDB.find('Fusion', {'name' : fusionName})
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
                display(net.show(f"{deck.name}.html"))

def update_decks_display(change):
    ic(update_decks_display, change)
    #print(f"Updating Decks Display : {change}")
    global db_list, qm, filter_grid  # Assuming filter_grid is a global instance of FilterGrid

    for identifier in ['collection', 'count']:
        default_df = qm.get_default_data(identifier)
        if default_df.empty:
            if identifier == 'collection':
                default_df = generate_deck_statistics_dataframe()
            elif identifier == 'count':
                default_df = generate_cardType_count_dataframe()                        
            qm.set_default_data(identifier, default_df)

    if change['new'] or change['new'] == '':                       
        if change['owner'] == db_list:
            print(f"Updating Decks Display for widget db_list")
            # Generate new DataFrame with new database
            default_coll_df = generate_deck_statistics_dataframe() 
            default_count_df = generate_cardType_count_dataframe(default_coll_df)            

            qm.set_default_data('collection', default_coll_df)
            qm.set_default_data('count', default_count_df)

            # Replace the data in the qgrid widgets
            #print(f"Replacing Grid collection with default data")
            qm.replace_grid('collection', default_coll_df)
            #print(f"Replacing Grid count with default data")
            qm.replace_grid('count', default_count_df)
        
        else:
            print(f"Updating Decks Display with FilterGrid")
            default_coll_df = qm.get_default_data('collection')

            # Apply the filter from FilterGrid                
            if filter_grid:                                
                filter_df = filter_grid.get_changed_df()  
                #print(change['new']  )                   
                filtered_df = apply_cardname_filter_to_dataframe(default_coll_df ,filter_df)
                #print(f"Replacing Grid collection with filtered data")
                qm.replace_grid('collection', filtered_df)
                qm.reset_dataframe('deck')
        

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
    cards = GlobalVariables.myDB.find('Card', {})
    cardNames = [card['name'] for card in cards]

    # Filter all cardnames where value is a substring of 
    filtered_cardNames = [cardName for cardName in cardNames if value in cardName]

    # Filter all filtered_options that are a substring of any card name
    filtered_options = [option for option in options if any(option in cardName for cardName in filtered_cardNames)]
    
    # That should leave us with the options that are a substring of any card name and contain the value as a substring
    
    #print(f"Filtered options for {value}: {filtered_options}")
    return filtered_options
    


def refresh_faction_deck_options(faction_toggle, dropdown):    
    GlobalVariables.myDB.set_database_name(GlobalVariables.username)    
    deckCursor = GlobalVariables.myDB.find('Deck', { 'faction' : faction_toggle.value })
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

def initialize_widgets() :
    factionToggle = create_faction_selection_toggle(factionNames)
    dropdown = widgets.Dropdown()
    refresh_faction_deck_options(factionToggle, dropdown)
    factionToggle.observe(lambda change: refresh_faction_deck_options(factionToggle, dropdown), 'value')
    return factionToggle, dropdown

def create_database_selection_widget():
    global username
    db_names = GlobalVariables.myDB.mdb.client.list_database_names()
    db_names = [db for db in db_names if db not in ['local', 'admin', 'common', 'config']]
    db_list = widgets.RadioButtons(
        options= [''] + db_names ,
        description='Databases:',
        disabled=False
        #value=''
    )
    # Set the username to the value of the selected database
    
    #GlobalVariables.username = db_list.value or 'user'
    #GlobalVariables.myDB.set_database_name(GlobalVariables.username)
    # Also set the value of the username widget
    if username:
        username.value = GlobalVariables.username

    def on_db_list_change(change):    
        if username:
            username.value = change['new']

    db_list.observe(on_db_list_change, 'value')

    return db_list

############################
# Setup and Initialization #
############################
import json
def setup_interface():
    global db_list, username, button_load, card_title_widget, \
        qg_coll_options, qg_count_options, qg_syn_options, \
        filter_grid, out_qm, out_main, qm
    
    for i in range(2):            
        factionToggle, dropdown = initialize_widgets()
        factionToggles.append(factionToggle)
        dropdowns.append(dropdown)

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
    qm.add_grid('collection', pd.DataFrame(), options = qg_coll_options, dependent_identifiers=['count'])
    qm.add_grid('count', pd.DataFrame(), options = qg_count_options)    
    qm.add_grid('deck', pd.DataFrame(), options = qg_deck_options)
    
    qm.on('collection', 'selection_changed', coll_data_on_selection_changed)
    qm.on('count', 'selection_changed', coll_data_on_selection_changed)
    # Status Box for Dataframes 
    #df_status_widget = widgets.Textarea(value='', description='DataFrame Status:', disabled=True, layout=widgets.Layout(width='50%', height='200px'))
    #def update_df_status(identifier, df_status):
    #    df_status_widget.value = json.dumps(df_status, default=str, indent=4)

    #qm.register_callback('df_status_changed', update_df_status, identifier='collection')

    # Text widget to enter the username
    #username = widgets.Text(value=GlobalVariables.username, description='Username:', disabled=False)

    # Database selection widget
    db_list = create_database_selection_widget()
    db_list.observe(handle_db_list_change, names='value')

    # Filter widgets
    filter_grid_object = FilterGrid(update_decks_display)
    selection_grid, filter_grid = filter_grid_object.get_widgets()
    filterBox = widgets.VBox([selection_grid, filter_grid])

    # Update the filter grid on db change
    db_list.observe(filter_grid_object.update_selection_content)

    # Button to load decks / fusions / forgborns 
    button_load = widgets.Button(description="Load" )
    button_load.on_click(lambda button: reload_data_on_click(button, loadToggle.value))
    
    # Create a list of HBoxes of factionToggles, Labels, and dropdowns
    toggle_dropdown_pairs = [widgets.HBox([factionToggles[i], dropdowns[i]]) for i in range(len(factionToggles))]

    # Create a Checkbox widget to toggle debugging
    debug_toggle = widgets.Checkbox(value=False, description='Debugging', disabled=False)    
    debug_toggle.observe(handle_debug_toggle, 'value')

    # Toggle Box 
    toggle_box = widgets.VBox([loadToggle,  button_load, username, db_list, debug_toggle])    

    # Display the widgets    
    display(out_debug)
    display(toggle_box) 
    #display(df_status_widget) 
    display(filterBox)      
    display(out_qm)    
    #display(button_graph)
    #display(out_main)         
    #display(*toggle_dropdown_pairs, button_graph)


    from ipywidgets.embed import embed_minimal_html
    widget_list = [filterBox, out_qm]

    embed_minimal_html('export.html', views=widget_list, title='Widgets export')