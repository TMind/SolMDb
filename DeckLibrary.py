from Card_Library import Deck, Fusion
class DeckLibrary:
    def __init__(self, decks):
        self.decks = []
        self.fusions = []        

        for obj in decks:
            if isinstance(obj, Deck):
                self.decks.append(obj)
            if isinstance(obj, Fusion):
                FusionDeck = obj.getDeck()                
                self.fusions.append(FusionDeck)
        
        self.fusions.extend(self.get_fusions())              

    def get_fusions(self):
        fusions = []
        for deck1 in self.decks:
            for deck2 in self.decks:
                if deck1 is not deck2:                    
                    fusion = deck1 + deck2                                                       
                    if fusion is not None:
                        fusions.append(fusion)
        return fusions

    def update(decks):

        print(f"Update DeckLibrary...")


    @classmethod
    def from_json(cls, data):
        decks = [Deck.from_json(deck_data) for deck_data in data['decks']]
        fusions = [Fusion.from_json(fusion_data) for fusion_data in data['fusions']]
        return cls(decks, fusions)

    def to_json(self):
        return {
            'decks': [deck.to_json() for deck in self.decks],
            'fusions': [fusion.to_json() for fusion in self.fusions]         
        }


