import os, time, re
import ipywidgets as widgets
from pyvis.network import Network
import networkx as nx
import numpy as np
import qgrid

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
from QGridManager import QGridManager

from icecream import ic
ic.disable()

# Enable qgrid to automatically display all DataFrame and Series instances
#qgrid.enable(dataframe=True, series=True)
#qgrid.set_grid_option('forceFitColumns', False)


# Define Variables
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

GlobalVariables.username = 'enterUsernameHere'
uri = "mongodb://localhost:27017"
#uri = "mongodb+srv://solDB:uHrpfYD1TXVzf3DR@soldb.fkq8rio.mongodb.net/?retryWrites=true&w=majority&appName=SolDB"
myDB = DatabaseManager(GlobalVariables.username, uri=uri)
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

qm = QGridManager()

qgrid_widget_options = {}
filter_grid = None 
global_df = None

out = widgets.Output()
out_qm = widgets.Output()
out_debug = widgets.Output()

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
    'col_options' :         { 'width': 50, } ,
    'col_defs' : {                   
        'name':             { 'width': 250, },     
        'rarity':           { 'width': 125,  },        
        'cardType':         { 'width': 90,  },
        'cardSubType':      { 'width': 110,  },
    }
}

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

def generate_deck_content_dataframe(event, widget):
    ic(generate_deck_content_dataframe, event, widget)
    print(f"Generating Deck Content DataFrame : {event}")

    #Get the selection from the deck widget
    desired_fields = ['name', 'cardSubType', 'levels']    
    if widget:
        header_df = pd.DataFrame()
        all_decks_df = pd.DataFrame()        
        df_selected_rows = event['new']
        # Get the selected rows from the DataFrame based on the indices
        changed_df = widget.get_changed_df()
        decks_df = changed_df.iloc[df_selected_rows]        
        deckList = decks_df.index        
        #deckList = ['The Reeves of Loss', 'The People of Bearing']                
        for deckName in deckList:
            #print(f'DeckName: {deckName}')
            #Get the Deck from the Database 
            deck = myDB.find_one('Deck', {'name': deckName})
            if deck:
                #print(f'Found deck: {deck}')
                #Get the cardIds from the Deck
                cardIds = deck['cardIds']
                cardTitles = []
                deck_df = pd.DataFrame([deck])  # Create a single row DataFrame from deck
                card_dfs = []  # List to store DataFrames for each card
                for cardId in cardIds:
                    card = myDB.find_one('Card', {'_id': cardId})
                    if card:
                        #print(f"Found card: {card['_id']}")
                        # Select only the desired fields from the card document
                        card = {field: card[field] for field in desired_fields if field in card}
                        # Flatten the 'levels' dictionary
                        if 'levels' in card and card['levels']:
                            levels = card.pop('levels')
                            for level, level_data in levels.items():
                                card[f'A{level}'] = int(level_data['attack']) if 'attack' in level_data else ''
                                card[f'H{level}'] = int(level_data['health']) if 'health' in level_data else ''
                        # Create a DataFrame from the remaining card fields
                        card_df = pd.DataFrame([card])                        
                        card_dfs.append(card_df)  # Add full_card_df to the list
                # Concatenate all card DataFrames along the rows axis
                deck_df = pd.concat(card_dfs, ignore_index=True, axis=0)
                # Replace empty values in the 'cardSubType' column with 'Spell'
                if 'cardSubType' in deck_df.columns:
                    deck_df['cardSubType'] = deck_df['cardSubType'].replace(['', '0', 0], 'Spell')
                    deck_df['cardSubType'] = deck_df['cardSubType'].replace(['Exalt'], 'Spell Exalt')
                # Create a header DataFrame with a single row containing the deck name
                deckName_df = pd.DataFrame({'name': [deckName]})                
                header_df = pd.concat([header_df, deckName_df], ignore_index=True, axis=0)                
                all_decks_df = pd.concat([all_decks_df, deck_df], ignore_index=True, axis=0)
                
        # Concatenate the header DataFrame with the deck DataFrames
        final_df = pd.concat([header_df, all_decks_df], ignore_index=True, axis=0)        
    return final_df.fillna('')  
    

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

    # Insert the 'faction' column to the second position
    numeric_df.insert(0, 'faction', faction_df)

    #display(numeric_df)
    return numeric_df


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
            if card_title:  # Check if card_title is not empty
                card_titles.append(card_title)
        # Join the list of titles into a single string separated by commas
        return ', '.join(card_titles)

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

