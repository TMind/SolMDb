import os, time, re
import ipywidgets as widgets
from numpy import isin
from pyvis.network import Network
import networkx as nx
import pickle

from GlobalVariables import global_vars
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
from GridManager import GridManager, DynamicGridManager, TemplateGrid

from icecream import ic
ic.disable()

pd.set_option('future.no_silent_downcasting', True)

# Custom CSS style

custom_css = '''
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
'''
display(HTML(custom_css))  


# Enable qgrid to automatically display all DataFrame and Series instances
#qgrid.enable(dataframe=True, series=True)
#qgrid.set_grid_option('forceFitColumns', False)


# Define Variables
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

synergy_template = SynergyTemplate()    
ucl_paths = [os.path.join('csv', 'sff.csv'), os.path.join('csv', 'forgeborn.csv'), os.path.join('csv', 'synergies.csv')]

#Read Entities and Forgeborns from Files into Database
myUCL = UniversalLibrary(global_vars.username, *ucl_paths)
deckCollection = None

# Widget Variables
factionToggles = []
dropdowns = []
factionNames = ['Alloyin', 'Nekrium', 'Tempys', 'Uterra']
types = ['Decks', 'Fusions']
username_widget = widgets.Text(value=global_vars.username, description='Username:', disabled=False)
button_load = None
db_list = None 
cardTypes_names_widget = {}
deck_selection_widget = None

qgrid_widget_options = {}
data_generation_functions = {}

out_debug = widgets.Output()
central_frame_output = widgets.Output()

# Manager Variables
grid_manager = None 
qm = GridManager(out_debug)

# Widget original options for qgrid
default_width = 150

all_column_definitions = {
    'index':            {'width': 50},
    'name':             {'width': 250},
    'type':             {'width': 60},
    'Deck A':           {'width': 250},
    'Deck B':           {'width': 250},
    'registeredDate':   {'width': 200},
    'UpdatedAt':        {'width': 200},
    'xp':               {'width': 50},
    'elo':              {'width': 50},
    'level':            {'width': 50},
    'pExpiry':          {'width': 200},
    'cardSetNo':        {'width': 50},
    'faction':          {'width': 100},
    'forgebornId':      {'width': 100},
    'cardTitles':       {'width': 200},
    'FB4':              {'width': default_width},
    'FB2':              {'width': default_width},
    'FB3':              {'width': default_width},
    'A1':               {'width': 50},
    'H1':               {'width': 50},
    'A2':               {'width': 50},
    'H2':               {'width': 50},
    'A3':               {'width': 50},
    'H3':               {'width': 50},
    'Creatures':        {'width': 80},
    'Spells':           {'width': 80},
    'Beast':            {'width': 80},
    'Beast Synergy':    {'width': default_width},
    'Dinosaur':         {'width': 80},
    'Dinosaur Synergy': {'width': default_width},
    'Mage':             {'width': 80},
    'Mage Synergy':     {'width': default_width},
    'Robot':            {'width': 80},
    'Robot Synergy':    {'width': default_width},
    'Scientist':        {'width': 80},
    'Scientist Synergy': {'width': default_width},
    'Spirit':           {'width': 80},
    'Spirit Synergy':   {'width': default_width},
    'Warrior':          {'width': 80},
    'Warrior Synergy':  {'width': default_width},
    'Zombie':           {'width': 80},
    'Zombie Synergy':   {'width': default_width},
    'Replace Setup':    {'width': default_width},
    'Replace Profit':    {'width': default_width},
    'Minion':           {'width': 80},
    'Minion Synergy':   {'width': default_width},
    'Spell':            {'width': 80},
    'Spell Synergy':    {'width': default_width},
    'Healing Source':   {'width': default_width},
    'Healing Synergy':  {'width': default_width},
    'Movement':         {'width': 80},
    'Disruption':       {'width': 80},
    'Movement Benefit':  {'width': default_width},
    'Armor':            {'width': 80},
    'Armor Giver':      {'width': default_width},
    'Armor Synergy':    {'width': default_width},
    'Activate':         {'width': 80},
    'Ready':            {'width': 80},
    'Free':             {'width': 80},
    'Upgrade':          {'width': 80},
    'Upgrade Synergy':  {'width': default_width},
    'Face Burn':        {'width': 80},
    'Removal':          {'width': 80},
    'Breakthrough':     {'width': default_width},
    'Breakthrough Giver':{'width': default_width},
    'Aggressive':       {'width': 80},
    'Aggressive Giver': {'width': default_width},
    'Defender':         {'width': 80},
    'Defender Giver':   {'width': default_width},
    'Stealth':          {'width': 80},
    'Stealth Giver':    {'width': default_width},
    'Stat Buff':        {'width': default_width},
    'Attack Buff':      {'width': default_width},
    'Health Buff':      {'width': default_width},
    'Stat Debuff':      {'width': default_width},
    'Attack Debuff':    {'width': default_width},
    'Health Debuff':    {'width': default_width},
    'Destruction Synergy':{'width': default_width},
    'Destruction Activator':{'width': default_width},
    'Self Damage Payoff':{'width': default_width},
    'Self Damage Activator':{'width': default_width},
    'Silence':          {'width': 80},
    'White Fang':       {'width': 80},
    'Dragon':           {'width': 80},
    'Dragon Synergy':   {'width': default_width},
    'Elemental':        {'width': 80},
    'Elemental Synergy':{'width': default_width},
    'Plant':            {'width': 80},
    'Plant Synergy':    {'width': default_width},
    'Exalts':           {'width': 80},
    'Exalt Synergy':    {'width': default_width},
    'Slay':             {'width': 80},
    'Deploy':           {'width': 80},
    'Last Winter':      {'width': default_width},
    'Spicy':            {'width': 80},
    'Cool':             {'width': 80},
    'Fun':              {'width': 80},
    'Annoying':         {'width': 80}
}

