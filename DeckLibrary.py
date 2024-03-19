from MongoDB.DatabaseManager import DatabaseManager
from CardLibrary import  Fusion, FusionData, Deck, Card
from tqdm import tqdm 
from MultiProcess import MultiProcess
from tqdm import tqdm
import GlobalVariables

class DeckLibrary:
    def __init__(self, decks_data, fusions_data, mode):                
        self.dbmgr = DatabaseManager(GlobalVariables.username)
        self.new_decks = []
        self.online_fusions = []
        
        deckNames = []
        if not mode == 'update':
            deckCursor = self.dbmgr.find('Deck', {})
            deckNames = [deck['name'] for deck in deckCursor]

        with tqdm(total=self.dbmgr.count_documents('Deck'), desc="Loading Decks",mininterval=0.1, colour='BLUE') as pbar:
            for deckData in decks_data:
                deckName = deckData['name']
                if deckName not in deckNames:                    
                    self.new_decks.append(deckData)    
                    new_deck = Deck.from_data(deckData)
                    if new_deck.children_data:
                        new_deck.children_data.update({new_deck.forgebornId : 'CardLibrary.Forgeborn'})
                    new_deck.save()            
                    for index, card in new_deck.cards.items():                      
                        myCard = Card.from_data(card)
                        id = new_deck.cardIds[int(index)-1]
                        myCard._id = id
                        myCard.save()
                pbar.update(1)
        
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
            multi_process = MultiProcess(create_fusion, deckCombinationData, GlobalVariables.username)
            multi_process.run()
           

from pymongo import UpdateOne

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
            fusionHash = fusionObject.hash_children()
            fusionData['hash'] = fusionHash

            operations.append(UpdateOne({'_id': fusionId}, {'$set': fusionData}, upsert=True))

    if operations and dbmgr:
        dbmgr.bulk_write('Fusion', operations)
    
    return len(operations)