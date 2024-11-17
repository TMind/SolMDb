import os, re
import ipywidgets as widgets
from pyvis.network import Network
import networkx as nx
import pickle

import pytz  
from tzlocal import get_localzone  

from GlobalVariables import global_vars as gv
from GlobalVariables import GLOBAL_COLUMN_ORDER

# Ensure global_vars is initialized before using it
if gv is None:
    raise RuntimeError("global_vars was not initialized properly.")

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
from GridManager import GridManager, DynamicGridManager
from CustomGrids import TemplateGrid, ActionToolbar

from icecream import ic
ic.disable()

try:  
    # Try to set the option  
    pd.set_option('future.no_silent_downcasting', True)  
except KeyError:  
    # Handle the case where the option does not exist  
    print("Option 'future.no_silent_downcasting' is not neccessary in this version of pandas.")  

# Enable qgrid to automatically display all DataFrame and Series instances
#qgrid.enable(dataframe=True, series=True)
#qgrid.set_grid_option('forceFitColumns', False)


# Define Variables
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

synergy_template = SynergyTemplate()    

#Read Entities and Forgeborns from Files into Database
deckCollection = None

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

central_frame_output = widgets.Output()
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
        print(f'Fetching decks from Magic Eden') 
        args.type = 'deck'       
        # Fetch the listings from Magic Eden
        collection_symbol = 'sfgc'  # This could be dynamic based on args
        
        deck_data = fetch_all_magiceden_listings(collection_symbol, myApi, args)
        print(f"Total Magic Eden decks processed: {len(deck_data)}")
        gv.myDB.set_database_name('magiceden')
        gv.myDB.drop_database()
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
    global deckCollection
    net_decks = []
    net_fusions = []

    myApi = NetApi()                   
    types = args.type.split(',')
    for type in types:
        if args.username == 'magiceden' and type == 'fuseddeck':
            print(f"Skipping 'fuseddeck' for Magic Eden.")
            continue
        args.type = type
        net_results = fetch_network_decks(args, myApi)            
        
        if args.type == 'deck':     net_decks = net_results
        elif args.type == 'fuseddeck': net_fusions = net_results
        
    deckCollection = DeckLibrary(net_decks, net_fusions, args.mode)
    return deckCollection

def merge_by_adding_columns(df1, df2):
    """
    Merges two DataFrames by adding new columns from df2 to df1. 
    Assumes the indices are the same and there are no new rows to add.
    
    Parameters:
    - df1: First DataFrame.
    - df2: Second DataFrame.
    
    Returns:
    - A DataFrame that contains all columns from both df1 and df2, aligned by index.
    """
    # Ensure both DataFrames have the same index
    if not df1.index.equals(df2.index):
        raise ValueError("The indices of both DataFrames must be the same to merge by adding columns.")

    # Merge DataFrames by concatenating columns
    merged_df = pd.concat([df1, df2], axis=1)
    
    return merged_df

def print_dataframe(df, name):
    print(f'DataFrame: {name}')
    print(f'Shape: {df.shape}')
    print(df.index)    
    display(qgrid.show_grid(df, grid_options={'forceFitColumns': False}, column_definitions=gv.all_column_definitions))    

def clean_columns(df, exclude_columns=None):
    """
    Cleans both numeric and non-numeric columns of a DataFrame by:
    1. Replacing NaN values with 0 in numeric columns and converting them to integers.
    2. Replacing NaN values with empty strings in non-numeric columns.
    3. Converting the numeric DataFrame to strings, replacing '0' with ''.

    Args:
        df (pd.DataFrame): The DataFrame containing columns to clean.

    Returns:
        pd.DataFrame: The cleaned DataFrame with both numeric and non-numeric columns processed.
    """
    if exclude_columns is None:
        exclude_columns = []
    
    # Select numeric columns, excluding the ones you want to preserve
    numeric_df = df.select_dtypes(include='number').drop(columns=exclude_columns, errors='ignore')

    # Replace NaN values with 0 and convert to integer for only numeric columns
    numeric_df = numeric_df.fillna(0).astype(int)
    
    # Convert numeric DataFrame to strings and replace '0' with ''
    numeric_df = numeric_df.astype(str).replace('0', '')

    # Select non-numeric columns
    non_numeric_df = df.select_dtypes(exclude='number')
    non_numeric_df = non_numeric_df.fillna('').replace('0', '')
    
    # Update the original DataFrame with the cleaned numeric and non-numeric DataFrames
    df[numeric_df.columns] = numeric_df
    df[non_numeric_df.columns] = non_numeric_df

    return df

try:
    import qgridnext as qgrid
except ImportError:
    import qgrid
    
# Function to update the central data frame tab    
def update_central_frame_tab(central_df):
    global central_frame_output
    # Update the content of the central_frame_tab
    central_frame_output.clear_output()  # Clear existing content
    with central_frame_output:
        grid = qgrid.show_grid(central_df, grid_options={'forceFitColumns': False}, column_definitions=gv.all_column_definitions)  # Create a qgrid grid from the DataFrame
        grid.add_class(gv.rotate_suffix)
        display(grid)  # Display the qgrid grid
    
    #print("Central DataFrame tab updated.")


def merge_and_concat(df1, df2):
    """
    Efficiently merges two DataFrames by handling overlapping columns and concatenating them row-wise,
    ensuring all columns, including 'deckScore', are preserved.
    """
    # Concatenate both DataFrames row-wise without dropping any columns
    combined_df = pd.concat([df1, df2], axis=0, sort=False)
    
    # If needed, you can fill missing values with NaN (or other strategies)
    #combined_df = combined_df.fillna(value=np.nan)
    
    return combined_df

def enforce_column_order(df, column_order):
    """
    Ensure the DataFrame has the columns in the specified order, 
    but only includes columns that are present in the DataFrame.
    """
    # Ensure the order of columns matches column_order, including only those present in df.columns
    existing_columns = [col for col in column_order if col in df.columns]
    
    # Find columns in df that are not in column_order
    extra_columns = [col for col in df.columns if col not in column_order]
    if extra_columns:
        print(f"Columns in DataFrame that are not in column_order: {extra_columns}")
    
    # Reindex the DataFrame with the valid columns in the specified order
    df_reindexed = df.reindex(columns=existing_columns)
    
    #print_dataframe(df_reindexed, 'Reindexed DataFrame')
    return df_reindexed

def sum_card_types(df):
    # Get the list of columns that are in gv.rotated_column_definitions
    columns_to_sum = [col for col in df.columns if col in gv.rotated_column_definitions.keys()]

    # Convert the specified columns to numeric (float) values, errors='coerce' will turn invalid parsing into NaN
    df[columns_to_sum] = df[columns_to_sum].apply(pd.to_numeric, errors='coerce')

    # Calculate the sum of the specified columns for each row
    sum_column = df[columns_to_sum].sum(axis=1)

    # Concatenate the original DataFrame with the new 'Sum' column
    new_df = pd.concat([df, sum_column.rename('Sum')], axis=1)

    return new_df


