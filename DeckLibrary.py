from Card_Library import Fusion, Deck, Card
from tqdm import tqdm 
from itertools import combinations
from multiprocessing import Pool, cpu_count


class DeckLibrary:
    def __init__(self, decks_data):        
        self.decks = {}        
        self.Decks = 'Decks'        
        self.Fusions = 'Fusions'
        
        for deck_data in decks_data:
            deck = Deck.from_data(deck_data) 
            deck.children_data = {cardId : 'Card_Library.Card' for cardId in deck.cardIds}
            deck.save()
            deckHash = deck.hash_children()
            print(deckHash)
        
        #deck = Deck.lookup(name=deck.name)
        #if deck:
        #    for card_data in deck.cards.values():
        #        card_obj = Card.from_data(card_data)                
        #        myInterfaceHash = {card_obj._id : card_obj.hash_children() }
        #        if myInterfaceHash: print(myInterfaceHash) 
                 
    def make_fusions(self, fusion_limit=None):
        total_decks = len(self.decks)
        if total_decks == 0:
            return 0            
       
#        Prepare the arguments for the fusion_task
        args = [(deck1, deck2) for deck1, deck2 in combinations(self.decks.values(), 2)]

        with Pool(processes=cpu_count()) as pool:
            try:
                for fusion in pool.imap_unordered(create_fusion, args):
                    if fusion:
                        write_queue.put((fusion.name, fusion))                        
            except KeyboardInterrupt:
                print("Interrupted! Terminating processes...")
                pool.terminate()
                pool.join()

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