qg_options ={ 'column_options' : {}, 'column_definitions' : all_column_definitions }   
class StdErrRedirector(object):
    global out_debug
    def __init__(self, output_widget):
        self.output_widget = output_widget
        self._old_stderr = sys.stderr
    
    def write(self, message):
        with self.output_widget:
            self._old_stderr.write(message)
            print(message, end='', file=self._old_stderr)  # Display in the original stderr as well
            
    def flush(self):
        self._old_stderr.flush()

import sys
# Redirect stderr to the output widget
sys.stderr = StdErrRedirector(out_debug)

######################
# Network Operations #
######################

def fetch_network_decks(args, myApi):
    #print(f'Fetching Network Decks with args: {args}')
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

    myApi = NetApi(myUCL)                   
    types = args.type.split(',')
    for type in types:
        args.type = type
        net_results = fetch_network_decks(args, myApi)            
        
        if args.type == 'deck':     net_decks = net_results
        elif args.type == 'fuseddeck': net_fusions = net_results
        
    deckCollection = DeckLibrary(net_decks, net_fusions, args.mode)
    return deckCollection


# Function to update the central data frame tab
import qgridnext as qgrid
def update_central_frame_tab(central_df):
    global central_frame_output
    # Update the content of the central_frame_tab
    central_frame_output.clear_output()  # Clear existing content
    with central_frame_output:
        grid = qgrid.show_grid(central_df, grid_options={'forceFitColumns': False}, column_definitions=all_column_definitions)  # Create a qgrid grid from the DataFrame
        display(grid)  # Display the qgrid grid
    
    print("Central DataFrame tab updated.")

