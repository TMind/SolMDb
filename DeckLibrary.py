from ast import Global
from MyGraph import MyGraph
from MongoDB.DatabaseManager import DatabaseManager
from CardLibrary import  Fusion, FusionData, Deck, Card
from tqdm import tqdm 
from MultiProcess import MultiProcess
from tqdm import tqdm
from GlobalVariables import global_vars

class DeckLibrary:
    def __init__(self, decks_data, fusions_data, mode):                
        #self.dbmgr = DatabaseManager(global_vars.username)
        self.dbmgr = global_vars.myDB
        self.new_decks = []
        self.online_fusions = []
        
        if decks_data:            
            deckCursor = self.dbmgr.find('Deck', {}, {'name': 1})                
            deckNamesDatabase = [deck['name'] for deck in deckCursor]
                                    
            cardListDatabase = self.dbmgr.find('Card', {})        
            cardIdsDatabase = [card['_id'] for card in cardListDatabase]

            length = len(decks_data) 
            #with tqdm(total=length, desc="Saving Decks",mininterval=0.1, colour='BLUE') as pbar:
            deckDataList = []
            cardDataList = []
            for deckData in decks_data:
                deckName = deckData['name'] 
                # Save only new decks
                if deckName not in deckNamesDatabase:                         
                    self.new_decks.append(deckData)    
                    new_deck = Deck.from_data(deckData)
                    if new_deck.children_data:
                        new_deck.children_data.update({new_deck.forgebornId : 'CardLibrary.Forgeborn'})
                    deckDataList.append(new_deck.to_data())
                    
                    # Save all cards that are not already in the database
                    for index, card in new_deck.cards.items():
                        id = new_deck.cardIds[int(index)-1]                                                
                        if id not in cardIdsDatabase:
                            myCard = Card.from_data(card)                                                                                
                            myCard.data._id = id                            
                            cardDataList.append(myCard.to_data())
                    #pbar.update(1)
                
            if deckDataList:
                self.dbmgr.insert_many('Deck', deckDataList)                
            if cardDataList:                                                   
                # Remove duplicate entries but keep the first one in the list
                seen = set()
                cardDataList = [x for x in cardDataList if not (x['_id'] in seen or seen.add(x['_id']))]                                    
                self.dbmgr.insert_many('Card', cardDataList)

        if fusions_data:
            
            global_vars.update_progress('DeckLibrary', 0, len(fusions_data), 'Saving Online Fusions')            
            for fusion_data in fusions_data:
                decks = fusion_data['myDecks']                      
                fusionObject = Fusion.from_data(fusion_data)
                fusionGraph = MyGraph()  
                fusionGraph.create_graph_children(fusionObject)
                # Convert the graph to a dictionary
                fusionGraphDict = nx.to_dict_of_dicts(fusionGraph.G)
                fusionObject.graph = fusionGraphDict
                fusionObject.node_data = fusionGraph.node_data
                fusionObject.save()           
                self.online_fusions.append(fusion_data)                
                global_vars.update_progress('DeckLibrary', message=f"Saved Fusion {fusionObject.name}")
                            
        # Get number of fusions from the database
        fusionCursor = self.dbmgr.find('Fusion', {})
        fusionNamesDatabase = [fusion['name'] for fusion in fusionCursor]
        
        # Check if fusions exist already in the database and if not, create them

        if mode =='create':
            print('Creating fusions...')
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
            multi_process = MultiProcess(create_fusion, deckCombinationData, global_vars.username)
            multi_process.run()
           

from pymongo.operations import UpdateOne
import networkx as nx

def create_fusion(dataChunks):
    operations = []
    dbmgr = None 
    
    dataChunk , additional_data = dataChunks

    for decks in dataChunk:
        global_vars.username = additional_data
        if not dbmgr:
            dbmgr = DatabaseManager(global_vars.username)
        deck1, deck2 = decks

        if deck1['faction'] != deck2['faction']:
            fusionName = f"{deck1['name']}_{deck2['name']}"                     
            fusionId = fusionName
            fusionDeckNames =  [deck1['name'], deck2['name']] 
            fusionBornIds = [deck1['forgebornId'], deck2['forgebornId']]            
            fusionObject = Fusion(FusionData(fusionName, fusionDeckNames, deck1['forgebornId'] ,fusionBornIds, fusionId) )
            fusionData = fusionObject.to_data()  
            fusionGraph = MyGraph()  
            fusionGraph.create_graph_children(fusionObject)
            # Convert the graph to a dictionary
            fusionGraphDict = nx.to_dict_of_dicts(fusionGraph.G)
            fusionData['graph'] = fusionGraphDict
            fusionData['node_data'] = fusionGraph.node_data

            operations.append(UpdateOne({'_id': fusionId}, {'$set': fusionData}, upsert=True))            

    if operations and dbmgr:
        dbmgr.bulk_write('Fusion', operations)
    
    return len(dataChunk) #len(operations)