user_dataframes = {}
### Dataframe Generation Functions ###
def generate_central_dataframe(force_new=False):
    username = os.getenv('SFF_USERNAME')
    identifier = f"Main DataFrame: {username}"
    file_record = None
    if gv.myDB:
        file_record = gv.myDB.find_one('fs.files', {'filename': f'central_df_{username}'})
    
    # Manage the cached DataFrame
    if not force_new and username in user_dataframes:
        stored_df = user_dataframes[username]
        if stored_df is not None:
            update_deck_and_fusion_counts()
            update_central_frame_tab(stored_df)
            return stored_df

    # Load or regenerate the DataFrame
    if file_record and not force_new:
        if gv.fs:
            with gv.fs.get(file_record['_id']) as file:
                stored_df = pickle.load(file)
                user_dataframes[username] = stored_df
                update_deck_and_fusion_counts()
                update_central_frame_tab(stored_df)
                return stored_df

    gv.update_progress(identifier, total=5, message='Generating Central Dataframe...')
    deck_stats_df = generate_deck_statistics_dataframe()
    #validate_dataframe_attributes(deck_stats_df, 'Deck Stats', expected_index_name=None, disallow_columns=['name'])

    gv.update_progress(identifier, message='Generating Card Type Count Dataframe...')
    card_type_counts_df = generate_cardType_count_dataframe()
    #validate_dataframe_attributes(card_type_counts_df, 'Card Type Counts', expected_index_name=None, disallow_columns=['name'])

    central_df = merge_by_adding_columns(deck_stats_df, card_type_counts_df)
    #validate_dataframe_attributes(central_df, 'Central DF after merging Card Type Counts', expected_index_name=None, disallow_columns=['name'])

    gv.update_progress(identifier, message='Generating Fusion statistics Dataframe...')
    fusion_stats_df = generate_fusion_statistics_dataframe(central_df)
    #validate_dataframe_attributes(fusion_stats_df, 'Fusion Stats', expected_index_name=None, disallow_columns=['name'])

    central_df = merge_and_concat(central_df, fusion_stats_df)
    #validate_dataframe_attributes(central_df, 'Central DF after merging Fusion Stats', expected_index_name=None, disallow_columns=['name'])

    # Clean the columns of the central DataFrame
    gv.update_progress(identifier, message='Clean Central Dataframe...')
    central_df = clean_columns(central_df, exclude_columns=['deckScore', 'elo', 'price', 'Free'])
    central_df = central_df.copy()
    #validate_dataframe_attributes(central_df, 'Central DF after cleaning', expected_index_name=None, disallow_columns=['name'])

    # Reset the index and create a new column named 'name' from the original index
    central_df.reset_index(inplace=True)
    central_df.rename(columns={'name': 'Name'}, inplace=True)
    #validate_dataframe_attributes(central_df, 'Central DF after resetting index' ,expected_index_name=None, disallow_columns=[])

    # Check if renaming was successful
    if 'Name' not in central_df.columns:
        raise RuntimeError("The renaming of the index column to 'Name' failed.")

    #print("Central DataFrame After Resetting Index and Renaming:")
    #print("Columns:", central_df.columns)
    
    # After all DataFrame processing is done, enforce the global column order
    central_df = enforce_column_order(central_df, GLOBAL_COLUMN_ORDER)
    
    gv.update_progress(identifier, message='Central Dataframe Generated.')
    user_dataframes[username] = central_df

    NuOfDecks = len(deck_stats_df)
    NuOfFusions = len(fusion_stats_df)

    if gv.fs:
        if file_record:
            gv.fs.delete(file_record['_id'])
        with gv.fs.new_file(filename=f'central_df_{username}', metadata={'decks': NuOfDecks, 'fusions' : NuOfFusions}) as file:
            pickle.dump(central_df, file)

    update_deck_and_fusion_counts()
    update_central_frame_tab(central_df)
    gv.update_progress(identifier, message='Central Dataframe Stored.')
    return central_df



from CardLibrary import Forgeborn, ForgebornData
def process_deck_forgeborn(item_name, currentForgebornId , forgebornIds):
    try:
        
        forgebornCounter = 0
        inspired_ability_cycle = 0
        forgeborn_ability_texts = {}

        for forgeborn_id in forgebornIds:
            forgebornCounter += 1
            forgebornId = forgeborn_id[:-3]
            if forgebornId.startswith('a'):
                forgebornId = 's' + forgebornId[1:]
            commonDB = DatabaseManager('common')
            forgeborn_data = commonDB.find_one('Forgeborn', {'id': forgebornId})
            if forgeborn_data is None:
                print(f'No data found for forgebornId: {forgebornId}')
                return
            fb_data = ForgebornData(**forgeborn_data)
            forgeborn = Forgeborn(data=fb_data)
            unique_forgeborn = forgeborn.get_permutation(forgeborn_id)
            forgeborn_abilities = unique_forgeborn.abilities

            if forgeborn_abilities:
                for aID, aName in forgeborn_abilities.items():
                    cycle = aID[-3]

                    # Check if the ability is inspired
                    if forgebornCounter == 1 and 'Inspire' in aName:
                        inspired_ability_cycle = cycle 

                    # Apply the inspired label if necessary
                    if forgebornCounter == 2 and cycle == inspired_ability_cycle:
                        #if "Inspire" in aName:
                        #    print(f'Inspired Ability: {aName} {inspired_ability_cycle} for {item_name}')
                        aName += " (Inspire)"
                        
                        #print(f'Inspired Ability: {aName} {inspired_ability_cycle} for {item_name}')
                    
                    # Update the DataFrame with the ability name
                    if forgebornCounter == 1 or cycle == inspired_ability_cycle:
                        forgeborn_ability_texts[cycle] =  aName
                        #df.loc[item_name, f'FB{cycle}'] = aName

            #df.loc[item_name, 'forgebornId'] = currentForgebornId[5:-3].title()
            
            
            replace_forgebornId = currentForgebornId[5:-3].title()
            
            
    except KeyError as e:
        print(f"KeyError: {e}")
        print(f"Index: {item_name}, ForgebornId key: {forgebornIds}")
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Index: {item_name}, ForgebornId key: {forgebornIds}")
    
    
    return replace_forgebornId, forgeborn_ability_texts
    

def generate_deck_content_dataframe(deckNames):
    from CardLibrary import Card , CardData
    
        
    # Get the data set from the global variables
    desired_fields = gv.data_selection_sets['Deck Content']

    card_dfs_list = []

    for deckName in deckNames:
        #print(f'DeckName: {deckName}')
        #Get the Deck from the Database 
        deck = None 
        if gv.myDB:
            deck = gv.myDB.find_one('Deck', {'name': deckName})
        if deck:
            #print(f'Found deck: {deck}')
            #Get the cardIds from the Deck
            cardIds = deck['cardIds']
            deck_df_list = pd.DataFrame([deck])  # Create a single row DataFrame from deck                    
            for cardId in cardIds:
                card = None
                if gv.myDB:
                    card = gv.myDB.find_one('Card', {'_id': cardId})
                if card:
                    fullCard = card 

                    # Create Graph for Card 
                    myGraph = MyGraph()
                    data = CardData(**fullCard)
                    myGraph.create_graph_children(Card(data))
                    interface_ids = myGraph.get_length_interface_ids()

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

                    # Merge the dictionaries
                    card_dict = {**card, **interface_ids}
                    
                    # Insert 'DeckName' at the beginning of the card dictionary
                    card = {'DeckName': deckName, **card_dict}

                    # Create a DataFrame from the remaining card fields      
                    card_df = pd.DataFrame([card])                                             
                    card_dfs_list.append(card_df)  # Add full_card_df to the list                            
            
    # Concatenate the header DataFrame with the deck DataFrames
    if card_dfs_list:
        final_df = pd.concat(card_dfs_list, ignore_index=True, axis=0)        

        # Replace empty values in the 'cardSubType' column with 'Spell'
        if 'cardSubType' in final_df.columns:
            final_df['cardSubType'] = final_df['cardSubType'].replace(['', '0', 0], 'Spell')
            final_df['cardSubType'] = final_df['cardSubType'].replace(['Exalt'], 'Spell Exalt')

        # Sort all columns alphabetically
        sorted_columns = sorted(final_df.columns)
        
        # Ensure 'DeckName' is first, followed by the specified order for other columns
        fixed_order = ['DeckName', 'faction', 'name', 'cardType', 'cardSubType']
        # Remove the fixed order columns from the sorted list
        sorted_columns = [col for col in sorted_columns if col not in fixed_order]
        # Concatenate the fixed order columns with the rest of the sorted columns
        final_order = fixed_order + sorted_columns
        
        # Reindex the DataFrame with the new column order
        final_df = final_df.reindex(columns=final_order)
        #df_numeric = final_df.select_dtypes(include='number')
        # Convert to integers and replace 0 with empty strings
        #df_numeric = df_numeric.fillna(0).astype(int).replace(0, '').astype(str)            
        
        # Select numeric columns and convert them to strings, replacing '0' with an empty string
        df_numeric = final_df.select_dtypes(include='number').astype(str)
        # Replace '0' with an empty string and NaN with an empty string
        df_numeric = df_numeric.replace('0', '').replace('nan', '')
        # Ensure the columns in final_df are of type object to handle the update properly
        final_df[df_numeric.columns] = final_df[df_numeric.columns].astype(object)
        final_df.update(df_numeric)
        # Ensure the DataFrame has the columns in the same order
        final_df = enforce_column_order(final_df, GLOBAL_COLUMN_ORDER)
        return clean_columns(final_df)
    else:
        print(f'No cards found in the database for {deckNames}')
        return pd.DataFrame()


