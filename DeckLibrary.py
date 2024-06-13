from MyGraph import MyGraph
from MongoDB.DatabaseManager import DatabaseManager
from Card_Library import  Fusion, FusionData, Deck, Card
from tqdm import tqdm 
from MultiProcess import MultiProcess
from tqdm import tqdm
import GlobalVariables

class DeckLibrary:
    def __init__(self, decks_data, fusions_data, mode):                
        self.dbmgr = DatabaseManager(GlobalVariables.username)
        self.new_decks = []
        self.online_fusions = []
        
        if decks_data:            
            deckCursor = self.dbmgr.find('Deck', {}, {'name': 1})                
            deckNamesDatabase = [deck['name'] for deck in deckCursor]
                                    
            cardListDatabase = self.dbmgr.find('Card', {})        
            cardIdsDatabase = [card['_id'] for card in cardListDatabase]

            length = len(decks_data) 
            with tqdm(total=length, desc="Saving Decks",mininterval=0.1, colour='BLUE') as pbar:
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
                    pbar.update(1)
                
                if deckDataList:
                    self.dbmgr.insert_many('Deck', deckDataList)                
                if cardDataList:                                                   
                    # Remove duplicate entries but keep the first one in the list
                    seen = set()
                    cardDataList = [x for x in cardDataList if not (x['_id'] in seen or seen.add(x['_id']))]                                    
                    self.dbmgr.insert_many('Card', cardDataList)
    
        if fusions_data:
            with tqdm(total=len(fusions_data), desc="Saving Fusions",mininterval=0.1, colour='YELLOW') as pbar:
                for fusion_data in fusions_data:
                    decks = fusion_data['myDecks']            
                    fusionDeckNames = []
                    if isinstance(decks[0], str):
                        fusionDeckNames = [deckName for deckName in decks]
                    else:
                        fusionDeckNames = [deck['name'] for deck in decks]
                                    
                    fusion = Fusion.from_data(fusion_data)            
                    fusion.save()           
                    self.online_fusions.append(fusion_data)
                    pbar.update(1)
                         
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
            multi_process = MultiProcess(create_fusion, deckCombinationData, GlobalVariables.username)
            multi_process.run()
           

from pymongo.operations import UpdateOne
import networkx as nx

def create_fusion(dataChunks):
    operations = []
    dbmgr = None 
    
    dataChunk , additional_data = dataChunks

    for decks in dataChunk:
        GlobalVariables.username = additional_data
        if not dbmgr:
            dbmgr = DatabaseManager(GlobalVariables.username)
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

            operations.append(UpdateOne({'_id': fusionId}, {'$set': fusionData}, upsert=True))

    if operations and dbmgr:
        dbmgr.bulk_write('Fusion', operations)
    
    return len(operations)