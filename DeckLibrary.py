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
                self.fusions.append(obj.getDeck())
        
        self.fusions += self.get_fusions()
        self.synergy_template = synergy_template or SynergyTemplate()                

    def get_fusions(self):
        fusions = []
        for deck1 in self.decks:
            for deck2 in self.decks:
                fusion = deck1 + deck2
                if fusion is not None:
                    fusions.append(fusion)
        return fusions

    def evaluate_decks(self):
        evaluation = {}
        for fusion in self.fusions:
            score = ev.evaluate_deck(fusion)
            evaluation[fusion.name]  = score
            print(f"Deck Evaluation added: {fusion.name} {score}")
        return evaluation

    def get_best_synergies(self):

        best_synergy_decks = { synergy : [] for synergy in self.synergy_template.synergies}
      
        for synergy in self.synergy_template.synergies:  
            max_percentage = 0 
            for fusion in self.fusions:                  
                if synergy in fusion.ICollection.synergies:
                    deck_synergy = fusion.ICollection.synergies[synergy] 
                    p = ev.evaluate_synergy(deck_synergy)
                    if p == max_percentage :
                        best_synergy_decks[synergy].append(fusion)     
                    if p > max_percentage :
                        max_percentage = p
                        best_synergy_decks[synergy] = [fusion] 
                    

        for synergy, fusions in best_synergy_decks.items():
            for fusion in fusions:
                deck_synergy = fusion.ICollection.synergies[synergy]
                sources = sum(deck_synergy.get_source_counts().values())
                targets = sum(deck_synergy.get_target_counts().values())
                print(f"Synergy: {synergy} in '{fusion.name}' = {sources} / {targets} =>  {ev.evaluate_synergy(deck_synergy)}")

    