def generate_cardType_count_dataframe():
    identifier = 'CardType Count Data'
    deck_iterator = []
    total_decks = 0 
    if gv.myDB:
        deck_iterator = gv.myDB.find('Deck', {})
        deck_list = list(deck_iterator)
    gv.update_progress(identifier, 0, len(deck_list), 'Generating CardType Count Data...')
    
    all_decks_list = []
    
    for deck in deck_list:
        gv.update_progress(identifier, message=f'Processing Deck: {deck["name"]}')
        
        # Initialize the network graph
        myGraph = MyGraph()
        myGraph.from_dict(deck.get('graph', {}))        
        interface_ids = myGraph.get_length_interface_ids()
        
        # Generate combo data for the current deck  
        combo_data = get_combos_for_graph(myGraph, deck['name'])  

        # Concatenate the interface IDs with the combo data
        interface_ids = {**interface_ids, **combo_data}

        # Prepare DataFrame for interface IDs (including combo data)
        interface_ids_df = pd.DataFrame([interface_ids], index=[deck['name']])

        # Check if the deck has statistics; if not, append only interface_ids_df
        if 'stats' in deck and 'card_types' in deck['stats']:
            cardType_df = pd.DataFrame(deck['stats']['card_types'].get('Creature', {}), index=[deck['name']])
            
            # Ensure indices are consistent before merging
            if not cardType_df.index.equals(interface_ids_df.index):
                cardType_df = cardType_df.reindex(interface_ids_df.index)
            
            # Combine both DataFrames, prioritizing cardType_df values where present
            combined_df = cardType_df.combine_first(interface_ids_df)

            # Append the combined DataFrame
            all_decks_list.append(combined_df)
        else:
            # Append interface_ids_df directly if no card stats
            all_decks_list.append(interface_ids_df)            

    if all_decks_list:
        # Step 1: Gather all possible columns from the single-row DataFrames
        all_columns = set()
        for df in all_decks_list:
            all_columns.update(df.columns)
            
        # Step 2: Reindex each single-row DataFrame to have all columns
        all_decks_list = [df.reindex(columns=all_columns, fill_value='') for df in all_decks_list]

        # Step 3: Concatenate all DataFrames into a single DataFrame
        all_decks_df = pd.concat(all_decks_list, axis=0, sort=False)

        # If the 'name' column is present in columns, set it as index
        if 'name' in all_decks_df.columns:
            all_decks_df.set_index('name', inplace=True)
        
        # Sort columns for consistency
        all_decks_df.sort_index(axis=1, inplace=True)

        all_decks_df = sum_card_types(all_decks_df)

        # Clean numeric columns (convert NaNs to empty strings, etc.)
        all_decks_df = clean_columns(all_decks_df)

        # Enforce global column order
        result_df = enforce_column_order(all_decks_df, GLOBAL_COLUMN_ORDER)

        return result_df
    else:
        print('No decks found in the database')
        return pd.DataFrame()

deck_card_titles = {}    
def generate_fusion_statistics_dataframe(central_df=None):
    deck_card_ids_dict = {}
    if gv.myDB:
       # Get all deck documents from the database
        deck_data_cursor = gv.myDB.find('Deck', {}, {'name': 1, 'cardIds': 1})

        # Create a dictionary to store cardIds by deck name
        deck_card_ids_dict = {deck['name']: deck['cardIds'] for deck in deck_data_cursor if 'name' in deck and 'cardIds' in deck}

    def get_card_titles(card_ids):
        titles = [cid[5:].replace('-', ' ').title() for cid in card_ids if cid[5:].replace('-', ' ').title()]
        return sorted(titles)
    
    def fetch_deck_titles(deck_names):
        deck_titles = {
            name: get_card_titles(deck_card_ids_dict[name])
            for name in deck_names if name in deck_card_ids_dict
        }
        return deck_titles

    def get_card_titles_by_Ids(fusion_children_data):
        gv.update_progress('Fusion Card Titles', message='Fetching Card Titles')
        deck_names = [name for name, dtype in fusion_children_data.items() if dtype == 'CardLibrary.Deck']
        all_card_titles = {name: fetch_deck_titles([name]).get(name, []) for name in deck_names}        
        return ', '.join(sorted(sum(all_card_titles.values(), [])))

    def get_items_from_child_data(children_data, item_type):
        # Children data is a dictionary that contains the deck names as keys, where the value is the object type CardLibrary.Deck
        item_names = [name for name, data_type in children_data.items() if data_type == item_type]
        return item_names
    
    def process_row(fusion_row):
        fusion_name = fusion_row.name
        
        # Process the forgeborn data for each fusion
        replace_forgebornId, forgeborn_ability_texts = process_deck_forgeborn(
            fusion_name, fusion_row['forgebornId'], getattr(fusion_row, 'ForgebornIds', [])
        )
        
        # Update the DataFrame with the forgeborn ID and abilities
        fusion_row['forgebornId'] = replace_forgebornId
        for cycle , ability in forgeborn_ability_texts.items():
            fusion_row[f'FB{cycle}'] = ability

        # Extract decks from children data
        decks = get_items_from_child_data(fusion_row['children_data'], 'CardLibrary.Deck')
        if len(decks) > 1:
            fusion_row['Deck A'] = decks[0]
            fusion_row['Deck B'] = decks[1]


        # Combine deck values to fusion 'digital' 
        if central_df is not None:
            fusion_name = fusion_row.name
            for deck in ['Deck A', 'Deck B']:
                
                # Get deck Name from the fusion_row
                deck_name = fusion_row[deck] if deck in fusion_row else ''
                deck_row = None
                
                # Find the deck in the deck_stats_df
                if deck_name:
                    deck_row = central_df.loc[deck_name] if deck_name in central_df.index else None
                
                # If the deck is found, update the 'digital' and 'cardSetNo' values in the fusion_row
                if deck_row is not None:
                                                            
                    # Set the digital value based on whether any of the decks is digital or not                 
                    digital = deck_row.get('digital', '?')
                    if digital == "0":   digital = 0
                    elif digital == "1": digital = 1
                    elif digital == "":  digital = 0                    
                    
                    if 'digital' not in fusion_row or not isinstance(fusion_row['digital'], set):
                        fusion_row['digital'] = set()
                    fusion_row['digital'].add(digital)
                                    
                    # Set the cardSetNo to combine the values from the decks in a list
                    cardSetNo = deck_row.get('cardSetNo', None)
                    if cardSetNo:
                        if 'cardSetNo' not in fusion_row or not isinstance(fusion_row['cardSetNo'], set):
                            fusion_row['cardSetNo'] = set()
                        fusion_row['cardSetNo'].add(cardSetNo)
                        
                    for item in ['Creatures', 'Spells', 'Exalt']:
                        count = deck_row.get(item, 0)
                        if item not in fusion_row:
                            fusion_row[item] = 0
                        fusion_row[item] += count                    
                
                    Betrayer = deck_row.get('Betrayers', '')
                    if Betrayer:
                        if 'Betrayers' not in fusion_row:
                            fusion_row['Betrayers'] = []
                        fusion_row['Betrayers'].append(Betrayer)
                        
                    SolBind = deck_row.get('SolBinds', '')
                    if SolBind:
                        if 'SolBinds' not in fusion_row:
                            fusion_row['SolBinds'] = []
                        fusion_row['SolBinds'].append(SolBind)
                
                else:
                    print(f"Deck '{deck_name}' not found in the central DataFrame.")
            
            # Convert the set 'digital' to a comma-separated string for display in the DataFrame
            if 'digital' in fusion_row and isinstance(fusion_row['digital'], set):
                fusion_row['digital'] = ", ".join(str(item) for item in fusion_row['digital'])
            
            # Convert the set 'cardSetNo' to a comma-separated string for display in the DataFrame
            if 'cardSetNo' in fusion_row and isinstance(fusion_row['cardSetNo'], set):
                fusion_row['cardSetNo'] = ", ".join(str(item) for item in sorted(fusion_row['cardSetNo']))
            
            if 'Betrayers' in fusion_row and isinstance(fusion_row['Betrayers'], list):
                fusion_row['Betrayers'] = ", ".join(str(item) for item in sorted(fusion_row['Betrayers']))
            
            if 'SolBinds' in fusion_row and isinstance(fusion_row['SolBinds'], list):
                fusion_row['SolBinds'] = ", ".join(str(item) for item in sorted(fusion_row['SolBinds']))
             

        # Generate graph data for the current fusion
        myGraph = MyGraph()
        myGraph.from_dict(fusion_row['graph'])
        interface_ids = myGraph.get_length_interface_ids()    # Store the interface IDs in the database instead of generating it here

        # Generate combo data directly for this fusion
        combo_data = get_combos_for_graph(myGraph, fusion_name)
        interface_ids = {**interface_ids, **combo_data}

        # Convert interface IDs dictionary to DataFrame row and concatenate
        interface_ids_df = pd.DataFrame([interface_ids], index=[fusion_name])
        all_interface_ids_df_list.append(interface_ids_df)

        # Update progress
        gv.update_progress('Fusion Stats', message=f"Processing Fusion Forgeborn: {fusion_name}")
        
        return fusion_row


    # Define the fields you need  
    additional_fields = ['name', 'id', 'type', 'faction', 'crossFaction', 'forgebornId', 'currentForgebornId', 'ForgebornIds', 'CreatedAt', 'UpdatedAt', 'deckRank', 'cardTitles', 'graph', 'children_data', 'tags']  
    projection = {field: 1 for field in additional_fields}  
    
    # Fetch fusions from the database using a batch approach  
    count = 0  
    batch_size = 1000  # Set your desired batch size here  
    df_fusions_filtered = pd.DataFrame()  # Initialize an empty DataFrame  
    
    if gv.myDB:
        fusion_count = gv.myDB.count_documents('Fusion', {})
        fusion_cursor = gv.myDB.find('Fusion', {}, projection).batch_size(batch_size)
        
        batch = []  
        for fusion in fusion_cursor:  
            batch.append(fusion)  
            count += 1  
        
            # If batch is full, process it  
            if len(batch) >= batch_size:  
                df_batch = pd.DataFrame(batch)  
                df_fusions_filtered = pd.concat([df_fusions_filtered, df_batch], ignore_index=True)  
                gv.update_progress('Fetching Fusions', value=count, total=fusion_count, message=f'{count} Fusions fetched so far')  
                batch = []  
        
        # Process any remaining documents in the batch  
        if batch:  
            df_batch = pd.DataFrame(batch)  
            df_fusions_filtered = pd.concat([df_fusions_filtered, df_batch], ignore_index=True)  
            gv.update_progress('Fetching Fusions', value=count, total=fusion_count, message=f'{count} Fusions fetched in total')  
            print(f"{count} fusions fetched from the database.")  
            
    # If fusions are found, process them
    if not df_fusions_filtered.empty:
        gv.update_progress('Fusion Card Titles', 0, len(df_fusions_filtered), 'Fetching Card Titles')

        # Extract necessary columns and add additional calculated columns
        df_fusions_filtered['cardTitles'] = df_fusions_filtered['children_data'].apply(get_card_titles_by_Ids)
        df_fusions_filtered['forgebornId'] = df_fusions_filtered['currentForgebornId']
        df_fusions_filtered['type'] = 'Fusion'

        # Select only relevant fields for analysis
        #additional_fields = ['name', 'id', 'type', 'faction', 'crossFaction', 'forgebornId', 'ForgebornIds', 'CreatedAt', 'UpdatedAt', 'deckRank', 'cardTitles', 'graph', 'children_data', 'tags']
        #df_fusions_filtered = df_fusions[additional_fields].copy()

        # Set 'name' as the index and drop the original 'name' column
        if 'name' in df_fusions_filtered.columns:
            df_fusions_filtered.set_index('name', drop=True, inplace=True)
            # Check if the 'name' column is still in the  dataframe
            if 'name' in df_fusions_filtered.columns:
                print("Column name still present in the DataFrame.")
                df_fusions_filtered.drop('name', axis=1, inplace=True)                
            else:
                print("OK: 'name' column not found in the dataframe.")                 
            
        # Initialize a list to store all interface ID DataFrames
        gv.update_progress('Fusion Stats', 0, len(df_fusions_filtered), 'Generating Fusion Dataframe...')
        all_interface_ids_df_list = []
        
        # Apply the function across all rows in a more efficient way
        all_interface_ids_df_list = []
        df_fusions_filtered = df_fusions_filtered.apply(process_row, axis=1)

        # Concatenate all the interface ID DataFrames
        if all_interface_ids_df_list:            
            interface_ids_total_df = pd.concat(all_interface_ids_df_list)
            interface_ids_total_df.set_index('name', inplace=True, drop=True)
            interface_ids_total_df = clean_columns(interface_ids_total_df)

            # Concatenate the fusion DataFrame with the interface IDs DataFrame
            df_fusions_filtered = pd.concat([df_fusions_filtered, interface_ids_total_df], axis=1)

        # Ensure the column order is correct
        df_fusions_filtered = enforce_column_order(df_fusions_filtered, GLOBAL_COLUMN_ORDER)

        return df_fusions_filtered
    else:
        print('No fusions found in the database')
        return pd.DataFrame()
    