user_dataframes = {}
### Dataframe Generation Functions ###
def generate_central_dataframe(force_new=False):
    # Get the current username from the global variables

    def merge_on_index(df1, df2):
        # Merge with suffixes to temporarily differentiate overlapping columns
        merged_df = df1.merge(df2, left_index=True, right_index=True, how='left', suffixes=('', '_dup'))

        # Identify overlapping columns (those with '_dup' suffix)
        overlap_cols = [col[:-4] for col in merged_df.columns if col.endswith('_dup')]

        # Combine overlapping columns and drop duplicates
        for col in overlap_cols:
            merged_df[col] = merged_df[col].combine_first(merged_df[f'{col}_dup'])
            merged_df.drop(columns=[f'{col}_dup'], inplace=True)

        return merged_df

    username = global_vars.username
    identifier = f"Main DataFrame: {username}"

    file_record = global_vars.myDB.find_one('fs.files',  {'filename': 'central_df'})
    if not force_new:
        if username in user_dataframes:
            update_central_frame_tab(user_dataframes[username])
            return user_dataframes[username]

        # Check if the DataFrame already exists in GridFS
        if file_record:
            # Retrieve the DataFrame from GridFS
            file_id = file_record['_id']
            with global_vars.fs.get(file_id) as file:
                central_df = pickle.load(file)
                user_dataframes[username] = central_df
                update_central_frame_tab(central_df)
                return central_df
    else:
        # Clear the existing DataFrame from the user_dataframes dictionary
        if username in user_dataframes:
            del user_dataframes[username]
    
        # Delete the old DataFrame from GridFS
        if file_record:
            file_id = file_record['_id']
            global_vars.fs.delete(file_id)                        

    # Start with deck statistics which form the basis of the DataFrame
    global_vars.update_progress(identifier, 0, 100, 'Generating Central Dataframe...')
    deck_stats_df = generate_deck_statistics_dataframe()
    
    global_vars.update_progress(identifier, 50, 100, 'Halfway there...')
    # Generate card type counts and merge them into the deck_stats_df
    card_type_counts_df = generate_cardType_count_dataframe()
    

    # Example usage    
    central_df = merge_on_index(deck_stats_df, card_type_counts_df)

#    central_df = deck_stats_df.merge(card_type_counts_df, left_index=True, right_index=True, how='left', suffixes=('', ''))

    fusion_stats_df = generate_fusion_statistics_dataframe()

    # Append the fusion_stats_df to the central_df
    central_df = pd.concat([central_df, fusion_stats_df])
    
    # Reset the index to move the index to the 'name' column
    central_df.reset_index(inplace=True)
    
    global_vars.update_progress(identifier, 100, 100, 'Central Dataframe Generated.')

    # Store the central_df in the user_dataframes dictionary
    user_dataframes[username] = central_df.copy()

  # Serialize the DataFrame to a bytes-like object and store it in GridFS
    with global_vars.fs.new_file(filename='central_df') as file:
        pickle.dump(central_df, file)

    update_central_frame_tab(central_df)
    return central_df

from CardLibrary import Forgeborn, ForgebornData
def process_deck_forgeborn(item_name, currentForgebornId , forgebornIds, df):
    try:
        if item_name not in df.index:
            display(df)
            print(f"Fusion name '{item_name}' not found in DataFrame index.")
            return        
        
        forgebornCounter = 0
        inspired_ability_cycle = 0

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
                        if "Inspire" in aName:
                            print(f'Inspired Ability: {aName} {inspired_ability_cycle} for {item_name}')
                        aName += " (Inspire)"
                        
                        #print(f'Inspired Ability: {aName} {inspired_ability_cycle} for {item_name}')
                    
                    # Update the DataFrame with the ability name
                    if forgebornCounter == 1 or cycle == inspired_ability_cycle:
                        df.loc[item_name, f'FB{cycle}'] = aName

            df.loc[item_name, 'forgebornId'] = currentForgebornId[5:-3].title()
    except KeyError as e:
        print(f"KeyError: {e}")
        print(f"Index: {item_name}, ForgebornId key: {forgebornIds}")
        print(df.head())
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Index: {item_name}, ForgebornId key: {forgebornIds}")
        print(df.head())

