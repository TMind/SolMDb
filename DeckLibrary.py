from Card_Library import Deck, Fusion
class DeckLibrary:
    def __init__(self, decks_or_fusions):
        self.decks = {}          # Deck        
        self.fusions = {}

        for obj in decks_or_fusions:
            if isinstance(obj, Deck):
                self.decks[obj.name] = obj
            if isinstance(obj, Fusion):                
                self.fusions[obj.name] = obj
        
        self.make_fusions()

    def make_fusions(self):
        print("Fusing decks...")
        for deck1 in self.decks.values():
            for deck2 in self.decks.values():
                if deck1 is not deck2:
                    fusion_name = f"{deck1.name}_{deck2.name}"
                    if fusion_name not in self.fusions:
                        fusion = Fusion(fusion_name, [deck1, deck2])
                        if fusion.fused is not None:
                            print(f"+ {fusion_name}")
                            self.fusions[fusion_name] = fusion

    def update(self, new_decks):
        print(f"Updating DeckLibrary...")        
        for deck in new_decks:
            if deck.name not in self.decks:
                print(f"+ {deck.name}")
                self.decks[deck.name] = deck
        self.make_fusions()
        
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