def extract_forgeborn_ids_and_factions(my_decks, fusion_data):
    forgeborn_ids = []
    factions = []

    for deck in my_decks:
        if isinstance(deck, dict):
            # If deck is a dictionary, extract the forgeborn ID and faction
            if 'forgeborn' in deck and isinstance(deck['forgeborn'], dict):
                forgeborn_ids.append(deck['forgeborn']['id'])
            faction = deck.get('faction')
            if faction:
                factions.append(faction)
        elif isinstance(deck, str):
            # If deck is a string, assume the forgeborn IDs are provided separately in fusion_data
            if hasattr(fusion_data, 'ForgebornIds'):
                forgeborn_ids = fusion_data.ForgebornIds
            if hasattr(fusion_data, 'faction'):
                factions.append(fusion_data.faction)
            break  # Exit loop since we handled this case

    return forgeborn_ids, factions
def generate_combo_dataframe(df: pd.DataFrame=None) -> pd.DataFrame:
    # If no DataFrame is provided, fetch Deck and Fusion names and graphs from the database  
    if df is None:  
        items = {'Deck': [], 'Fusion': []}  # Initialize dictionary to avoid KeyError  
        if gv.myDB:  
            for item_type in items.keys():  
                # Fetch only the names and graph fields from the database  
                items[item_type] = [  
                    {'name': item['name'], 'graph': item.get('graph', {})}  
                    for item in gv.myDB.find(item_type, {}, {'name': 1, 'graph': 1})  
                ]              

        # Combine the Deck and Fusion lists, add a 'type' field for differentiation, and create DataFrame  
        data = [{'name': item['name'], 'graph': item['graph'], 'type': item_type}  
                for item_type, item_list in items.items() for item in item_list]  
        df = pd.DataFrame(data)  
  
    # Initialize an empty DataFrame for combos  
    combos_list = []
  
    # For each deck and fusion, process the graph data to generate combos  
    gv.update_progress(f'Combo Data', 0, len(df), 'Generating Combo Data...')  
    #print_dataframe(df, 'Input DataFrame')
    for _, item in df.iterrows():  
        # Process the current item and graph and get its combo data as a dictionary 
        gv.update_progress('Combo Data', message=f'Generating Combo Data for {item["name"]}')  
        myGraph = MyGraph()
        myGraph.from_dict(item['graph'])

        combo_data = get_combos_for_graph(myGraph, item['name'])  
        # Append the combo data to the combos_df DataFrame  
        combos_list.append(combo_data)  
  
    combos_df = pd.DataFrame(combos_list)

    # Merge the original df with the combos_df  
    result_df = pd.merge(df, combos_df, on='name', how='left')  
    result_df = clean_columns(result_df)

    #print_dataframe(result_df, 'Combo DataFrame')  
    return result_df  

def get_combos_for_graph(myGraph: MyGraph, name: str) -> dict:  
    # Prepare the combo data as a dictionary with the item's name  
    combo_data = {'name': name}  
    for combo_name, (input_count, output_count) in myGraph.combo_data.items():  
        product = input_count * output_count  
        text = f'{product:>2}'  
        if product == 0:  
            text = ''  
            if input_count > 0:  
                text = f'{-input_count:>2}'  
                
        combo_data[combo_name] = text  
    
    return combo_data
   

