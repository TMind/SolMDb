import pandas as pd
import logging, re
from utils import normalize_time_string
from GlobalVariables import GLOBAL_COLUMN_ORDER, global_vars as gv
from MyGraph import MyGraph
from MongoDB.DatabaseManager import DatabaseManager
from CardLibrary import Forgeborn, ForgebornData
import utils

class DataFrameGenerator:
    def __init__(self):
        pass
 
    def generate_central_dataframe(self, tasks=None, filter_df=None):
        if tasks is None:
            tasks = ['deck_stats', 'card_type_counts', 'fusion_stats']

        identifier = 'Central DataFrame'
        gv.progress_manager.update_progress(identifier, total=len(tasks) + 1, message='Generating Central Dataframe...')

        central_df = None

        if 'deck_stats' in tasks:
            gv.progress_manager.update_progress(identifier, message='Generating Deck Statistics Dataframe...')
            deck_stats_df = self.generate_deck_statistics_dataframe(filter_df)
            central_df = deck_stats_df
            utils.validate_dataframe_attributes(central_df, 'deck_stats')

        if 'card_type_counts' in tasks:
            gv.progress_manager.update_progress(identifier, message='Generating Card Type Count Dataframe...')
            card_type_counts_df = self.generate_card_type_count_dataframe(filter_df)
            central_df = (card_type_counts_df if central_df is None 
                          else utils.merge_by_adding_columns(central_df, card_type_counts_df))
            utils.validate_dataframe_attributes(central_df, 'card_type_counts')

        if 'fusion_stats' in tasks:
            gv.progress_manager.update_progress(identifier, message='Generating Fusion Statistics Dataframe...')
            fusion_stats_df = self.generate_fusion_statistics_dataframe(central_df, filter_df)
            central_df = (fusion_stats_df if central_df is None 
                          else utils.merge_and_concat(central_df, fusion_stats_df))
            utils.validate_dataframe_attributes(central_df, 'fusion_stats')

        if central_df is not None:
            gv.progress_manager.update_progress(identifier, message='Cleaning Central Dataframe...')
            central_df = utils.clean_columns(central_df, exclude_columns=['deckScore', 'elo', 'price', 'Free'])
            central_df.reset_index(inplace=True)
            central_df.rename(columns={'name': 'Name'}, inplace=True)
            central_df = utils.enforce_column_order(central_df, GLOBAL_COLUMN_ORDER)
            utils.validate_dataframe_attributes(central_df, 'central_df')

        gv.progress_manager.update_progress(identifier, message='Central Dataframe Generated.')
        return central_df
 
 
    def generate_deck_statistics_dataframe(self, filter_df=None):
        
        # Fetch decks based on filter_df or all decks from the database
        decks = utils.fetch_data_from_db('Deck', filter_df=filter_df)
        if not decks:
            return pd.DataFrame()

        number_of_decks = len(decks)
        df_decks = pd.DataFrame(decks)

        # Select and preprocess relevant columns
        df_decks_filtered = df_decks[
            ['name', 'id', 'registeredDate', 'UpdatedAt', 'pExpiry', 'deckScore', 
            'deckRank', 'level', 'xp', 'elo', 'cardSetNo', 'digital', 'nft', 
            'price', 'owner', 'faction', 'forgebornId', 'CardTitles', 'graph']
        ].copy()
        df_decks_filtered['type'] = 'Deck'

        # Preprocess numeric and datetime columns
        df_decks_filtered['cardSetNo'] = pd.to_numeric(df_decks_filtered['cardSetNo'], errors='coerce').fillna(0).astype(int).replace(99, 0)
        df_decks_filtered['xp'] = df_decks_filtered['xp'].astype(int)
        df_decks_filtered['elo'] = pd.to_numeric(df_decks_filtered['elo'], errors='coerce').fillna(-1).round(2)
        df_decks_filtered['registeredDate'] = df_decks_filtered['registeredDate'].apply(
            lambda x: normalize_time_string(x, cutoff='milliseconds') if x else x)
        df_decks_filtered['UpdatedAt'] = df_decks_filtered['UpdatedAt'].apply(
            lambda x: normalize_time_string(x, cutoff='milliseconds') if x else x)
        df_decks_filtered['pExpiry'] = df_decks_filtered['pExpiry'].apply(
            lambda x: normalize_time_string(x, cutoff='hours') if x else x)

        # Add default values for additional columns
        additional_columns = {'Creatures': 0, 'Spells': 0, 'Exalt': 0, 'FB2': '', 'FB3': '', 'FB4': '', 
                            'A1': 0.0, 'H1': 0.0, 'A2': 0.0, 'H2': 0.0, 'A3': 0.0, 'H3': 0.0}
        for column, default_value in additional_columns.items():
            df_decks_filtered[column] = default_value

        # Set the index to the 'name' column
        df_decks_filtered.set_index('name', inplace=True)

        # Initialize progress tracking
        identifier = 'Stats Data'
        gv.progress_manager.update_progress(identifier, 0, number_of_decks, message='Generating Statistics Data...')

        # Process individual deck data
        df_list = []
        for deck in decks:
            gv.progress_manager.update_progress(identifier, message=f'Processing Deck Stats: {deck["name"]}')
            
            # Process Forgeborn data
            deck_name = deck['name']
            forgeborn_id = deck['forgebornId']
            replace_forgeborn_id, forgeborn_ability_texts = self.process_deck_forgeborn(deck_name, forgeborn_id, [forgeborn_id])
            df_decks_filtered.loc[deck_name, 'forgebornId'] = replace_forgeborn_id
            for cycle, ability in forgeborn_ability_texts.items():
                df_decks_filtered.loc[deck_name, f'FB{cycle}'] = ability

            # Fetch and process cards
            cards = gv.myDB.find('Card', {'_id': {'$in': deck['cardIds']}}) if gv.myDB else []
            betrayers = []
            solbinds = {}

            for card in cards:
                if not card:
                    continue
                crossfaction = card.get('crossfaction') or card.get('crossFaction')
                faction = deck.get('faction')
                if card.get('rarity') == 'Solbind':
                    solbinds['Solbind'] = card['name']
                    for solbind_field in ['solbindId1', 'solbindId2']:
                        solbind_card_id = card.get(solbind_field, None)
                        if solbind_card_id:
                            solbind_card_id = solbind_card_id[5:]
                            solbind_card = gv.myDB.find_one('Card', {'_id': solbind_card_id})
                            solbinds[solbind_field] = solbind_card['name'] if solbind_card else solbind_card_id
                if crossfaction and crossfaction != faction or card.get('betrayer') in [True, 'True']:
                    betrayers.append(card['name'])

            df_decks_filtered.loc[deck_name, 'Betrayers'] = ', '.join(betrayers)
            df_decks_filtered.loc[deck_name, 'SolBinds'] = ', '.join(solbinds.get(k, '') for k in ['Solbind', 'solbindId1', 'solbindId2'] if k in solbinds)

            # Process stats
            if 'stats' in deck:
                stats = deck['stats']
                card_type_counts = {'Creatures': stats['card_types']['Creature']['count'], 'Spells': stats['card_types']['Spell']['count']}
                if 'Exalt Type' in stats['card_types']['Spell']:
                    card_type_counts['Exalt'] = stats['card_types']['Spell']['Exalt Type']
                attack_df = pd.DataFrame([stats['creature_averages']['attack']], index=[deck_name])
                defense_df = pd.DataFrame([stats['creature_averages']['health']], index=[deck_name])
                attack_df.columns = ['A1', 'A2', 'A3']
                defense_df.columns = ['H1', 'H2', 'H3']
                df_list.append(pd.concat([pd.DataFrame([card_type_counts], index=[deck_name]), attack_df, defense_df], axis=1))

        # Merge all processed data
        if df_list:
            df_decks_list = pd.concat(df_list, axis=0)
            df_decks_filtered.update(df_decks_list)

        return df_decks_filtered

    def process_deck_forgeborn(self, item_name, current_forgeborn_id, forgeborn_ids):
        """
        Processes the Forgeborn information for a given deck or fusion.

        Args:
            item_name (str): Name of the deck or fusion.
            current_forgeborn_id (str): The primary Forgeborn ID.
            forgeborn_ids (list): List of fallback Forgeborn IDs.

        Returns:
            tuple: (final_forgeborn_id, ability_texts_dict), where:
                - final_forgeborn_id: The updated Forgeborn ID after validation.
                - ability_texts_dict: A dictionary of cycle-to-ability mappings.
        """
        try:
            forgeborn_counter = 0
            inspired_ability_cycle = None
            forgeborn_ability_texts = {}
            replace_forgeborn_id = ''

            for forgeborn_id in forgeborn_ids:
                forgeborn_counter += 1
                # Normalize Forgeborn ID
                normalized_id = forgeborn_id[:-3]
                if normalized_id.startswith('a'):
                    normalized_id = 's' + normalized_id[1:]

                # Fetch Forgeborn data from the database
                common_db = DatabaseManager('common')
                forgeborn_data = common_db.find_one('Forgeborn', {'id': normalized_id})
                if forgeborn_data is None:
                    logging.error(f'No data found for Forgeborn ID: {normalized_id}')
                    return current_forgeborn_id.title(), {}

                fb_data = ForgebornData(**forgeborn_data)
                forgeborn = Forgeborn(data=fb_data)
                unique_forgeborn = forgeborn.get_permutation(forgeborn_id)
                forgeborn_abilities = unique_forgeborn.abilities

                if forgeborn_abilities:
                    for ability_id, ability_name in forgeborn_abilities.items():
                        cycle = ability_id[-3]

                        # Check if the ability is inspired
                        if forgeborn_counter == 1 and 'Inspire' in ability_name:
                            inspired_ability_cycle = cycle

                        # Apply the inspired label if necessary
                        if forgeborn_counter == 2 and cycle == inspired_ability_cycle:
                            ability_name += " (Inspire)"

                        # Update the ability texts dictionary
                        if forgeborn_counter == 1 or cycle == inspired_ability_cycle:
                            forgeborn_ability_texts[cycle] = ability_name

                # Update the Forgeborn ID
                replace_forgeborn_id = current_forgeborn_id[5:-3].title()

        except KeyError as e:
            logging.error(f"KeyError while processing Forgeborn: {e} (Item: {item_name}, Forgeborn IDs: {forgeborn_ids})")
        except Exception as e:
            logging.error(f"Unexpected error while processing Forgeborn: {e} (Item: {item_name}, Forgeborn IDs: {forgeborn_ids})")

        # Log an error if no valid Forgeborn ID was found
        if not replace_forgeborn_id:
            logging.error(f"No Forgeborn ID found for {item_name}")

        return replace_forgeborn_id, forgeborn_ability_texts

    # def process_fusion(self, fusion_row, central_df):
    #     """
    #     Processes a single fusion row to calculate interface IDs and combo data.
    #     Updates Forgeborn IDs and ability texts for the fusion.
    #     """
    #     fusion_name = fusion_row['name']
        
    #     # Process Forgeborn data
    #     replace_forgebornId, forgeborn_ability_texts = self.process_deck_forgeborn(
    #         fusion_name, fusion_row['forgebornId'], getattr(fusion_row, 'ForgebornIds', [])
    #     )
    #     fusion_row['forgebornId'] = replace_forgebornId

    #     for cycle, ability in forgeborn_ability_texts.items():
    #         fusion_row[f'FB{cycle}'] = ability

    #     # Extract decks from children data
    #     decks = self.get_items_from_child_data(fusion_row['children_data'], 'CardLibrary.Deck')
    #     if len(decks) > 1:
    #         fusion_row['Deck A'] = decks[0]
    #         fusion_row['Deck B'] = decks[1]

    #     # Update fusion statistics based on central_df
    #     if central_df is not None:
    #         for deck in ['Deck A', 'Deck B']:
    #             deck_name = fusion_row.get(deck, '')
    #             if deck_name and deck_name in central_df.index:
    #                 deck_row = central_df.loc[deck_name]

    #                 # Combine values for 'digital', 'cardSetNo', etc.
    #                 digital = deck_row.get('digital', '?')
    #                 digital = 0 if digital == "0" else 1 if digital == "1" else 0
    #                 fusion_row['digital'] = (
    #                     f"{fusion_row.get('digital', '')}, {digital}".strip(", ")
    #                 )

    #                 cardSetNo = deck_row.get('cardSetNo', None)
    #                 if cardSetNo:
    #                     fusion_row['cardSetNo'] = (
    #                         f"{fusion_row.get('cardSetNo', '')}, {cardSetNo}".strip(", ")
    #                     )

    #                 for item in ['Creatures', 'Spells', 'Exalt']:
    #                     fusion_row[item] = fusion_row.get(item, 0) + deck_row.get(item, 0)

    #                 betrayers = deck_row.get('Betrayers', '')
    #                 fusion_row['Betrayers'] = (
    #                     f"{fusion_row.get('Betrayers', '')}, {betrayers}".strip(", ")
    #                 )

    #                 solbinds = deck_row.get('SolBinds', '')
    #                 fusion_row['SolBinds'] = (
    #                     f"{fusion_row.get('SolBinds', '')}, {solbinds}".strip(", ")
    #                 )

    #                 pExpiry = deck_row.get('pExpiry', '')
    #                 fusion_row['pExpiry'] = (
    #                     f"{fusion_row.get('pExpiry', '')}, {pExpiry}".strip(", ")
    #                 )

    #     # Generate graph and combo data
    #     myGraph = MyGraph()
    #     myGraph.from_dict(fusion_row['graph'])
    #     interface_ids = myGraph.get_length_interface_ids()
    #     combo_data = utils.get_combos_for_graph(myGraph, fusion_name)
    #     interface_ids = {**interface_ids, **combo_data}

    #     # Convert interface IDs to DataFrame and return
    #     interface_ids_df = pd.DataFrame([interface_ids], index=[fusion_name])
    #     return fusion_row, interface_ids_df


    def update_fusion_with_deck_data(self, fusion_row, deck_row, deck_key):
        """
        Updates the fusion_row with data from the corresponding deck_row.

        Args:
            fusion_row (pd.Series): The current fusion row being processed.
            deck_row (pd.Series): The corresponding deck row from central_df.
            deck_key (str): The deck key ('Deck A' or 'Deck B').
        """
        # Get the digital value and ensure it's converted to an integer
        digital = deck_row.get('digital', '?')
        if digital == "0":
            digital = 0
        elif digital == "1":
            digital = 1
        elif digital == "":
            digital = 0

        # Initialize 'digital' as a set if not already present
        if 'digital' not in fusion_row or not isinstance(fusion_row['digital'], set):
            fusion_row['digital'] = set()
        fusion_row['digital'].add(int(digital))

        # Initialize 'cardSetNo' as a set if not already present
        cardSetNo = deck_row.get('cardSetNo', None)
        if cardSetNo:
            if 'cardSetNo' not in fusion_row or not isinstance(fusion_row['cardSetNo'], set):
                fusion_row['cardSetNo'] = set()
            fusion_row['cardSetNo'].add(cardSetNo)

        # Update counts for Creatures, Spells, and Exalt
        for item in ['Creatures', 'Spells', 'Exalt']:
            count = deck_row.get(item, 0)
            if item not in fusion_row:
                fusion_row[item] = 0
            fusion_row[item] += count

        # Update Betrayers
        betrayers = deck_row.get('Betrayers', '')
        if betrayers:
            if 'Betrayers' not in fusion_row:
                fusion_row['Betrayers'] = []
            fusion_row['Betrayers'].append(betrayers)

        # Update SolBinds
        solbinds = deck_row.get('SolBinds', '')
        if solbinds:
            if 'SolBinds' not in fusion_row:
                fusion_row['SolBinds'] = []
            fusion_row['SolBinds'].append(solbinds)

        # Update pExpiry
        p_expiry = deck_row.get('pExpiry', '')
        if p_expiry:
            if 'pExpiry' not in fusion_row:
                fusion_row['pExpiry'] = []
            fusion_row['pExpiry'].append(p_expiry)


    def generate_fusion_statistics_dataframe(self, central_df=None, filter_df=None):
        """
        Generates a DataFrame with fusion statistics.

        Args:
            central_df (pd.DataFrame): The central DataFrame containing deck data.
            filter_df (pd.DataFrame): Optional filter DataFrame to limit fusions.

        Returns:
            pd.DataFrame: The fusion statistics DataFrame.
        """
        # Fetch fusion data from the database
        fusions = utils.fetch_data_from_db('Fusion', filter_df=filter_df, projection={
            'name': 1, 'currentForgebornId': 1, 'ForgebornIds' : 1, 'children_data': 1, 'graph': 1
        })
        if not fusions:
            return pd.DataFrame()

        # Create DataFrame for fusions
        df_fusions = pd.DataFrame(fusions)
        df_fusions['forgebornId'] = df_fusions['currentForgebornId']
        df_fusions['type'] = 'Fusion'

        # Ensure 'name' is set as the index
        if 'name' in df_fusions.columns:
            df_fusions.set_index('name', inplace=True)
        else:
            raise ValueError("Fusion data is missing the 'name' column.")

        all_interface_ids_df_list = []

        # Iterate through fusions to process each row
        for _, fusion_row in df_fusions.iterrows():
            fusion_name = fusion_row.name

            # Process Forgeborn data
            replace_forgebornId, forgeborn_ability_texts = self.process_deck_forgeborn(
                fusion_name, fusion_row['forgebornId'], getattr(fusion_row, 'ForgebornIds', [])
            )
            fusion_row['forgebornId'] = replace_forgebornId
            for cycle, ability in forgeborn_ability_texts.items():
                fusion_row[f'FB{cycle}'] = ability

            # Extract decks from children data
            decks = self.get_items_from_child_data(fusion_row['children_data'], 'CardLibrary.Deck')
            if len(decks) > 1:
                fusion_row['Deck A'] = decks[0]
                fusion_row['Deck B'] = decks[1]

            # Combine deck values from central_df
            for deck_key in ['Deck A', 'Deck B']:
                deck_name = fusion_row.get(deck_key, None)
                if deck_name and central_df is not None:
                    deck_row = central_df.loc[deck_name] if deck_name in central_df.index else None
                    if deck_row is not None:
                        self.update_fusion_with_deck_data(fusion_row, deck_row, deck_key)
                    else:
                        print(f"Deck '{deck_name}' not found in central DataFrame for fusion '{fusion_name}'.")

            # Generate graph data for the fusion
            myGraph = MyGraph()
            myGraph.from_dict(fusion_row['graph'])
            interface_ids = myGraph.get_length_interface_ids()
            combo_data = utils.get_combos_for_graph(myGraph, fusion_name)
            interface_ids = {**interface_ids, **combo_data}

            # Create a DataFrame for interface IDs
            interface_ids_df = pd.DataFrame([interface_ids], index=[fusion_name])
            all_interface_ids_df_list.append(interface_ids_df)

        # Combine all interface ID DataFrames
        if all_interface_ids_df_list:
            interface_ids_total_df = pd.concat(all_interface_ids_df_list)
            # df_fusions = pd.merge(
            #     df_fusions, interface_ids_total_df, left_index=True, right_index=True, how='left'
            # )
            
             # Ensure no overlap of columns with the index
            interface_ids_total_df.index.name = 'name'
            df_fusions = pd.merge(
                df_fusions.reset_index(), interface_ids_total_df, left_on='name', right_index=True, how='left'
            )
            df_fusions.set_index('name', inplace=True)

        # Clean and reorder columns
        df_fusions = utils.clean_columns(df_fusions)
        df_fusions = utils.enforce_column_order(df_fusions, GLOBAL_COLUMN_ORDER)

        return df_fusions

    def get_items_from_child_data(self, children_data, item_type):
        # Children data is a dictionary that contains the deck names as keys, where the value is the object type CardLibrary.Deck
        item_names = [name for name, data_type in children_data.items() if data_type == item_type]
        return item_names


    def generate_card_type_count_dataframe(self, filter_df=None):
        identifier = 'CardType Count Data'
        deck_list = utils.fetch_data_from_db('Deck', filter_df=filter_df)
        if not deck_list:
            return pd.DataFrame()

        gv.progress_manager.update_progress(identifier, 0, len(deck_list), message='Generating CardType Count Data...')
        all_decks_list = []

        for deck in deck_list:
            gv.progress_manager.update_progress(identifier, message=f'Processing Deck: {deck["name"]}')

            myGraph = MyGraph()
            myGraph.from_dict(deck.get('graph', {}))
            interface_ids = myGraph.get_length_interface_ids()

            combo_data = utils.get_combos_for_graph(myGraph, deck['name'])
            interface_ids = {**interface_ids, **combo_data}

            interface_ids_df = pd.DataFrame([interface_ids], index=[deck['name']])

            if 'stats' in deck and 'card_types' in deck['stats']:
                cardType_df = pd.DataFrame(deck['stats']['card_types'].get('Creature', {}), index=[deck['name']])
                if not cardType_df.index.equals(interface_ids_df.index):
                    cardType_df = cardType_df.reindex(interface_ids_df.index)
                combined_df = cardType_df.combine_first(interface_ids_df)
                all_decks_list.append(combined_df)
            else:
                all_decks_list.append(interface_ids_df)

        if all_decks_list:
            all_columns = set()
            for df in all_decks_list:
                all_columns.update(df.columns)

            all_decks_list = [df.reindex(columns=all_columns, fill_value='') for df in all_decks_list]
            all_decks_df = pd.concat(all_decks_list, axis=0, sort=False)

            if 'name' in all_decks_df.columns:
                all_decks_df.set_index('name', inplace=True)

            all_decks_df.sort_index(axis=1, inplace=True)
            all_decks_df = utils.sum_card_types(all_decks_df)
            all_decks_df = utils.clean_columns(all_decks_df)
            result_df = utils.enforce_column_order(all_decks_df, GLOBAL_COLUMN_ORDER)

            return result_df
        else:
            print('No decks found in the database')
            return pd.DataFrame()


    def generate_deck_content_dataframe(self, deckNames):
        from CardLibrary import Card , CardData
        
        # Get the data set from the global variables
        #desired_fields = gv.data_selection_sets['Deck Content']
        desired_fields = {
            'name': True,
            'faction': True,
            'rarity': True,
            'cardType': True,
            'cardSubType': True,
        }

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
            final_df = utils.enforce_column_order(final_df, GLOBAL_COLUMN_ORDER)
            return utils.clean_columns(final_df)
        else:
            print(f'No cards found in the database for {deckNames}')
            return pd.DataFrame()

    def generate_combo_dataframe(self, df=None):
        if df is None:
            items = {'Deck': [], 'Fusion': []}
            if gv.myDB:
                for item_type in items.keys():
                    items[item_type] = [
                        {'name': item['name'], 'graph': item.get('graph', {})}
                        for item in gv.myDB.find(item_type, {}, {'name': 1, 'graph': 1})
                    ]

            data = [{'name': item['name'], 'graph': item['graph'], 'type': item_type}
                    for item_type, item_list in items.items() for item in item_list]
            df = pd.DataFrame(data)

        combos_list = []
        gv.progress_manager.update_progress(f'Combo Data', 0, len(df), message='Generating Combo Data...')
        for _, item in df.iterrows():
            gv.progress_manager.update_progress('Combo Data', message=f'Generating Combo Data for {item["name"]}')
            myGraph = MyGraph()
            myGraph.from_dict(item['graph'])
            combo_data = utils.get_combos_for_graph(myGraph, item['name'])
            combos_list.append(combo_data)

        combos_df = pd.DataFrame(combos_list)
        result_df = pd.merge(df, combos_df, on='name', how='left')
        result_df = utils.clean_columns(result_df)

        return result_df

   
