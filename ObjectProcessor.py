import logging
import utils
from MyGraph import MyGraph
from DBQueryHelper import fetch_filtered_documents
from GlobalVariables import global_vars as gv
from MongoDB.DatabaseManager import DatabaseManager
from utils import compare_times, get_min_time, normalize_time_string

from CardLibrary import Forgeborn, ForgebornData, Fusion # Ensure proper imports

DECKBASICS  = ['type', 'name', 'cardIds']
DECKSTATS   = ['Creatures', 'Spells', 'Exalt']
DECKAVGS    = ['A1', 'A2', 'A3', 'H1', 'H2', 'H3']
DECKDATES   = ['digital','cardSetNo' ,'pExpiry']

DECKPROJECTION = DECKBASICS + DECKSTATS + DECKAVGS + DECKDATES

class ObjectProcessor:
    @staticmethod
    def process_object_for_db(object):
        """
        Fully processes a Deck or Fusion object before storing it in the database.
        """
        decks_data = None        
        if isinstance(object, Fusion) and object.myDecks:
            deck_names = [deck['name'] for deck in object.myDecks if 'name' in deck]
            if not deck_names:
                print(f"No names from object: {object.name}")
            #deck_names_from_list = [name for name in object.myDecks]
            #if deck_names_from_list: 
            #    
            #deck_names = deck_names_from_dict or deck_names_from_list
                        
            decks_data = list(fetch_filtered_documents(
                'Deck', 
                filter_query = {'name': {'$in': deck_names }},
                projection_fields= DECKPROJECTION,
            ))
            cardIds = [card_id for deck in decks_data if 'cardIds' in deck for card_id in deck['cardIds']]
        else:
            cardIds = object.cardIds
                                
        # Create the graph for the object 
        object_graph = ObjectProcessor.create_graph_for_object(object)
        object.data.CardTitles = ';'.join(object_graph.get_card_list())
        
        # Get the card data for the deck        
        cards = gv.myDB.find('Card', {'_id': {'$in': cardIds}})
        ObjectProcessor.process_betrayers_and_solbinds(object, list(cards))
        ObjectProcessor.process_object_stats(object, decks_data)
        ObjectProcessor.process_object_fb_abilities(object)
        ObjectProcessor.process_object_field_formats(object)
        
        if decks_data:           
           for deck_data in decks_data:                         
                ObjectProcessor.update_object_data(object, deck_data)
        
        ObjectProcessor.process_graph_statistics(object)
    
    @staticmethod
    def process_graph_statistics(object): 
        
        myGraph = MyGraph()
        myGraph.from_dict(object.graph)
        interface_ids = myGraph.get_length_interface_ids()

        combo_data = utils.get_combos_for_graph(myGraph, object.name)
        interface_ids = {**interface_ids, **combo_data}
        object.data.FrameData = interface_ids
    
    @staticmethod
    def process_betrayers_and_solbinds(object, cards):
        betrayers = []
        solbinds = {}

        for card in cards:
            if not card:
                continue
            crossFaction = card.get('crossFaction', None)
            faction = card.get('faction', None)
            if card.get('rarity') == 'Solbind':
                solbinds['Solbind'] = card['name']
                for solbind_field in ['solbindId1', 'solbindId2']:
                    solbind_card_id = card.get(solbind_field, None)
                    if solbind_card_id:
                        solbind_card_id = solbind_card_id[5:]
                        solbind_card = gv.myDB.find_one('Card', {'_id': solbind_card_id})
                        solbinds[solbind_field] = solbind_card['name'] if solbind_card else solbind_card_id
                        
            betrayer = card.get('betrayer', None)

            # Normalize betrayer values
            if isinstance(betrayer, str):
                betrayer = betrayer.strip().lower()
                if betrayer == "false":
                    betrayer = False
                elif betrayer == "true":
                    betrayer = True
                elif betrayer == "":  
                    betrayer = None

            crossFaction_betrayer = bool(crossFaction) and crossFaction != faction

            if betrayer is not None:
                if betrayer:  
                    betrayers.append(card['name'])
            elif crossFaction_betrayer:
                betrayers.append(card['name'])

        object.data.Betrayers = ', '.join(betrayers)
        object.data.SolBinds  = ', '.join(solbinds.get(k, '') for k in ['Solbind', 'solbindId1', 'solbindId2'] if k in solbinds)

    @staticmethod
    def process_object_stats(object, decks_data=None):
        if isinstance(object, Fusion):
            if decks_data:             
                items = ['Creatures', 'Spells', 'Exalt']            
                for item in items:
                    setattr(object.data, item, sum(deck[item] for deck in decks_data))                
                
                items = ['A1', 'A2', 'A3', 'H1', 'H2', 'H3']
                for item in items:                
                    setattr(object.data, item, round(sum(deck[item] for deck in decks_data) / len(decks_data),2))            
            else:
                logging.warning(f"No deck data found for Fusion: {object.name}")
                            
        else:
            stats = object.data.stats
            object.data.Creatures = stats['card_types']['Creature']['count']
            object.data.Spells = stats['card_types']['Spell']['count']
            if object.data.Spells and 'Exalt' in stats['card_types']['Spell']:
                object.data.Exalt = stats['card_types']['Spell']['Exalt']
            
            for item, prefix in [('attack', 'A'), ('health', 'H')]:
                for i in range(1, 4):  # Loop directly over 1, 2, 3
                    setattr(object.data, f"{prefix}{i}", stats['creature_averages'][item][str(i)])
            # object.data.A1  = stats['creature_averages']['attack']['1']
            # object.data.A2  = stats['creature_averages']['attack']['2']
            # object.data.A3  = stats['creature_averages']['attack']['3']
            # object.data.H1  = stats['creature_averages']['health']['1']
            # object.data.H2  = stats['creature_averages']['health']['2']
            # object.data.H3  = stats['creature_averages']['health']['3']
    
    @staticmethod
    def process_object_fb_abilities(object):
        """
        Processes Forgeborn abilities for a given deck and updates the DataFrame.

        Args:
            deck_object (object): The deck object containing Forgeborn IDs.
        """
        object_name = object.name
                
        forgeborn_ids = object.ForgebornIds if isinstance(object, Fusion) else [object.forgebornId]

        if not forgeborn_ids:
            logging.warning(f"No Forgeborn ID found for deck: {object_name}")
            return
        
        # Determine Forgeborn Name 
        currentForgebornId = forgeborn_ids[0]
        object.data.Forgeborn= currentForgebornId[5:-3].capitalize() if currentForgebornId else None

        forgeborn_ability_texts = {}
        inspired_ability_cycle = None

        try:
            common_db = DatabaseManager('common')

            for index, forgeborn_id in enumerate(forgeborn_ids, start=1):
                normalized_id = forgeborn_id[:-3]
                if normalized_id.startswith('a'):
                    normalized_id = 's' + normalized_id[1:]

                # Fetch Forgeborn data from the database
                forgeborn_data = common_db.find_one('Forgeborn', {'id': normalized_id})
                if not forgeborn_data:
                    logging.error(f"No data found for Forgeborn ID: {normalized_id}")
                    continue

                fb_data = ForgebornData(**forgeborn_data)
                forgeborn = Forgeborn(data=fb_data)
                unique_forgeborn = forgeborn.get_permutation(forgeborn_id)
                forgeborn_abilities = unique_forgeborn.abilities

                for ability_id, ability_name in forgeborn_abilities.items():
                    cycle = ability_id[-3]

                    # Detect inspired ability
                    if index == 1 and 'Inspire' in ability_name:
                        inspired_ability_cycle = cycle

                    # Apply inspire label if applicable
                    if index == 2 and cycle == inspired_ability_cycle:
                        ability_name += " (Inspire)"

                    # Store ability in the dictionary
                    if index == 1 or cycle == inspired_ability_cycle:
                        forgeborn_ability_texts[cycle] = ability_name                

        except Exception as e:
            logging.error(f"Error processing Forgeborn for deck '{object_name}': {e}")
        
        for cycle, ability in forgeborn_ability_texts.items():
            setattr(object.data, f'FB{cycle}', ability)
            
    @staticmethod
    def process_object_field_formats(object):
        for item in ['elo', 'xp', 'deckScore']:
            value = getattr(object.data, item, None)
            if value:
                setattr(object.data, item, round(float(value), 2))
        
        for item in ['registeredDate', 'UpdatedAt', 'CreatedAt', 'pExpiry']: 
            value = getattr(object.data, item, None)
            if value: 
                setattr(object.data, item, normalize_time_string(value, cutoff='milliseconds'))
            
    @staticmethod
    def update_object_data(object, deck_data=None):
        # Initialize 'digital' as a set if not already present

        if deck_data:
            digital = deck_data.get('digital', 0)
            cardSetNo = deck_data.get('cardSetNo', None)
            p_expiry = deck_data.get('pExpiry', '')
            deck_name = deck_data.get('name', None)
            if not object.data.faction:
                object.data.faction = deck_data.get('faction', None)
        else:
            digital = object.data.digital 
            cardSetNo = object.data.cardSetNo
            p_expiry = object.data.pExpiry 
    
        if deck_name:
            if not isinstance(object.data.myDecks, list):
                object.data.myDecks = []  # Ensure it's a list

            # Check if a dictionary with 'name' equal to deck_name already exists
            if not any(deck.get("name") == deck_name for deck in object.data.myDecks):
                object.data.myDecks.append({"name": deck_name})  # Append as a dictionary            
            
        if digital == '': digital = 0

        # Ensure object.digital behaves like a set but stores as a list
        if not hasattr(object.data, 'digital') or not isinstance(object.data.digital, list):
            object.data.digital = []
        object.data.digital = list(set(object.data.digital) | {int(digital)})

        # Ensure object.cardSetNo behaves like a set but stores as a list
        if not hasattr(object.data, 'cardSetNo') or not isinstance(object.data.cardSetNo, list):
            object.cardSetNo = []
        object.data.cardSetNo = list(set(object.data.cardSetNo) | {int(cardSetNo)}) if cardSetNo else object.data.cardSetNo
        
        if not hasattr(object.data, 'pExpiry'):
            object.data.pExpiry = p_expiry
            # Compare the expiration dates and keep the earliest one            
        object.data.pExpiry = get_min_time([object.data.pExpiry, p_expiry]) 
        
        
    @staticmethod        
    def create_graph_for_object(object):
        # Graph creation
        try:
            objectGraph = MyGraph()
            objectGraph.create_graph_children(object)
            object.data.node_data = objectGraph.node_data
            object.data.combo_data = objectGraph.combo_data
            
            # Convert the graph to a dictionary
            objectGraphDict = objectGraph.to_dict()
            object.data.graph = objectGraphDict
            
            logging.debug(f"Graph created for object: {object}.")
            return objectGraph
        
        except Exception as e:
            logging.error(f"Error creating graph for object: {e}")
            raise
            
        