def generate_deck_statistics_dataframe():
    def get_card_titles(card_ids):
        card_titles = [card_id[5:].replace('-', ' ').title() for card_id in card_ids]
        return ', '.join(sorted(card_titles))

    # Get all Decks from the database once and reuse this list
    decks = []
    if gv.myDB:
        decks = list(gv.myDB.find('Deck', {}))
    
    number_of_decks = len(decks)

    df_decks = pd.DataFrame(decks)
    df_decks['cardTitles'] = df_decks['cardIds'].apply(get_card_titles)
    df_decks_filtered = df_decks[['name', 'id', 'registeredDate', 'UpdatedAt', 'pExpiry', 'deckScore', 'deckRank', 'level', 'xp', 'elo', 'cardSetNo', 'digital', 'faction', 'forgebornId', 'cardTitles', 'graph']].copy()
    df_decks_filtered['type'] = 'Deck'
    # Replace non-numeric values with NaN, then convert to int
    df_decks_filtered['cardSetNo'] = pd.to_numeric(df_decks_filtered['cardSetNo'], errors='coerce').fillna(0).astype(int)
    df_decks_filtered['cardSetNo'] = df_decks_filtered['cardSetNo'].replace(99, 0)
    df_decks_filtered['xp'] = df_decks_filtered['xp'].astype(int)
    df_decks_filtered['elo'] = pd.to_numeric(df_decks_filtered['elo'], errors='coerce').fillna(-1).round(2)

    additional_columns = {'Creatures': 0, 'Spells': 0, 'Exalt': 0, 'FB2': '', 'FB3': '', 'FB4': '', 'A1': 0.0, 'H1': 0.0, 'A2': 0.0, 'H2': 0.0, 'A3': 0.0, 'H3': 0.0}
    for column, default_value in additional_columns.items():
        df_decks_filtered[column] = default_value

    df_decks_filtered.set_index('name', inplace=True)

    df_list = []
    identifier = 'Stats Data'
    gv.update_progress(identifier, 0, number_of_decks, 'Generating Statistics Data...')
    for deck in decks:
        gv.update_progress(identifier, message='Processing Deck Stats: ' + deck['name'])        
        
        # Process the forgeborn data for this deck
        deck_name = deck['name']
        forgebornId = deck['forgebornId']
        replace_forgebornId , forgeborn_ability_texts =  process_deck_forgeborn(deck_name, forgebornId, [forgebornId])
        df_decks_filtered.loc[deck_name, 'forgebornId'] = replace_forgebornId
        for cycle, ability in forgeborn_ability_texts.items():
            df_decks_filtered.loc[deck_name, f'FB{cycle}'] = ability
        
        # Fetch all cards in deck from the database
        cards = []
        faction = deck.get('faction')
        if gv.myDB:
            cards = gv.myDB.find('Card', {'_id': {'$in': deck['cardIds']}}) 
            # Collect all cards where the betrayer attribute is True
            betrayers = []
            solbinds = {}
            for card in cards:
                if not card: continue
                crossfaction = card.get('crossfaction') or card.get('crossFaction')
                betrayer = card.get('betrayer')
                rarity = card.get('rarity')
                if rarity == 'Solbind':
                    solbinds['Solbind'] = card['name']
                    for solbind_field in ['solbindId1', 'solbindId2']:
                        if card.get(solbind_field, None):
                            solbind_cardId = card.get(solbind_field, None)[5:]
                            solbind_card = gv.myDB.find_one('Card', {'_id': solbind_cardId})
                            if solbind_card:
                                solbinds[solbind_field] = solbind_card['name']
                            else:
                                solbinds[solbind_field] = card[solbind_field]
                            
                # Check if betrayer is explicitly 'True' as a string
                if crossfaction and crossfaction != faction:
                    betrayers.append(card['name'])                    
                elif betrayer and betrayer == 'True' or betrayer == True:
                    betrayers.append(card['name'])
            
            # Define the order of keys
            solbind_order = ['Solbind', 'solbindId1', 'solbindId2']
            
            df_decks_filtered.loc[deck['name'], 'Betrayers'] = ', '.join(betrayers)
            df_decks_filtered.loc[deck['name'], 'SolBinds'] = ''
            if 'Solbind' in solbinds and solbinds['Solbind']:
                df_decks_filtered.loc[deck['name'], 'SolBinds'] = ', '.join([solbinds[key] for key in solbind_order])
        
        if 'stats' in deck:
            stats = deck.get('stats', {})
            card_type_count_dict = {'Creatures': stats['card_types']['Creature']['count'], 'Spells': stats['card_types']['Spell']['count']}
            if 'Exalt Type' in stats['card_types']['Spell']: 
                card_type_count_dict['Exalt'] = stats['card_types']['Spell']['Exalt Type']
            card_type_count_df = pd.DataFrame([card_type_count_dict], index=[deck['name']])
            attack_dict = stats['creature_averages']['attack']
            defense_dict = stats['creature_averages']['health']
            attack_df = pd.DataFrame([attack_dict], index=[deck['name']])
            defense_df = pd.DataFrame([defense_dict], index=[deck['name']])
            attack_df.columns = ['A1', 'A2', 'A3']
            defense_df.columns = ['H1', 'H2', 'H3']
            deck_stats_df = pd.concat([card_type_count_df, attack_df, defense_df], axis=1).round(2)
            df_list.append(deck_stats_df)

    df_decks_list = pd.concat(df_list, axis=0)
    df_decks_filtered.update(df_decks_list)

    return df_decks_filtered

def validate_dataframe_attributes(df, identifier=None, expected_index_name=None, disallow_columns=None):
    """
    Validate the attributes of a DataFrame.

    Parameters:
    - df (pd.DataFrame): The DataFrame to validate.
    - identifier (str, optional): An identifier for the DataFrame being checked.
    - expected_index_name (str, optional): The expected name of the index.
    - disallow_columns (list, optional): A list of column names that should not be present in the DataFrame.

    Returns:
    - dict: A dictionary containing validation results.
    """
    validation_results = {
        'index_name_correct': True,
        'unwanted_columns_present': False,
        'unwanted_columns': [],
        'messages': []
    }
    
    # Check if the index name matches the expected index name
    if expected_index_name is not None:
        if df.index.name != expected_index_name:
            validation_results['index_name_correct'] = False
            validation_results['messages'].append(f"[{identifier}] Index name '{df.index.name}' does not match the expected name '{expected_index_name}'.")

    # Check for unwanted columns
    if disallow_columns is not None:
        for col in disallow_columns:
            if col in df.columns:
                validation_results['unwanted_columns_present'] = True
                validation_results['unwanted_columns'].append(col)
                validation_results['messages'].append(f"[{identifier}] Column '{col}' should not be present in the DataFrame.")

    # Print summary of validation results
    if validation_results['messages']:
        for message in validation_results['messages']:
            print(message)
    else:
        print(f"[{identifier}] DataFrame validation passed.")

    return validation_results

##################
# Event Handling #
##################

# def coll_data_on_selection_changed(event, widget):
#     global qm
#     # Generate a DataFrame from the selected rows
#     print(f'Selection changed: {event}')
#     deck_df = generate_deck_content_dataframe(event)    
#     qm.replace_grid('deck', deck_df)    
#     qm.set_default_data('deck', deck_df)

# Function to check if any value in the column is not an empty string with regards to the changed_df of the qgrid widget
# def check_column_values(column, changed_df):
#     # Check if the column exists in the DataFrame
#     if column in changed_df.columns:
#         # Check if any value in the column is not an empty string
#         result = changed_df[column].ne('').any()   
#         return result
#     else:
#         print(f"Column '{column}' does not exist in the DataFrame.")
#         return False

# Function to handle changes to the checkbox
def handle_debug_toggle(change):
    if change.new:
        ic.enable()
        gv.debug = True
    else:
        ic.disable()
        gv.debug = False

def handle_db_list_change(change):
    global username_widget, grid_manager

    if gv.out_debug:
        with gv.out_debug:
            print(f'DB List Change: {change}')

    if change['name'] == 'value' and change['old'] != change['new']:
        new_username = change['new'] #or ''  # Ensure new_username is a string

        if new_username:

            change['type'] = 'username'
            # Update the Global Username Variable
            gv.username = new_username

            # Update Username Widget
            username_widget.value = new_username  # Reflect change in username widget
            
            grid_manager.refresh_gridbox(change)
        else:
            pass 
            #print('No valid database selected.')

operation_in_progress = False  # Add this global variable to track the in-progress state

def reload_data_on_click(button, value):
    global db_list, username_widget, operation_in_progress

    # Prevent multiple concurrent operations
    if operation_in_progress:
        print('Operation is already in progress. Please wait.')
        return

    # Set the flag to indicate that the operation is ongoing
    operation_in_progress = True

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
        elif value == 'Generate Dataframe':
            generate_central_dataframe(force_new=True)
            grid_manager.refresh_gridbox({'type': 'generation', 'new': 'central_dataframe'})
            return
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
        elif value == 'Find Combos':
            combo_df = generate_combo_dataframe()
            return combo_df

        # Execute main task if other tasks are not returning early
        load_deck_data(args)
        # Refresh db_list widget
        db_names = []
        if not gv.myDB:
            gv.set_myDB()
        db_names = gv.myDB.mdb.client.list_database_names()
        valid_db_names = [db for db in db_names if db not in ['local', 'admin', 'common', 'config']]

        if valid_db_names:
            db_list.options = [''] + valid_db_names
            if username_value in valid_db_names:
                update_deck_and_fusion_counts()
                db_list.value = username_value
            else:
                db_list.value = valid_db_names[0]
        else:
            db_list.options = ['']
            db_list.value = ''  # Set to an empty string if no valid databases
    finally:
        # Ensure we reset the progress flag and button state
        operation_in_progress = False
        if button:
            button.disabled = False

def display_graph_on_click(button):
    myDecks = []
    for dropdown in dropdowns:
        myDecks.append(Deck.lookup(dropdown.value))
    
    myDeckA = myDecks[0]
    myDeckB = myDecks[1]

    if myDeckA and myDeckB:
        fusionName = f'{myDeckA.name}_{myDeckB.name}'
        fusionCursor = None
        if gv.myDB:
            fusionCursor = gv.myDB.find('Fusion', {'name' : fusionName})
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

# def update_filter_widget(change=None):
#     global cardTypes_names_widget
    
#     # Get values of both widgets
#     widget_values = {cardTypesString: cardType_widget.value for cardTypesString, cardType_widget in cardTypes_names_widget.items()}