def generate_deck_content_dataframe(event = None):
    global deck_selection_widget
    ic(generate_deck_content_dataframe)
    #print(f'Generating Deck Content DataFrame : {event}')
    widget = deck_selection_widget

    with out_debug:
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
                print('No previous data found in the deck grid.')
                unique_deckNames = []
            else:
                # Get the unique values from the deckName column in old_df
                unique_deckNames = old_df['DeckName'].unique().tolist()
        
            # Add the deckList to the unique_deckNames and remove the deselectList
            print(f'Select: {selectList} \nDeselect: {deselectList}\nUnique: {unique_deckNames}')
            union_set = set(unique_deckNames) | set(selectList)
            deckList =  list(union_set - set(deselectList))            
            #deckList = ['The Reeves of Loss', 'The People of Bearing']                
            card_dfs_list = []  # List to store DataFrames for each card

            from CardLibrary import Card , CardData

            for deckName in deckList:
                print(f'DeckName: {deckName}')
                #Get the Deck from the Database 
                deck = global_vars.myDB.find_one('Deck', {'name': deckName})
                if deck:
                    #print(f'Found deck: {deck}')
                    #Get the cardIds from the Deck
                    cardIds = deck['cardIds']
                    deck_df_list = pd.DataFrame([deck])  # Create a single row DataFrame from deck                    
                    for cardId in cardIds:
                        card = global_vars.myDB.find_one('Card', {'_id': cardId})
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
                fixed_order = ['DeckName', 'name', 'cardType', 'cardSubType', 'A1', 'H1', 'A2', 'H2', 'A3', 'H3']
                # Remove the fixed order columns from the sorted list
                sorted_columns = [col for col in sorted_columns if col not in fixed_order]
                # Concatenate the fixed order columns with the rest of the sorted columns
                final_order = fixed_order + sorted_columns
                
                # Reindex the DataFrame with the new column order
                final_df = final_df.reindex(columns=final_order)
                
                return final_df.fillna('')
            else:
                print(f'No cards found in the database for {deckList}')
                return pd.DataFrame()

def generate_cardType_count_dataframe(existing_df=None):
    # Initialize a list to accumulate the DataFrames for each deck
    all_decks_list = []
    identifier = 'CardType Count Data'

    # Get interface ids from the database 
    #interface_ids = global_vars.commonDB.find('Interface', {})
    #interface_ids = [interface['_id'] for interface in interface_ids]
    #print(f'Interface IDs: {interface_ids}')
    
    # Get the cardTypes from the stats array in the database
    deckIterator = global_vars.myDB.find('Deck', {})
    
    # Get the number of decks in the collection
    totalDecks = global_vars.myDB.count_documents('Deck', {})

    global_vars.update_progress(identifier, 0, totalDecks , 'Generating CardType Count Data...')

    for deck in deckIterator:

        global_vars.update_progress(identifier, message = f'Processing Deck: {deck["name"]}')
        deckName = deck['name']
        myDeck = Deck.load(deckName)
        myGraph = MyGraph()
        #myGraph.create_graph_children(myDeck)

        myGraph.G = nx.from_dict_of_dicts(deck['graph'])

        interface_ids = myGraph.get_length_interface_ids()

        # Add a new row to the interface_ids_df DataFrame with the index of deckName and the column of interface_id
        interface_ids_df = pd.DataFrame(interface_ids, index=[deckName])

        #display(interface_ids_df)
        if 'stats' in deck:
            stats = deck.get('stats', {})
            card_types = stats.get('card_types', {})                        
            cardType_df = pd.DataFrame(card_types['Creature'], index=[deckName])
            
            # Combine interface_ids_df and cardType_df
            cardType_df = cardType_df.combine_first(interface_ids_df)

            # Add 'faction' column to cardType_df
            cardType_df['faction'] = deck.get('faction', 'None')  # Replace 'Unknown' with a default value if 'faction' is not in deck

            # Append cardType_df to all_decks_list
            all_decks_list.append(cardType_df)

    # Concatenate all the DataFrames in all_decks_list, keeping the original index    
    if all_decks_list : 
        all_decks_df = pd.concat(all_decks_list)
        all_decks_df.sort_index(axis=1, inplace=True)
    else:
        print('No decks found in the database')
        all_decks_df = pd.DataFrame()

    # Filter all_decks_df to only include rows that exist in existing_df ( not necessary anymore )
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

    #numeric_df.reset_index(inplace=True)
    #numeric_df.rename(columns={'index': 'name'}, inplace=True)

    #display(numeric_df)
    return numeric_df

