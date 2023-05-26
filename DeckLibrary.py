import Evaluation as ev
from Synergy import SynergyTemplate
import Card_Library
class DeckLibrary:
    def __init__(self, decks, synergy_template=None):
        self.decks = []
        self.fusions = []

        for obj in decks:
            if isinstance(obj, Card_Library.Deck):
                self.decks.append(obj)
            if isinstance(obj, Card_Library.Fusion):
                FusionDeck = obj.getDeck()                
                self.fusions.append(FusionDeck)
        
        self.fusions.extend(self.get_fusions())
        self.synergy_template = synergy_template or SynergyTemplate()                

    def get_fusions(self):
        fusions = []
        for deck1 in self.decks:
            for deck2 in self.decks:
                if deck1 is not deck2:                    
                    fusion = deck1 + deck2                                                       
                    if fusion is not None:
                        fusions.append(fusion)
        return fusions

    