#     if not change or all(value == '' for value in widget_values.values()):    
#         # If no change is passed or both values are '' , update both widgets
#         for cardTypesString, cardType_widget in cardTypes_names_widget.items():
#             if cardType_widget:
#                 new_options = []
#                 for cardType in cardTypesString.split('/'):
#                     new_options = new_options + get_cardType_entity_names(cardType)                
#                 cardType_widget.options = [''] + new_options
#     else:
#         # If a change is passed, update the other widget
#         changed_widget = change['owner']  
#         if change['new'] == '':             
#             # Get the value of the other widget from the already fetched values
#             for cardTypesString, cardType_widget in cardTypes_names_widget.items():
#                 if cardType_widget and cardType_widget != changed_widget:                    
#                     change['new'] = widget_values[cardTypesString]
#                     change['owner'] = cardType_widget                        
#             update_filter_widget(change)            
#         else:
#             for cardTypesString, cardType_widget in cardTypes_names_widget.items():
#                 if cardType_widget and cardType_widget != changed_widget and cardType_widget.value == '':                
#                     new_options = []
#                     for cardType in cardTypesString.split('/'):
#                         new_options = new_options + get_cardType_entity_names(cardType)           
#                     new_options = filter_options(change['new'], new_options)  # Filter the options                         
#                     cardType_widget.options = [''] + new_options    
    

# def filter_options(value, options):
#     # First get all card names from the database
#     cards = global_vars.myDB.find('Card', {})
#     cardNames = [card['name'] for card in cards]

#     # Filter all cardnames where value is a substring of 
#     filtered_cardNames = [cardName for cardName in cardNames if value in cardName]

#     # Filter all filtered_options that are a substring of any card name
#     filtered_options = [option for option in options if any(option in cardName for cardName in filtered_cardNames)]
    
#     # That should leave us with the options that are a substring of any card name and contain the value as a substring
    
#     #print(f'Filtered options for {value}: {filtered_options}')
#     return filtered_options
    

def refresh_faction_deck_options(faction_toggle, dropdown):    
    #global_vars.myDB.set_database_name(global_vars.username)   
    deckCursor = []
    if gv.myDB: 
        deckCursor = gv.myDB.find('Deck', { 'faction' : faction_toggle.value })
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

# Initialize a global dictionary to store the different stats to be displayed
display_data = {
    'Collection': {},
    'CM Sheet': {}  # Allowing for complex structures
}
count_display = widgets.Output()
def update_count_display():
    """
    Updates the count_display widget with the combined information stored in the display_data dictionary.
    Displays each Info Type with its corresponding key-value pairs in a structured format.
    """
    global count_display
    global display_data

    # Clear the output widget
    count_display.clear_output()

    # Initialize a list to hold rows for the DataFrame
    rows = []

    for key, value in sorted(display_data.items()):
        if value:  # Only proceed if the value is not empty
            if isinstance(value, dict):
                # Add each key-value pair in the dictionary as new rows with Info Type
                for sub_key, sub_value in sorted(value.items()):
                    rows.append((key, sub_key, sub_value))

    # Create a DataFrame from the rows
    if rows:
        df_display = pd.DataFrame(rows, columns=['Info Type', 'Key', 'Value'])

        # Set a MultiIndex using Info Type and Sub Key
        df_display.set_index(['Info Type', 'Key'], inplace=True)

        # Display the DataFrame in the output widget
        with count_display:
            display(df_display)  # Use the display function to show the DataFrame
    else:
        with count_display:
            print("No data to display.")

def update_deck_and_fusion_counts():
    global display_data
    
    # Ensure we are querying the right database based on the selected username
    db_manager = gv.myDB
    if db_manager:
        
        # Count the number of decks and fusions in the database
        deck_count = db_manager.count_documents('Deck', {})
        fusion_count = db_manager.count_documents('Fusion', {})
        username = db_manager.get_current_db_name()        

        # Query the GridFS for the 'central_df' file
        file_record = db_manager.find_one('fs.files', {'filename': f"central_df_{username}"})
        
        if file_record and 'uploadDate' in file_record:
            # Get the local timezone from your system
            utc_upload_date = file_record['uploadDate']
            local_timezone = get_localzone()
            NuOfDecks = file_record['metadata']['decks'] if 'metadata' in file_record else 0
            NuOfFusions = file_record['metadata']['fusions'] if 'metadata' in file_record else 0
            
            # Convert UTC to your local timezone
            creation_date = utc_upload_date.replace(tzinfo=pytz.utc).astimezone(local_timezone)
            creation_date_str = creation_date.strftime('%Y-%m-%d %H:%M:%S')
            
            # Store the DataFrame information in the dictionary
            display_data['DataFrame'] = {
                'Timestamp':    creation_date_str,
                'Decks':        NuOfDecks,
                'Fusions' :     NuOfFusions                
            }
            
        else:
            creation_date_str = "No previous update found"
        
        # Store the deck and fusion count information in the dictionary
        display_data['Collection'] = {
            'Timestamp': creation_date_str,
            'Decks': deck_count,
            'Fusions': fusion_count
        }
        
        
        
        
        # Call the helper function to update the display
        update_count_display()
    else:
        print('No database manager found.')