deck_card_titles = {}
def generate_fusion_statistics_dataframe():

    def get_items_from_child_data(children_data, item_type):
        # Children data is a dictionary that contains the deck names as keys, where the value is the object type CardLibrary.Deck 
        item_names = []
        for name, data_type in children_data.items():
            if data_type == item_type:
                item_names.append(name)

        return item_names

    def get_card_titles(card_ids):
        card_titles = []
        for card_id in card_ids:
            card_title = card_id[5:].replace('-', ' ').title()

            if card_title:  # Check if card_title is not empty
                card_titles.append(card_title)
        # Join the list of titles into a single string separated by commas
        return sorted(card_titles)

    def get_card_titles_by_Ids(fusion_children_data):
        global deck_card_titles
        all_card_titles_list = []
        deck_names = get_items_from_child_data(fusion_children_data, 'CardLibrary.Deck')
        
        for deck_name in deck_names:
            card_titles_list = deck_card_titles.get(deck_name)
            
            if card_titles_list is None:
                deck = global_vars.myDB.find_one('Deck', {'name': deck_name})
                if deck:
                    card_ids = deck.get('cardIds', [])
                    card_titles_list = get_card_titles(card_ids)
                    deck_card_titles[deck_name] = card_titles_list
            
            if card_titles_list:
                all_card_titles_list.extend(card_titles_list)
            global_vars.update_progress('Fusion Card Titles', message=f'Fetching Card Titles for {deck_name}')
        cardTitles = ', '.join(sorted(all_card_titles_list))        
        return cardTitles
        
    # Fetch fusion data
    fusion_cursor = global_vars.myDB.find('Fusion', {})
    
    # Convert cursor to DataFrame
    df_fusions = pd.DataFrame(list(fusion_cursor))
    global_vars.update_progress('Fusion Card Titles', 0, len(df_fusions) * 2, 'Fetching Card Titles')
    df_fusions['cardTitles'] = df_fusions['children_data'].apply(get_card_titles_by_Ids)    
    df_fusions_filtered = df_fusions[['name', 'CreatedAt', 'UpdatedAt', 'deckRank', 'children_data', 'graph', 'node_data', 'tags', 'cardTitles']].copy()
    df_fusions_filtered['type'] = 'Fusion'

    df_fusions_filtered.set_index('name', inplace=True)

    # Add new columns for Deck A, Deck B, and forgebornId
    df_fusions_filtered['Deck A'] = None
    df_fusions_filtered['Deck B'] = None
    df_fusions_filtered['forgebornId'] = None

    # Assign values before setting index
    total = len(df_fusions)
    global_vars.update_progress('Fusion Stats', 0, total, 'Generating Fusion Dataframe...')    
    for fusion_data in df_fusions.itertuples():
        fusion_name = fusion_data.name
        decks = get_items_from_child_data(fusion_data.children_data, 'CardLibrary.Deck')
        myDecks = fusion_data.myDecks
        # Filter out invalid entries and ensure they contain the required structure
        valid_decks = [deck for deck in myDecks if isinstance(deck, dict) and 'forgeborn' in deck and isinstance(deck['forgeborn'], dict)]
        forgebornIds = [deck['forgeborn']['id'] for deck in valid_decks]
        currentForgebornId = valid_decks[0]['forgeborn']['id'] if valid_decks else None

        # Handle the case where forgebornIds might come from fusion_data
        if not forgebornIds and 'ForgebornIds' in fusion_data:
            forgebornIds = fusion_data['ForgebornIds']
            currentForgebornId = forgebornIds[0] if forgebornIds else None
                    
        # Determine the faction of the fusion , which is the faction of the deck where the forgebornId is the currentForgebornId
        faction = valid_decks[0]['faction'] if valid_decks else None

        # Assign the faction to the DataFrame
        if faction:
            df_fusions_filtered.loc[fusion_name, 'faction'] = faction

        if len(decks) > 1:
            df_fusions_filtered.loc[fusion_name, 'Deck A'] = decks[0]
            df_fusions_filtered.loc[fusion_name, 'Deck B'] = decks[1]
        if currentForgebornId:
            print(f'ForgebornId: {currentForgebornId} for {fusion_name}')
            df_fusions_filtered.loc[fusion_name, 'forgebornId'] = currentForgebornId

        process_deck_forgeborn(fusion_data.name, currentForgebornId, forgebornIds, df_fusions_filtered)
        global_vars.update_progress('Fusion Stats', message = f"Processing Fusion Forgeborn:  {fusion_data.name}")

    return df_fusions_filtered

