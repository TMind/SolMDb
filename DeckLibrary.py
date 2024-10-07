import os
import CardLibrary
from MyGraph import MyGraph
from MongoDB.DatabaseManager import DatabaseManager, BufferManager
from CardLibrary import  Fusion, Deck, Card
from MultiProcess import MultiProcess
from GlobalVariables import global_vars as gv
import networkx as nx

def create_graph_for_object(object):
    # Graph creation
    objectGraph = MyGraph()
    objectGraph.create_graph_children(object)
    object.data.node_data = objectGraph.node_data
    
    # Convert the graph to a dictionary
    objectGraphDict = objectGraph.to_dict()
    object.data.graph = objectGraphDict
    
    return object

class DeckLibrary:
    def __init__(self, decks_data, fusions_data, mode):                
        
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
                for deckData in decks_data:
                    deckName = deckData['name'] 
                    # Save only new decks
                    if deckName not in deckNamesDatabase:                         
                        self.new_decks.append(deckData)    
                        new_deck = Deck.from_data(deckData)
                        
                        if new_deck.children_data:
                            new_deck.children_data.update({new_deck.forgebornId : 'CardLibrary.Forgeborn'})
            
                        # Store the deck object for later use
                        deck_objects.append(new_deck)
                        
                        # Save all cards that are not already in the database
                        for index, card in new_deck.cards.items():
                            id = new_deck.cardIds[int(index)-1]    
                            if card['rarity'] == 'Solbind':
                                # Add Solbind Cards to the database as well
                                for solbindCard in ['solbindId1', 'solbindId2']:
                                    solbindId = card[solbindCard][5:]
                                    if solbindId and solbindId not in cardIdsDatabase:                                        
                                        solbind_entity = CardLibrary.Entity.lookup(solbindId)
                                        if solbind_entity:  
                                            solbind_data = extract_card_data_from_entity(solbind_entity, solbindId)
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
                for deckObject in deck_objects:
                    # Now create the graph since the cards are in the database
                    create_graph_for_object(deckObject)
                    
                    # Update the deck data with the graph and node data
                    deck_data = deckObject.to_data()
                    #deck_data['graph'] = deckObject.data.graph
                    #deck_data['node_data'] = deckObject.data.node_data

                    # Collect the deck data for upserting
                    deckDataList.append(deck_data)

                if deckDataList:                 
                    self.dbmgr.upsert_many('Deck', deckDataList)                

        if fusions_data:
            
            def extract_fb_ids_and_factions(my_decks, fusion_data):
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

                return forgeborn_ids, factions

            gv.update_progress('DeckLibrary', 0, len(fusions_data), 'Saving Online Fusions')            
            for fusion_data in fusions_data:
                decks = fusion_data['myDecks']                      
                forgebornIds, factions = extract_fb_ids_and_factions(decks, fusion_data)
                fusion_data['ForgebornIds'] = forgebornIds
                fusion_data['faction'] = factions[0]
                fusion_data['crossFaction'] = factions[1]

                # Graph creation 
                fusionObject = Fusion.from_data(fusion_data)
                create_graph_for_object(fusionObject)
                
                # Save the fusion to the database
                fusionObject.save()           
                self.online_fusions.append(fusion_data)                
                gv.update_progress('DeckLibrary', message=f"Saved Fusion {fusionObject.name}")
        
        # In creation mode we create fusions for all decks

        if mode =='fuse':
            #print('Creating fusions...')
            deckCursor = self.dbmgr.find('Deck', {}, {'name': 1})                
            self.new_decks = [deck for deck in deckCursor]             
            self.make_fusions()
                         
    def make_fusions(self):
        # Get all deckNames from the database
        deckCursor = self.dbmgr.find('Deck', {})
        allDeckData = {deck['name']: deck for deck in deckCursor}
        allDeckNames = list(allDeckData.keys())

        # Combine allDeckNames in pairs with new_decks only, not with themselves
        newDeckNames = [deck['name'] for deck in self.new_decks]
    
        # Pair newDeckNames with allDeckNames but not with itself
        newCombinations = [(newDeck, allDeck) for newDeck in newDeckNames for allDeck in allDeckNames if newDeck != allDeck]
        newCombinationsSets = [set(combination) for combination in newCombinations]

        # Replace newCombinationNames with the actual decks
        deckCombinationData = []
        for combination in newCombinationsSets:
            deckCombinationData.append([allDeckData[deckName] for deckName in combination])

        # Create new fusions with the newCombinations
        if deckCombinationData:
            print(f'Creating fusions with username: {gv.username}')
            multi_process = MultiProcess(gv.username, deckCombinationData)
            multi_process.run()
         