def update_sheet_stats():
    """
    Updates the timestamp, title, and tags of the Google Sheet only when this function is called.
    This avoids frequent and unnecessary connections to Google Sheets.
    """
    global display_data

    # Ensure the CMManager is already initialized in GlobalVariables
    if gv.cm_manager:
        # Get the current timestamp and title from the CMManager
        current_timestamp = gv.cm_manager.timestamp  # Direct access
        current_title = gv.cm_manager.title  # Direct access

        # Store the latest sheet information in display_data
        display_data['CM Sheet'] = {
            'Title': current_title,
            'Timestamp': current_timestamp
        }

        # Call helper function to update the display
        update_count_display()

    else:
        print("CMManager not initialized.")
            
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
    global db_list, button_load, card_title_widget, grid_manager, central_frame_output, tab, net_api
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
        options=['Load Decks/Fusions', 'Update Decks/Fusions', 'Generate Dataframe', 'Update CM Sheet'],
        description='Action:',
        disabled=False,
        button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
        tooltips=['Load Decks and Fusions from the website', 'Update Decks and Fusions in the database', 'Generate table from database', 'Get the latest version from Collection Manager'])

    # Button to load decks / fusions / forgborns 
    button_load = widgets.Button(description='Execute', button_style='info', tooltip='Execute the selected action')
    button_load.on_click(lambda button: reload_data_on_click(button, loadToggle.value))

    # Database selection widget
    db_list = create_database_selection_widget()
    db_list.observe(handle_db_list_change, names='value')
    
    # Create a Checkbox widget to toggle debugging
    debug_toggle = widgets.Checkbox(value=False, description='Debugging', disabled=False)    
    debug_toggle.observe(handle_debug_toggle, 'value')
    
    data_generation_functions = {
        'central_dataframe' : generate_central_dataframe, 
        'deck_content' : generate_deck_content_dataframe,
        'update_selection_area' : None,}
    
    # Create an instance of the manager
    grid_manager = DynamicGridManager(data_generation_functions, qg_options, gv.out_debug)

    # Update the filter grid on db change
    db_list.observe(grid_manager.filterGridObject.update_selection_content, names='value')

    # Create styled HTML widgets with background colors
    db_helper = create_styled_html(
        "Database Tab: This tab allows you to load and manage a database for a username on Solforge Fusion.",
        text_color='white', bg_color='blue', border_color='blue'
    )

    # Create the guidance text
    db_guide_text = """
### **Creating a New Database**

1. **Select a Database:**
    - Use the "Databases" list to select an existing database or leave it empty if you want to create a new one.

2. **Set Your Username:**
    - Enter your username in the "Username" text box. This username will be associated with your Solforge Fusion account.

3. **Choose an Action:**

    - **Load Decks/Fusions:**  
      Select this option to fetch and load decks and fusions from the network. This action is necessary to populate your database with existing data.
    
    - **Create All Fusions:**  
      Choose this option to generate all possible fusions based on the decks currently available in the database. This is helpful for exploring new combinations and strategies.
    
    - **Generate Dataframe:**  
      This option generates a comprehensive dataframe summarizing your decks, fusions, and other related statistics. The dataframe contains all relevant information in a non-structured format.

4. **Execute the Action:**
    - Once you’ve selected the desired action, click the "Execute" button to perform the operation. The system will process your request and update the database accordingly.

5. **Review Data Counts:**
    - The label below the action buttons will display the current counts of decks and fusions in your database, along with the timestamp of the last update. This helps you monitor the content of your database.

### **Button Descriptions**

- **Load Decks/Fusions:**  
  Fetches and loads online decks and fusions into the selected database. Creates a new database if none exists.

- **Create All Fusions:**  
  Creates all possible fusions based on the decks in the database. Useful for exploring new combinations.

- **Generate Dataframe:**  
  Aggregates data from the database into a central dataframe, providing a summary of all relevant statistics.

- **Execute:**  
  Executes the selected action (loading data, creating fusions, or generating the dataframe).
"""

    deck_guide_text = """
### **FilterGrid Guide**

The **FilterGrid** is a dynamic filtering tool that allows you to apply custom filters to your data and view the results in an interactive grid. Below is a guide on how to use the FilterGrid and its features.

---

#### **Using the FilterGrid**

1. **Creating and Managing Filters:**
   - The FilterGrid allows you to create multiple filters by defining criteria across different columns of your dataset. Each filter is represented by a row in the filter grid.
   - You can specify conditions for different types of data (e.g., `Creature`, `Spell`, `Forgeborn Ability`) and combine them using logical operators such as `AND`, `OR`, and `+`.
     - **`AND`**: Filters will match only if both surrounding fields are met (mandatory).
     - **`OR`**: Filters will match if either of the surrounding fields is met (optional).
   - Within each field, you can make specific items mandatory or optional:
     - **`+`**: Use `+` to delimit items that must be included in the filter. For example, `+Dragon+` will make "Dragon" a mandatory match.
     - **`-`**: Use `-` to delimit items that are optional. For example, `-Elf-` will make "Elf" an optional match.
   - The **Forgeborn Ability** field is mandatory in every filter row and must be filled in to apply the filter.
   - For each filter, you can decide whether it is active or not by toggling the **Active** checkbox. Only active filters will be applied to the data.

2. **Adding a New Filter Row:**
   - To add a new filter row, click the **"Add Row"** button. A new row will appear in the filter grid where you can define your filter criteria.
   - The available fields include:
     - **Type**: Choose between `Deck` and `Fusion`.
     - **Modifier**, **Creature**, **Spell**: Select the entities or card types that you want to filter.
     - **Forgeborn Ability**: Select specific abilities from the Forgeborn cards.
     - **Data Set**: Choose the dataset to apply the filter to (e.g., `Fusion Tags`).

3. **Removing a Filter Row:**
   - To remove a filter row, select the row you want to remove and click the **"Remove Row"** button. The row will be deleted, and the remaining filters will be automatically adjusted.

4. **Editing Filters:**
   - You can edit any existing filter by clicking on its cells and modifying the content. The filter will be applied in real-time as you make changes.

5. **Visualizing Filtered Data:**
   - Once the filters are applied, the FilterGrid will dynamically generate and display the filtered datasets in individual grids below the filter row. Each grid corresponds to the specific filter applied to the data, bearing the same number.
   - The filtered results are shown in a tabular format, allowing you to analyze the data that meets your specified criteria.

"""


    # Convert Markdown to HTML using the markdown module
    guide_html_content = md.markdown(db_guide_text)
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
    guide_html_content = md.markdown(deck_guide_text)
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
    deck_tab = widgets.VBox([deck_helper, deck_accordion, deck_filter_bar, grid_manager.get_ui()])    
    central_frame_tab = widgets.VBox([central_frame_helper, central_frame_output])

    # Create the Tab widget with children
    tab = widgets.Tab(children=[db_tab, deck_tab, central_frame_tab])
    tab.set_title(0, 'Database')
    tab.set_title(1, 'Decks')
    tab.set_title(2, 'CentralDataframe')

    # Set the default selected tab
    tab.selected_index = 1


    # Layout: Progress bars at the top, then the tab widget below
    layout = widgets.VBox([progressbar_header,gv.progressbar_container,tab])
    display(layout)

    update_sheet_stats()
    
    if db_list and 'magiceden' in db_list.options:
        db_list.value = 'magiceden'
    else:
        username_widget.value = 'magiceden'
        reload_data_on_click(None, 'Load Decks/Fusions')
    
    username_widget.disabled = True 
    db_list.disabled = True 
    