# Data Handling and Transformation 
def generate_deck_statistics_dataframe():

    def get_card_titles(card_ids):
        card_titles = []
        for card_id in card_ids:
            card_title = card_id[5:].replace('-', ' ').title()
            #card_title = get_card_title(card_id)

            if card_title:  # Check if card_title is not empty
                card_titles.append(card_title)
        # Join the list of titles into a single string separated by commas
        return ', '.join(sorted(card_titles))

    # Get all Decks from the database
    deck_cursor = global_vars.myDB.find('Deck', {}) 
    deck_list = list(deck_cursor)       
    df_decks = pd.DataFrame(deck_list)
    df_decks['cardTitles'] = df_decks['cardIds'].apply(get_card_titles)
    df_decks_filtered = df_decks[[ 'name', 'registeredDate', 'UpdatedAt', 'pExpiry', 'level', 'xp', 'elo', 'cardSetNo', 'faction', 'forgebornId', 'cardTitles']].copy()
    df_decks_filtered['type'] = 'Deck'

    # For column 'cardSetNo' replace the number 99 with 0 
    df_decks_filtered['cardSetNo'] = df_decks_filtered['cardSetNo'].astype(int).replace(99, 0)
    df_decks_filtered['xp'] = df_decks_filtered['xp'].astype(int)

    # Assuming 'name' is the column with names and 'elo' originally contains the values to convert

    # Convert 'elo' to numeric, coercing errors to NaN
    df_decks_filtered['elo'] = pd.to_numeric(df_decks_filtered['elo'], errors='coerce').astype(float).round(2)
    df_decks_filtered['elo'] = df_decks_filtered['elo'].fillna(-1)

    # Identify rows where conversion failed
    failed_conversions = df_decks_filtered[df_decks_filtered['elo'].isna()]

    # Iterate over the failed conversions to print/store the name and original 'elo' value
    for index, row in failed_conversions.iterrows():
        with out_debug:
            print(f"Index: {index}, Name: {row['name']}, Failed Value: {row['elo']}")

    # Add additional columns to the DataFrame -> Count
    additional_columns_count = ['Creatures', 'Spells']
    for column in additional_columns_count:
        df_decks_filtered.loc[:,column] = 0

    # Add additional columns to the DataFrame -> FB
    additional_columns_fb = ['FB2', 'FB3', 'FB4']
    for column in additional_columns_fb:
        df_decks_filtered.loc[:,column] = ''

    # Add additional columns to the DataFrame -> Stats
    additional_columns_stats = ['A1', 'H1', 'A2', 'H2', 'A3', 'H3']
    for column in additional_columns_stats:
        df_decks_filtered.loc[:,column] = 0.0
            
    df_decks_filtered.set_index('name', inplace=True)
    
    identifier = 'Forgeborn Data'

    # Create a DataFrame from the fb_abilities sub-dictionary  
    number_of_decks = global_vars.myDB.count_documents('Deck', {})
    global_vars.update_progress(identifier, 0, number_of_decks, 'Fetching Forgeborn Data...')
    for deck in global_vars.myDB.find('Deck', {}) :
        global_vars.update_progress(identifier, message = 'Processing Deck Forgeborn: ' + deck['name'])
        if 'forgebornId' in deck:   process_deck_forgeborn(deck['name'], deck['forgebornId'] ,[deck['forgebornId']], df_decks_filtered)

    identifier = 'Stats Data' 
    global_vars.update_progress(identifier, 0, number_of_decks, 'Generating Statistics Data...')
    
    # Create a DataFrame from the 'stats' sub-dictionary
    for deck in global_vars.myDB.find('Deck', {}):
        global_vars.update_progress(identifier, message = 'Processing Deck Stats: ' + deck['name'])

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