def apply_cardname_filter_to_dataframe(df_to_filter, filter_df):
    with out_debug: 
        def filter_by_substring(df, filter_row):       
            def apply_filter(df, substrings):
                substring_check_results = []

                if not substrings:
                    return df

                #print(f"Applying filter {substrings} to DataFrame")
                #display(df)
                # Iterate over the 'cardTitles' column
                for title in df['cardTitles']:
                    # Apply the check_substring_in_titles function to each title                
                    result = any(substring in title for substring in substrings)
                    substring_check_results.append(result)

                # Convert the list to a pandas Series
                substring_check_results = pd.Series(substring_check_results, index=df.index)

                # Assign the results to filtered_indices
                filtered_indices = substring_check_results
                true_indices = filtered_indices[filtered_indices].index
                print(f"True indices for filter {substrings}: {list(true_indices)}")

                current_filter_results = df[substring_check_results].copy()

                return current_filter_results

            # Define previous_filter_type here
            previous_filter_type = 'Modifier'        

            # Apply the first filter outside the loop
            substrings = re.split(r'\s*,\s*', filter_row['Modifier']) if filter_row['Modifier'] else []
            df_filtered = apply_filter(df, substrings)

            print(type(df_filtered))

            # Apply the remaining filters in the loop
            for i, filter_type in enumerate(['Creature', 'Spell'], start=1):
                operator = filter_row[f'op{i}']
                previous_substrings = substrings
                substrings = re.split(r'\s*,\s*', filter_row[filter_type]) if filter_row[filter_type] else []
                print(f"Substrings = '{substrings}'")
                if operator == '+':
                    #previous_substrings = re.split(r'\s*,\s*', filter_row[previous_filter_type]) if filter_row[previous_filter_type] else []
                    substrings = [f"{s1} {s2}" for s1 in previous_substrings for s2 in substrings]

                # Apply the filter to the original DataFrame when the operator is 'OR'
                df_to_filter = df if operator == 'OR' else df_filtered
                current_filter_results = apply_filter(df_to_filter, substrings)
                previous_filter_type = filter_type            

                # Handle the operator logic in the outer loop
                if operator == 'AND':
                    df_filtered = df_filtered[df_filtered.index.isin(current_filter_results.index)]
                elif operator == 'OR':
                    df_filtered = pd.concat([df_filtered, current_filter_results]).drop_duplicates()
                else:
                    df_filtered = current_filter_results

            return df_filtered

        df_filtered = df_to_filter
        active_filters = filter_df[filter_df['Active'] == True]  # Get only the active filters

        print(f"Active filters: ")
        display(active_filters)

        for _, filter_row in active_filters.iterrows():
            print(f"Applying filter: {filter_row}")
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

def coll_data_on_filter_changed():
    update_visible_rows_on_count()
    update_visible_columns_on_count()

def coll_data_on_selection_changed(event, widget):
    global qm
    # Generate a DataFrame from the selected rows
    qm.update_data('deck', generate_deck_content_dataframe(event, widget))
    