def setup_interface():
    global db_list, button_load, card_title_widget, grid_manager, central_frame_output, tab, net_api
    global action_toolbar, selected_db_label, selected_items_label, text_box, graph_output, username_jhub

    if username_jhub == 'magiceden' : 
        return setup_restricted_interface()
            
    # Function to update the action area with selected info
    def update_action_area():
        # Get selected DB info and selected items from the grid manager
        if gv.myDB:
            selected_db_info = gv.myDB.get_current_db_name()  # Assuming gv.myDB manages the current database
        else:
            selected_db_info = "None"
        selected_items_info = grid_manager.get_selected_grid_items()  # This now returns a dictionary with lists of names

        # Update the labels with new info
        selected_db_label.value = f"Selected Database: {selected_db_info}"

        if selected_items_info:
            # Since selected_items_info is a dictionary of lists, we can flatten the lists and join the names
            selected_names = [name for names_list in selected_items_info.values() for name in names_list]

            # Update the label with the selected names
            selected_items_label.value = f"Selected Items: {', '.join(selected_names) if selected_names else 'None'}"
        else:
            selected_items_label.value = "Selected Items: None"
    
    
    for i in range(2):            
        factionToggle, dropdown = initialize_widgets()
        factionToggles.append(factionToggle)
        dropdowns.append(dropdown)

    # Button to create network graph
    button_graph = widgets.Button(description='Show Graph')
    button_graph.on_click(lambda button: display_graph()) #display_graph_on_click(button))

    # Toggle buttons to select load items
    loadToggle = widgets.ToggleButtons(
        options=['Load Decks/Fusions', 'Update Decks/Fusions', 'Create all Fusions', 'Generate Dataframe', 'Find Combos', 'Update CM Sheet'],
        description='Action:',
        disabled=False,
        button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
        tooltips=['Load Decks and Fusions from the website', 'Update Decks and Fusions in the database', 'Create Fusions from loaded decks', 'Get the latest version from Collection Manager'])

    # Button to load decks / fusions / forgborns 
    button_load = widgets.Button(description='Execute', button_style='info', tooltip='Execute the selected action')
    button_load.on_click(lambda button: reload_data_on_click(button, loadToggle.value))

    # Database selection widget
    db_list = create_database_selection_widget()
    db_list.observe(handle_db_list_change, names='value')
    
    # Create a list of HBoxes of factionToggles, Labels, and dropdowns
    toggle_dropdown_pairs = [widgets.HBox([factionToggles[i], dropdowns[i]]) for i in range(len(factionToggles))]

    # Create a Checkbox widget to toggle debugging
    debug_toggle = widgets.Checkbox(value=False, description='Debugging', disabled=False)    
    debug_toggle.observe(handle_debug_toggle, 'value')
    
    data_generation_functions = {
        'central_dataframe' : generate_central_dataframe, 
        'deck_content' : generate_deck_content_dataframe,
        'update_selection_area' : update_action_area,}
    
    # Create an instance of the manager
    grid_manager = DynamicGridManager(data_generation_functions, qg_options, gv.out_debug)

    # Update the filter grid on db change
    db_list.observe(grid_manager.filterGridObject.update_selection_content, names='value')

    templateGrid = TemplateGrid()

    # Create styled HTML widgets with background colors
    db_helper = create_styled_html(
        "Database Tab: This tab allows you to load and manage a database for a username on Solforge Fusion.",
        text_color='white', bg_color='blue', border_color='blue'
    )

    # Create the guidance text
    db_guide_text = """
### **Creating a New Database**

1. **Select a Database:**
    - Use the "Databases" list to select an existing database or leave it empty if you want to create a new one.

2. **Set Your Username:**
    - Enter your username in the "Username" text box. This username will be associated with your Solforge Fusion account.

3. **Choose an Action:**

    - **Load Decks/Fusions:**  
      Select this option to fetch and load decks and fusions from the network. This action is necessary to populate your database with existing data.
    
    - **Create All Fusions:**  
      Choose this option to generate all possible fusions based on the decks currently available in the database. This is helpful for exploring new combinations and strategies.
    
    - **Generate Dataframe:**  
      This option generates a comprehensive dataframe summarizing your decks, fusions, and other related statistics. The dataframe contains all relevant information in a non-structured format.

4. **Execute the Action:**
    - Once you’ve selected the desired action, click the "Execute" button to perform the operation. The system will process your request and update the database accordingly.

5. **Review Data Counts:**
    - The label below the action buttons will display the current counts of decks and fusions in your database, along with the timestamp of the last update. This helps you monitor the content of your database.

### **Button Descriptions**

- **Load Decks/Fusions:**  
  Fetches and loads online decks and fusions into the selected database. Creates a new database if none exists.

- **Create All Fusions:**  
  Creates all possible fusions based on the decks in the database. Useful for exploring new combinations.

- **Generate Dataframe:**  
  Aggregates data from the database into a central dataframe, providing a summary of all relevant statistics.

- **Execute:**  
  Executes the selected action (loading data, creating fusions, or generating the dataframe).
"""

    deck_guide_text = """
### **FilterGrid Guide**

The **FilterGrid** is a dynamic filtering tool that allows you to apply custom filters to your data and view the results in an interactive grid. Below is a guide on how to use the FilterGrid and its features.

---

#### **Using the FilterGrid**

1. **Creating and Managing Filters:**
   - The FilterGrid allows you to create multiple filters by defining criteria across different columns of your dataset. Each filter is represented by a row in the filter grid.
   - You can specify conditions for different types of data (e.g., `Creature`, `Spell`, `Forgeborn Ability`) and combine them using logical operators such as `AND`, `OR`, and `+`.
     - **`AND`**: Filters will match only if both surrounding fields are met (mandatory).
     - **`OR`**: Filters will match if either of the surrounding fields is met (optional).
   - Within each field, you can make specific items mandatory or optional:
     - **`+`**: Use `+` to delimit items that must be included in the filter. For example, `+Dragon+` will make "Dragon" a mandatory match.
     - **`-`**: Use `-` to delimit items that are optional. For example, `-Elf-` will make "Elf" an optional match.
   - The **Forgeborn Ability** field is mandatory in every filter row and must be filled in to apply the filter.
   - For each filter, you can decide whether it is active or not by toggling the **Active** checkbox. Only active filters will be applied to the data.

2. **Adding a New Filter Row:**
   - To add a new filter row, click the **"Add Row"** button. A new row will appear in the filter grid where you can define your filter criteria.
   - The available fields include:
     - **Type**: Choose between `Deck` and `Fusion`.
     - **Modifier**, **Creature**, **Spell**: Select the entities or card types that you want to filter.
     - **Forgeborn Ability**: Select specific abilities from the Forgeborn cards.
     - **Data Set**: Choose the dataset to apply the filter to (e.g., `Fusion Tags`).

3. **Removing a Filter Row:**
   - To remove a filter row, select the row you want to remove and click the **"Remove Row"** button. The row will be deleted, and the remaining filters will be automatically adjusted.

4. **Editing Filters:**
   - You can edit any existing filter by clicking on its cells and modifying the content. The filter will be applied in real-time as you make changes.

5. **Visualizing Filtered Data:**
   - Once the filters are applied, the FilterGrid will dynamically generate and display the filtered datasets in individual grids below the filter row. Each grid corresponds to the specific filter applied to the data, bearing the same number.
   - The filtered results are shown in a tabular format, allowing you to analyze the data that meets your specified criteria.

"""


    # Convert Markdown to HTML using the markdown module
    guide_html_content = md.markdown(db_guide_text)
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
    guide_html_content = md.markdown(deck_guide_text)
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
    db_tab = widgets.VBox([db_helper, db_accordion, loadToggle, button_load, count_display, username_widget, db_list])
    deck_tab = widgets.VBox([deck_helper, deck_accordion, deck_filter_bar, grid_manager.get_ui()])
    template_tab = widgets.VBox([template_helper, templateGrid.get_ui()])
    graph_tab = widgets.VBox([fusions_helper, *toggle_dropdown_pairs, button_graph, graph_output])
    debug_tab = widgets.VBox([debug_helper, debug_toggle, gv.out_debug])
    central_frame_tab = widgets.VBox([central_frame_helper, central_frame_output])

    # Create the Tab widget with children
    tab = widgets.Tab(children=[db_tab, deck_tab, template_tab, graph_tab, debug_tab, central_frame_tab])
    tab.set_title(0, 'Database')
    tab.set_title(1, 'Decks')
    tab.set_title(2, 'Templates')
    tab.set_title(3, 'Graphs')
    tab.set_title(4, 'Debug')
    tab.set_title(5, 'CentralDataframe')

    # Set the default selected tab
    tab.selected_index = 0
    
    # Create the labels that will be updated
    selected_db_label = widgets.Label(value="Selected Database: None")
    selected_items_label = widgets.Label(value="Selected Items: None")        

    def authenticate(button):
        username = gv.myDB.get_current_db_name()  
        password = text_box.value  # Get the password from the text box
        net_api = NetApi(username, password)
        
    def save_grid_dataframe(change):
        """
        Function to save the DataFrame from the grid to a CSV file.
        This function is triggered when the 'Save' button is clicked.
        """
        # Get the DataFrame from the grid manager
        if grid_manager:
            grid_manager.save_dataframes_to_csv()
        else:
            print("No GridManager available")


    # Function to open the selected deck in the browser
    def open_deck(button):
        global grid_manager        
        #selected_names = grid_manager.get_selected_grid_items()
        selected_items_info = selected_items_label.value.split(': ')[1] 
        username = selected_db_label.value.split(': ')[1]

        # Get the rows from the central dataframe based on the selected names
        central_df = user_dataframes[username]

        for item in selected_items_info.split(','):
            item = item.strip()
            
            # Get the row corresponding to the selected item
            item_row = central_df[central_df['Name'] == item]
            
            if not item_row.empty:
                # Convert the single-row DataFrame to a dictionary
                item_dict = item_row.to_dict(orient='records')[0]

                # Access 'id' and 'type' directly from the dictionary
                item_id = item_dict['id']
                item_type = item_dict['type']

                # Determine the correct URL path based on the item type
                if item_type == 'Fusion':
                    item_type = 'fused'
                elif item_type == 'Deck':
                    item_type = 'decks'

                # Create the link and open it in the web browser
                item_link = f'https://solforgefusion.com/{item_type}/{item_id}'
                webbrowser.open(item_link)
            else:
                print(f"Item '{item}' not found in the central dataframe.")
        

        # # Iterate over the dictionary items
        # item_links = []
        # for grid_id, selected_rows in selected_dfs.items():
        #     # selected_rows is a list of dictionaries representing rows
        #     for item_row in selected_rows:
        #         # Access the 'id' field from each row dictionary
        #         item_id = item_row.get('id')
        #         item_type = item_row.get('type')
                
        #         if item_type == 'Fusion' : item_type = 'fused'
        #         if item_type == 'Deck'   : item_type = 'decks'
                
        #         if item_type:
        #             item_link = f'https://solforgefusion.com/{item_type}/{item_id}'                                
        #             item_links.append(item_link)
        
        # for item_link in item_links:
        #     webbrowser.open(item_link)        
        #     pass

    # Function for making a solbind request
    def solbind_request(button):
        username = selected_db_label.value.split(': ')[1]  # Extract the username from the label
        selected_items_info = selected_items_label.value.split(': ')[1]  # Extract selected items from the label
        password = text_box.value  # Get the password from the text box
        
        # Here, handle multiple selected items if needed
        if ',' in selected_items_info:
            print("Multiple items selected, please select only one deck.")
            return
        deck_name = selected_items_info  # Assuming single selection
        deck_data = gv.myDB.find_one('Deck', {'name': deck_name})
        if deck_data:
            deck_id = deck_data.get('id')
        
        # Proceed with the solbind request using NetApi
        net_api = NetApi(username, password)
        net_api.post_solbind_request(deck_id)

    # Function for renaming a fusion
    def rename_fusion(button):
        #username = gv.myDB.get_current_db_name()  
        selected_items_info = selected_items_label.value.split(': ')[1]  # Extract selected items from the label
        #password = text_box.value  # Get the password from the text box
        
        # Here, handle multiple selected items if needed
        if ',' in selected_items_info:
            print("Multiple items selected, please select only one fusion.")
            return
        fusion_name = selected_items_info.strip(" ")  # Assuming single selection
        fusion = gv.myDB.find_one('Fusion', {'name': fusion_name})
                
        # Prompt for new name
        new_name = text_box.value
        
        # Proceed with the rename request using NetApi
        #net_api = NetApi(username, password)
        net_api.update_fused_deck(fusion, new_name)
    
    # Initialize the ActionToolbar and pass the update function
    action_toolbar = ActionToolbar()
    action_toolbar.assign_callback('Authenticate', authenticate)
    action_toolbar.assign_callback('Solbind', solbind_request)
    action_toolbar.assign_callback('Rename', rename_fusion)
    #action_toolbar.assign_callback('Open (Web)', open_deck)
    action_toolbar.assign_callback('Export', save_grid_dataframe)
    action_toolbar.add_button('Open', 'Open (web)', callback_function=open_deck)

    # Action area where the toolbar and the labels are displayed
    action_area = widgets.VBox([selected_db_label, selected_items_label, text_box, action_toolbar.get_ui()])
    
    # Layout: Progress bars at the top, then the tab widget below
    layout = widgets.VBox([progressbar_header,gv.progressbar_container,action_area, tab])
    display(layout)

    update_sheet_stats()
    


        
