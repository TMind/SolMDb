from Evaluation import Evaluation
from Synergy import SynergyTemplate
class DeckLibrary:
    def __init__(self, decks, synergy_template=None):
        self.decks = decks
        self.fusions = self.get_fusions()
        self.synergy_template = synergy_template or SynergyTemplate()
        #self.synergy_stats = {synergy_name: {'target': {}, 'source': {}} for synergy_name in self.synergy_template.get_synergies() }        
        self.evaluator = Evaluation()

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
            score = self.evaluator.evaluate_deck(fusion)
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
                    p = Evaluation().evaluate_synergy(deck_synergy)
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
                print(f"Synergy: {synergy} in '{fusion.name}' = {sources} / {targets} =>  {Evaluation().evaluate_synergy(deck_synergy)}")

    