##################
# Event Handling #
##################

def coll_data_on_selection_changed(event, widget):
    global qm
    # Generate a DataFrame from the selected rows
    print(f'Selection changed: {event}')
    deck_df = generate_deck_content_dataframe(event, widget)    
    qm.replace_grid('deck', deck_df)    
    qm.set_default_data('deck', deck_df)
        
# def get_dataframe_apply_index_filter(source, target):
#     # Initialize a list to store the filtered rows
#     filtered_rows = []

#     # Iterate over the indices of the source DataFrame
#     for idx in source.index:
#         # Check if the index exists in the target DataFrame
#         if idx in target.index:
#             # Filter the target DataFrame for each index and add the result to the list
#             filtered_rows.append(target.loc[[idx]])

#     # Concatenate all the filtered rows into a DataFrame
#     filtered_df = pd.concat(filtered_rows) if filtered_rows else pd.DataFrame()

#     return filtered_df

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

# def update_visible_columns_on_count():
#     global qm 

#     zero_width_columns = []   
#     # Analyze changed DataFrame for updates
#     qgrid_widget = qm.grids['count']['main_widget']
#     changed_df = qgrid_widget.get_changed_df()
#     #print(f'Columns : {changed_df.columns}')
#     for column in changed_df.columns:  
#         # Check if column values are not just empty strings
#         if not check_column_values(column, changed_df):
#             zero_width_columns.append(column)
#             changed_df.drop(column, axis=1, inplace=True)
        
#     qgrid_widget.column_definitions['index'] = {'width' : 250 }
#     qgrid_widget.df = changed_df    

# Function to handle changes to the checkbox
def handle_debug_toggle(change):
    if change.new:
        ic.enable()
        global_vars.debug = True
    else:
        ic.disable()
        global_vars.debug = False

def handle_db_list_change(change):
    global username_widget, grid_manager

    with out_debug:
        print(f'DB List Change: {change}')

    if change['name'] == 'value' and change['old'] != change['new']:
        new_username = change['new'] #or ''  # Ensure new_username is a string

        if new_username:

            change['type'] = 'username'
            # Update the Global Username Variable
            global_vars.username = new_username
            #global_vars.myDB = DatabaseManager(new_username)
            #global_vars.myDB.set_database_name(new_username)

            # Update Username Widget
            username_widget.value = new_username  # Reflect change in username widget
            update_deck_and_fusion_counts()

            # Update Interface for New Username
            #update_filter_widget()
            
            grid_manager.refresh_gridbox(change)
        else:
            print('No valid database selected.')

def reload_data_on_click(button, value):
    global db_list, username_widget
    username_value = username_widget.value if username_widget else global_vars.username
    global_vars.username = username_value

    if not db_list:
        print('No database list found.')
        return

    #print(f'{value} for username: {username_value}')
    if value == 'Load Decks/Fusions':
        arguments = ['--username', username_value,
                     '--mode', 'update',
                     '--type', 'deck,fuseddeck']
        print(f'Loading Decks/Fusions with arguments {arguments}')
        args = parse_arguments(arguments)
     
    elif value == 'Create all Fusions':
        arguments = ['--username', username_value,
                     '--mode', 'create' ]
        print(f'Loading Fusions with arguments {arguments}')
        args = parse_arguments(arguments)    

    load_deck_data(args)
    # Refresh db_list widget
    db_names = global_vars.myDB.mdb.client.list_database_names()
    valid_db_names = [db for db in db_names if db not in ['local', 'admin', 'common', 'config']]

    if valid_db_names:
        db_list.options = [''] + valid_db_names
        #print(f'Valid DB Names: {valid_db_names}')
        #print(f'Username Value: {username_value}')
        
        if username_value in valid_db_names:
            #print(f'Setting db_list value to {username_value}')
            # Force update the central DataFrame for the username after reloading the data 
            generate_central_dataframe(force_new=True)
            db_list.value = username_value
        else:
            #print(f'Setting db_list value to {valid_db_names[0]} because {username_value} not in {valid_db_names}')
            db_list.value = valid_db_names[0]
        
    else:
        db_list.options = ['']
        db_list.value = ''  # Set to an empty string if no valid databases