def update_visible_rows_on_count():
    global qm

    source_qgrid = qm.grids['collection']['main_widget']

    # Update the widget's DataFrame     
    df = qm.get_default_data('count')
    source_df = source_qgrid.get_changed_df()
    qm.update_data('count', get_dataframe_apply_index_filter(source = source_df, target = df))
    
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
    print(f"Updating Decks Display : {change}")
    global username, qm, filter_grid  # Assuming filter_grid is a global instance of FilterGrid

    default_coll_df = qm.get_default_data('collection')
    if default_coll_df.empty:
        default_coll_df = generate_deck_statistics_dataframe()
        qm.set_default_data('collection', default_coll_df)

    print(f"change['new']: {change.get('new')}")
    if change['new'] or change['new'] == '':                       

        if change['owner'] == username:
        
            # Generate new DataFrame with new database
            default_coll_df  = generate_deck_statistics_dataframe() 
            default_count_df = generate_cardType_count_dataframe(default_coll_df)            
            
            qm.set_default_data('collection', default_coll_df)
            qm.set_default_data('count', default_count_df)
        
            # Update the data in the qgrid widgets
            out_qm.clear_output()
            with out_qm:    
                for name in ['collection', 'count', 'deck']:
                    qm.display_grid_with_controls(name)

        
        default_coll_df = qm.get_default_data('collection')

        # Apply the filter from FilterGrid
        
        #print(f"Applying filter to collection")
        if filter_grid:                                
            print(f"Filtering collection with filter_grid")
            #print("Displaying default dataframe :")
            #display(default_coll_df)
            filter_df = filter_grid.get_changed_df()
            print("Displaying filter_df")
            display(filter_df)                                
            filtered_df = apply_cardname_filter_to_dataframe(default_coll_df ,filter_df)
            print(f"Result after filtering:")
            display(filtered_df)
            qm.update_data('collection', filtered_df)

        # Apply other changes to the qgrid widgets ( like shrinking columns )
        coll_data_on_filter_changed()

    

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


