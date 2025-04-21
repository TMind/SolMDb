import os
import CardLibrary
from MongoDB.DatabaseManager import DatabaseManager, BufferManager
from CardLibrary import  Fusion, Deck, Card#, ForgebornData, Forgeborn
from MultiProcess import MultiProcess
from GlobalVariables import global_vars as gv
from ObjectProcessor import ObjectProcessor
import logging

from utils import compare_times, get_min_time, normalize_time_string
from itertools import product

# def create_graph_for_object(object):
#     # Graph creation
#     objectGraph = MyGraph()
#     objectGraph.create_graph_children(object)
#     object.data.node_data = objectGraph.node_data
#     object.data.combo_data = objectGraph.combo_data
    
#     # Convert the graph to a dictionary
#     objectGraphDict = objectGraph.to_dict()
#     object.data.graph = objectGraphDict
    
#     return objectGraph

class DeckLibrary:
    def __init__(self, decks_data, fusions_data, mode):                
        
        # Initialize Universal Library 
        self.universal_library = gv.get_universal_library()
        
        def extract_card_data_from_entity(entity, id):
            card_data = {'_id': id}

            if entity.data:
                if entity.data.name:
                    card_data['name'] = entity.data.name
                    card_data['title'] = entity.data.name
                if entity.data.faction:
                    card_data['faction'] = entity.data.faction
                if 'cardType' in entity.data.attributes:
                    card_data['cardType'] = entity.data.attributes.get('cardType', '')
                if 'cardSubType' in entity.data.attributes:
                    card_data['cardSubType'] = entity.data.attributes.get('cardSubType', '')
                if 'betrayer' in entity.data.attributes:
                    card_data['betrayer'] = entity.data.attributes.get('betrayer', False)
                if hasattr(entity.data, 'solbindId1') and entity.data.solbindId1:
                    card_data['solbindId1'] = entity.data.solbindId1
                if hasattr(entity.data, 'solbindId2') and entity.data.solbindId2:
                    card_data['solbindId2'] = entity.data.solbindId2
                if hasattr(entity.data, 'sortValue') and entity.data.sortValue:
                    card_data['sortValue'] = entity.data.sortValue
                if 'crossFaction' in entity.data.attributes:
                    card_data['crossFaction'] = entity.data.attributes.get('crossFaction', '')
                if hasattr(entity.data, 'cardSetId') and entity.data.cardSetId:
                    card_data['cardSetId'] = entity.data.cardSetId
                if hasattr(entity.data, '_id') and entity.data._id:
                    card_data['_id'] = entity.data._id
                if 'rarity' in entity.data.attributes:
                    card_data['rarity'] = entity.data.attributes.get('rarity', '')
                if hasattr(entity.data, 'provides') and entity.data.provides:
                    card_data['provides'] = entity.data.provides
                if hasattr(entity.data, 'seeks') and entity.data.seeks:
                    card_data['seeks'] = entity.data.seeks
                if hasattr(entity.data, 'levels') and entity.data.levels:
                    card_data['levels'] = entity.data.levels
                if hasattr(entity.data, 'attack') and entity.data.attack:
                    card_data['attack'] = entity.data.attack
                if hasattr(entity.data, 'health') and entity.data.health:
                    card_data['health'] = entity.data.health
                if hasattr(entity.data, 'children_data') and entity.data.children_data:
                    card_data['children_data'] = entity.data.children_data

            else:
                print(f"Entity {entity} has no data.")
            
            return card_data

        
        self.dbmgr = DatabaseManager(gv.username)
        self.new_decks = []
        self.online_fusions = []
        
        if decks_data:            
                        
            #Default mode 'create'            
            deckNamesDatabase = []
            cardIdsDatabase = []
                
            if mode == 'update':
                deckCursor = self.dbmgr.find('Deck', {}, {'name': 1})                
                deckNamesDatabase = [deck['name'] for deck in deckCursor]
                                    
                cardListDatabase = self.dbmgr.find('Card', {})        
                cardIdsDatabase = [card['_id'] for card in cardListDatabase]

            deckDataList = []
            cardDataList = []
            deck_objects = []
            
            buffer_manager = BufferManager(os.getenv('MONGODB_URI', None))
            with buffer_manager: 
                gv.progress_manager.update_progress('DeckLibrary Decks', 0, len(decks_data), message='Saving Online Decks')
                for deckData in decks_data:
                    gv.progress_manager.update_progress('DeckLibrary Decks', message=f"Saving Deck {deckData['name']}")
                    deckName = deckData['name'] 
                    # Save only new decks
                    if deckName not in deckNamesDatabase:                         
                        self.new_decks.append(deckData)    
                        forgebornId = deckData.get('forgebornId', None)
                        forgeborn_index = 5
                        if forgebornId and 'blighted' in forgebornId:
                            # Find position of 'blighted' in the forgebornId
                            blighted_index = forgebornId.find('blighted')
                            forgebornId = forgebornId[:2] + forgebornId[blighted_index:]
                            forgeborn_index = 2
                            deckData['forgebornId'] = forgebornId
                            
                        deckData['Forgeborn'] = forgebornId[forgeborn_index:-3].capitalize() if forgebornId else None
                        
                        new_deck = Deck.from_data(deckData)
                        
                        if new_deck.children_data:
                            new_deck.children_data.update({new_deck.forgebornId : 'CardLibrary.Forgeborn'})
            
                        # Store the deck object for later use
                        deck_objects.append(new_deck)
                        
                        # Save all cards that are not already in the database
                        for index, card in new_deck.cards.items():                            
                            card_name = card['name'] if 'name' in card else card['title']                                                        
                            id = new_deck.cardIds[int(index)-1]    
                            if card['rarity'] == 'Solbind':
                                # Add Solbind Cards to the database as well
                                for solbindCard in ['solbindId1', 'solbindId2']:
                                    solbindId = card.get(solbindCard, None)
                                    if solbindId and solbindId[5:] not in cardIdsDatabase:                                        
                                        solbind_entity = CardLibrary.Entity.lookup(solbindId[5:])
                                        if solbind_entity:  
                                            solbind_data = extract_card_data_from_entity(solbind_entity, solbindId[5:])
                                            solbind_data['cardType'] = 'Solbind'
                                            cardDataList.append(solbind_data)
                                        else:
                                            print(f"Solbind card {solbindId} not found.")
                            if id not in cardIdsDatabase:
                                myCard = Card.from_data(card)                                                                                
                                myCard.data._id = id                            
                                cardDataList.append(myCard.to_data())
                        
                if cardDataList:                                                   
                    # Remove duplicate entries but keep the first one in the list
                    seen = set()
                    cardDataList = [x for x in cardDataList if x['_id'] not in seen and not seen.add(x['_id'])]
                    #cardDataList = [x for x in cardDataList if not (x['_id'] in seen or seen.add(x['_id']))]                                    
                    self.dbmgr.upsert_many('Card', cardDataList)

                # Prepare all deck data for upsert in a single operation
                gv.progress_manager.update_progress('DeckLibrary Graphs', 0, len(deck_objects), message='Creating Graphs for Decks')
                for deckObject in deck_objects:                    
                    gv.progress_manager.update_progress('DeckLibrary Graphs', message=f"Creating Graph for Deck {deckObject.name}")
                                                            
                    # Process the deck data for the database
                    ObjectProcessor.process_object_for_db(deckObject)
                                        
                    # Update the deck data with the graph and node data
                    deck_data = deckObject.to_data()
                    
                    # Collect the deck data for upserting
                    deckDataList.append(deck_data)

                if deckDataList:                 
                    result = self.dbmgr.upsert_many('Deck', deckDataList)                
                    print(f"Upserted {result} new decks.")

        # Print the betrayer statistics         
        print(gv.betrayer_statistics)

        if fusions_data:
            
            def extract_fb_ids_and_factions(my_decks, fusion_data):
                forgeborn_ids = []
                factions = []

                for deck in my_decks:
                    if isinstance(deck, dict):
                        # If deck is a dictionary, extract the forgeborn ID and faction
                        if 'forgeborn' in deck and isinstance(deck['forgeborn'], dict):
                            if 'id' in deck['forgeborn']:
                                forgeborn_ids.append(deck['forgeborn']['id'])
                        faction = deck.get('faction')
                        if faction:
                            factions.append(faction)

                return forgeborn_ids, factions

            gv.progress_manager.update_progress('DeckLibrary Fusions', 0, len(fusions_data), message='Saving Online Fusions')            
            for fusion_data in fusions_data:
                decks = fusion_data['myDecks']                      
                forgebornIds, factions = extract_fb_ids_and_factions(decks, fusion_data)
                fusion_data['ForgebornIds'] = forgebornIds
                fusion_data['faction'] = factions[0]
                fusion_data['crossFaction'] = factions[1]
                
                # Graph creation 
                fusionObject = Fusion.from_data(fusion_data)              
                ObjectProcessor.process_object_for_db(fusionObject)
                
                # Save the fusion to the database
                fusionObject.save()           
                self.online_fusions.append(fusion_data)                
                gv.progress_manager.update_progress('DeckLibrary Fusions', message=f"Saved Fusion {fusionObject.name}")
        
        # In creation mode we create fusions for all decks

        if mode =='fuse':
            #print('Creating fusions...')
            deckCursor = self.dbmgr.find('Deck', {}, {'name': 1})                
            self.new_decks = [deck for deck in deckCursor]             
            self.make_fusions()
          
    def make_fusions(self, deck_lists=None, ump=True):
        """
        Creates fusions from the given deck lists or from all decks in the database if no lists are provided.

        Args:
            deck_lists: List of lists containing deck names. If no lists are provided, all valid deck names are used.
        """
        # Fetch all deck data from the database
        deckCursor = self.dbmgr.find('Deck', {})
        allDeckData = {deck['name']: deck for deck in deckCursor}

        # Fetch all existing fusions from the database
        existing_fusions_cursor = self.dbmgr.find('Fusion', {}, projection=['myDecks'])

        # Extract deck name pairs from 'myDecks' field
        existing_fusions = {
            tuple(sorted(deck_obj["name"] for deck_obj in fusion["myDecks"] if "name" in deck_obj))
            for fusion in existing_fusions_cursor if "myDecks" in fusion and len(fusion["myDecks"]) == 2
        }

        # Filter out expired decks only if no lists are provided
        if not deck_lists:
            validDeckNames = [
                name for name, deck in allDeckData.items()
                if 'pExpiry' not in deck or compare_times(deck['pExpiry'], gv.current_date)
            ]
            deck_lists = [validDeckNames]
        else:
            validDeckNames = list(allDeckData.keys())

        # Handle case where only a single list is provided
        if len(deck_lists) == 1:
            single_list = deck_lists[0]
            newCombinations = [
                (deck_a, deck_b)
                for i, deck_a in enumerate(single_list)
                for j, deck_b in enumerate(single_list)
                if i != j and deck_a in validDeckNames and deck_b in validDeckNames
            ]
        else:
            # Generate combinations of decks from multiple lists, ensuring they come from different lists
            newCombinations = {
                (deck_a, deck_b)
                for i, deck_list_a in enumerate(deck_lists)
                for j, deck_list_b in enumerate(deck_lists)
                if i < j
                for deck_a in deck_list_a
                for deck_b in deck_list_b
                if deck_a in validDeckNames and deck_b in validDeckNames
            }

            reverse_pairs = False
            if reverse_pairs :
                # Add reverse pairs
                newCombinations |= {(b, a) for a, b in newCombinations}  

                # Convert back to a list
                newCombinations = list(newCombinations)

        # **Remove already existing fusions**
        newCombinations = [pair for pair in newCombinations if pair not in existing_fusions]

        # Replace newCombinationNames with the actual deck dictionaries
        deckCombinationData = []
        for combination in newCombinations:
            deckCombinationData.append([allDeckData[deckName] for deckName in combination])

        # Process all valid combinations using the MultiProcess module
        if deckCombinationData:
            multi_process = MultiProcess(gv.username, deckCombinationData)
            ump = multi_process.determine_required_cpus(len(deckCombinationData), min_items_per_cpu=1000) > 1
            multi_process.run(use_multiprocessing=ump)
            print(f"Processed {len(deckCombinationData)} fusions.")
        else:
            print("No valid fusions could be created.")