def display_graph_on_click(button):
    myDecks = []
    for dropdown in dropdowns:
        myDecks.append(Deck.lookup(dropdown.value))
    
    myDeckA = myDecks[0]
    myDeckB = myDecks[1]

    if myDeckA and myDeckB:
        fusionName = f'{myDeckA.name}_{myDeckB.name}'
        fusionCursor = global_vars.myDB.find('Fusion', {'name' : fusionName})
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
    deckCursor = global_vars.myDB.find('Deck', { 'faction' : faction_toggle.value })
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
    print('Displaying Graph!')
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
        username_widget.value = global_vars.username

    def on_db_list_change(change):    
        if username_widget:
            username_widget.value = change['new']

    db_list.observe(on_db_list_change, 'value')

    return db_list

count_display = widgets.Label(value='Deck / Fusion counts will be displayed here.')

def update_deck_and_fusion_counts():
    global count_display
    # Ensure we are querying the right database based on the selected username
    db_manager = global_vars.myDB
    deck_count = db_manager.count_documents('Deck', {})
    fusion_count = db_manager.count_documents('Fusion', {})
    
    # Update the display widget with the new counts
    if count_display:
        count_display.value = f"Decks: {deck_count}, Fusions: {fusion_count}"
    else:
        print(f"Decks: {deck_count}, Fusions: {fusion_count}")

############################
# Setup and Initialization #
############################
import json
def setup_interface():
    global db_list, button_load, card_title_widget, grid_manager, central_frame_output
    
    for i in range(2):            
        factionToggle, dropdown = initialize_widgets()
        factionToggles.append(factionToggle)
        dropdowns.append(dropdown)

    # Button to create network graph
    button_graph = widgets.Button(description='Show Graph')
    button_graph.on_click(lambda button: display_graph_on_click(button))

    # Toggle buttons to select load items
    loadToggle = widgets.ToggleButtons(
        options=['Load Decks/Fusions', 'Create all Fusions'],
        description='Action:',
        disabled=False,
        button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
        tooltips=['Load Decks and Fusions from the website', 'Create Fusions from loaded decks'])

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
    
    # Create an instance of the manager
    grid_manager = DynamicGridManager(generate_central_dataframe, qg_options, out_debug)

    # Update the filter grid on db change
    db_list.observe(grid_manager.filterGridObject.update_selection_content, names='value')

    templateGrid = TemplateGrid()

    # Create the Tab widget with children
    db_tab   = widgets.VBox([loadToggle, button_load, count_display, username_widget, db_list])
    deck_tab = widgets.VBox([grid_manager.get_ui()])  # , qm_gridbox])
    fusions_tab = widgets.VBox([*toggle_dropdown_pairs,button_graph])
    debug_tab = widgets.VBox([debug_toggle, out_debug])
    template_tab = widgets.VBox([templateGrid.qgrid_filter])
    central_frame_tab = widgets.VBox([central_frame_output])

    tab = widgets.Tab(children=[db_tab, deck_tab, template_tab, fusions_tab, debug_tab, central_frame_tab])
    tab.set_title(0, 'Database')
    tab.set_title(1, 'Decks')
    tab.set_title(2, 'Templates')
    tab.set_title(3, 'Graphs')
    tab.set_title(4, 'Debug')
    tab.set_title(5, 'CentralDataframe')

    tab.selected_index = 0
    display(tab)

    #global_vars.tqdmBar = tqdm(total=100, desc='Loading...', bar_format='{desc}: {percentage:3.0f}% {bar}')
    
    # Display the Tab widget
    #display(global_vars.intProgressBar)