def create_cardType_names_selector(cardType):    
    
    cardType_entity_names = [''] + get_cardType_entity_names(cardType)    

    cardType_name_widget = widgets.SelectMultiple(
        options=cardType_entity_names,
        description='',        
        #layout=widgets.Layout(width="200px"),
        value=()
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
    dropdown_items = []    

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
        dropdown_items.append(cardType_names_widget)
    
    # Create HBoxes for the labels and widgets
    label_box = widgets.HBox(label_items)
    dropdown_box = widgets.HBox(dropdown_items)    
    
    # Create a caption for the grid with bold text
    caption = widgets.HTML(value='<b>Filter:</b>')

    # Create a VBox to arrange the caption, labels, and widgets vertically
    grid = widgets.VBox([caption, label_box, dropdown_box])
    return grid

class FilterGrid:
    def __init__(self, update_decks_display):
        self.update_decks_display = update_decks_display
        self.df = self.create_initial_dataframe()
        self.qgrid_filter = self.create_filter_qgrid()
        self.selection_box = self.create_selection_box()

    def create_filter_qgrid(self):
        # Create a qgrid widget for the data from the selection widgets
        qgrid_filter = qgrid.show_grid(self.df, grid_options={'forceFitColumns' : False} , column_definitions={'index' : {'width' : 50}, 'op1' : {'width' : 50}, 'op2' : {'width' : 50}} ,show_toolbar=True)    
        qgrid_filter.on('row_added', self.grid_filter_on_row_added)           
        qgrid_filter.on('row_removed', self.grid_filter_on_row_removed)   
        qgrid_filter.on('cell_edited', self.on_cell_edit)             
        return qgrid_filter

    @staticmethod
    def create_initial_dataframe():
        return pd.DataFrame({
            'Modifier': [''],
            'op1': [''],
            'Creature': [''],
            'op2': [''],
            'Spell': [''], 
            'Active': [False]
        })
    
    def grid_filter_on_row_removed(self, event, widget):        
        # Check if index 0 is in the indices
        if 0 in event['indices']:
            df = self.create_initial_dataframe()
            widget.df = pd.concat([df, widget.get_changed_df()], ignore_index=True)
            # Remove index 0 from the indices
            event['indices'].remove(0)
    
        # If there are any indices left, update the display
        if event['indices']:
            # Create the active rows DataFrame
            active_rows = widget.df[widget.df['Active'] == True]
            self.update_decks_display({'new': active_rows, 'old': None, 'owner': 'filter'})

    def grid_filter_on_row_added(self, event, widget):  
        global out_debug
        #with out_debug if out_debug else nullcontext():
        print(f"Row added at index {event['index']}")
        new_row_index = event['index']
        # Get the DataFrame from the qgrid widget
        df = widget.get_changed_df()                   
        print(f"Selection Box Children: {self.selection_box.children}")     
        selected_values = [', '.join(widget.value) if isinstance(widget.value, (list, tuple)) else widget.value for widget in self.selection_box.children[:-1]]        
        selected_values.append(self.selection_box.children[-1].value)  # Handle the Checkbox widget separately
        print(f"Selected values: {selected_values}")        
        for i, column in enumerate(df.columns):                                
            df.loc[new_row_index, column] = selected_values[i]

        # Update the DataFrame in the qgrid widget
        widget.df = df
        
        if widget.df.loc[event['index'], 'Active']:            
            print(f"Calling update_decks_display from grid_filter_on_row_added")                                
            self.update_decks_display({'new': new_row_index, 'old': None, 'owner': 'filter'})
    
    def on_cell_edit(self, event, widget):        
        print(f"Old value: {event['old']} -> New value: {event['new']}")
        row_index = event['index']
        column_index = event['column']                        
        # Set the value for the cell
        widget.df.loc[row_index, column_index] = event['new']
        print(f"Cell edited at row {row_index}, column {column_index}")
        print(f"Final value in cell = {widget.df.loc[row_index, column_index]}")
        
        if widget.df.loc[row_index, 'Active']:
            # Filter is active , so it needs to update the list
            print(f"Calling update_decks_display from on_cell_edit")   
            self.update_decks_display({'new': row_index, 'old': None, 'owner': 'filter'})        

        elif column_index == 'Active':
            # Filter is inactive , so it needs to update the list
            print(f"Calling update_decks_display from on_cell_edit")   
            self.update_decks_display({'new': row_index, 'old': None, 'owner': 'filter'})


    def create_selection_box(self):
        selection_items = []
        for cardTypesString in ['Modifier', 'Creature' , 'Spell']:        
            widget = create_cardType_names_selector(cardTypesString)            
            selection_items.append(widget)
        operator1_widget = widgets.Dropdown(
            options=['+', 'AND', 'OR', ''], 
            description='', 
            layout=widgets.Layout(width='60px'),  # Adjust the width as needed
            value='+'
        )
        operator2_widget = widgets.Dropdown(
            options=['AND', 'OR', ''], 
            description='', 
            layout=widgets.Layout(width='60px'),  # Adjust the width as needed
            value=''
        )
        selection_items.insert(1, operator1_widget)
        selection_items.insert(3, operator2_widget)
        active_widget = widgets.Checkbox(value=True, description='Activated')
        selection_items.append(active_widget)
        selection_box = widgets.HBox(selection_items)
        return selection_box
    def get_changed_df(self):
        return self.qgrid_filter.get_changed_df()

    def get_widgets(self):        
        return self.selection_box, self.qgrid_filter

############################
# Setup and Initialization #
############################
def setup_interface():
    global db_list, username, button_load, card_title_widget, \
        qg_coll_options, qg_count_options, qg_syn_options, \
        filter_grid, out_qm, out, qm
    
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
    qgrid_coll_data  = qm.add_grid('collection', pd.DataFrame(), options = qg_coll_options, dependent_identifiers=['count'])
    qgrid_count_data = qm.add_grid('count', pd.DataFrame(), options = qg_count_options)    
    qgrid_deck_data  = qm.add_grid('deck', pd.DataFrame(), options = qg_deck_options)
    
    qm.on('collection', 'selection_changed', coll_data_on_selection_changed)

    # Text widget to enter the username
    username = widgets.Text(value=GlobalVariables.username, description='Username:', disabled=False)
    username.observe(lambda change: handle_username_change(change), 'value')

    # Database selection widget
    db_list = create_database_selection_widget()
    #db_list_box = widgets.VBox([db_list])    

    # Filter widgets
    grid_filter = create_filter_widgets()
    filter_grid_object = FilterGrid(update_decks_display)
    selection_grid, filter_grid = filter_grid_object.get_widgets()
    filterBox = widgets.VBox([selection_grid, filter_grid])

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
    display(out_debug)
    display(toggle_box)  
    display(filterBox)
    display(out_qm)    
    display(out)     
    #display(*toggle_dropdown_pairs, button_graph)



