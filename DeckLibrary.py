from CardLibrary import Forgeborn, Fusion, FusionData, Deck, Card
from tqdm import tqdm 
from itertools import combinations
from multiprocessing import Pool, cpu_count


class DeckLibrary:
    def __init__(self, decks_data, fusions_data):        
        self.decks = {}        
        self.fusions = {}        
        
        for deck_data in decks_data:
            deck = Deck.from_data(deck_data) 
            if deck.children_data:
                deck.children_data.update({deck.forgebornId : 'CardLibrary.Forgeborn'})            
            deck.save()
            for index, card in deck.cards.items():                      
                myCard = Card.from_data(card)
                id = deck.cardIds[int(index)-1]
                myCard._id = id
                myCard.save()
            #deckHash = deck.hash_children()
            #print(deckHash)
        
        for fusion_data in fusions_data:
            fusion = Fusion.from_data(fusion_data)
            # if fusion.children_data:
            #     if fusion.data.currentForgebornId == '':
            #         fusion.data.currentForgebornId = fusion.myDecks[0]['forgeborn']['id']                
            #     fusion.children_data.update({fusion.data.currentForgebornId : 'CardLibrary.Forgeborn'})                                
            fusion.save()
            #fusionHash = fusion.hash_children()
            #print(fusionHash)
        
        self.make_fusions()
                         
    def make_fusions(self):
                
        myItem = Deck(None)                        
        myItems = myItem.db_manager.find('Deck', {})
                
        
        deck_combinations = list(combinations(myItems, 2))
        progress_bar = tqdm(total=len(deck_combinations), desc="Creating Fusions", mininterval=0.1, colour='BLUE')
        for deck_combination in deck_combinations:
            deck1, deck2 = deck_combination
            if deck1['faction'] != deck2['faction']:
                fusionName = f"{deck1['name']}_{deck2['name']}"                     
                fusionId = fusionName
                fusionDecks =  [deck1, deck2] 
                fusionBorn = deck1['forgebornId']
                fusionData = FusionData(fusionName, fusionDecks, fusionBorn, fusionId) 
                fusion = Fusion(fusionData)
                if fusion:
                    fusion.save()
            progress_bar.update(1)
        progress_bar.close()
        

    def update(self, objects, limit=None):        
        total_updates = len(objects)
        #if total_updates == 0 : return 
        progress_bar = tqdm(total=total_updates, desc="Updating Library",mininterval=0.1, colour='MAGENTA')

        num = 0
        for obj in objects:
            self.decks[obj.name] = obj
            progress_bar.update(1)
        progress_bar.close()

        self.make_fusions(limit)
        return num 

    def filter(self, Filter):       
        self.database['Deck']   = Filter.apply(self.database['Deck'])
        self.database['Fusion'] = Filter.apply(self.database['Fusion'])

    def to_json(self):
        return {
            'decks': [deck.to_json() for deck in self.database['Deck'].values()],
            'fusions': [fusion.to_json() for fusion in self.database['Fusion'].values()]         
        }

def create_fusion(decks):    
    deck1, deck2 = decks
    fusion = None
    if deck1.faction != deck2.faction:
        fusion = Fusion(decks)
    return fusion


