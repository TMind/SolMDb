from Card_Library import Deck, Fusion
from tqdm import tqdm 
import time
from prof import profileit
class DeckLibrary:
    def __init__(self, decks_or_fusions):
        self.library = {
            'Deck': {},
            'Fusion': {}
        }

        self.update(decks_or_fusions)

    @profileit("profile_for_make_fusions_001")
    def make_fusions(self):
        total_fusions = len(self.library['Deck']) * (len(self.library['Deck']) - 1)
        if total_fusions == 0: return 
        progress_bar = tqdm(total=total_fusions, desc="Making Fusions", mininterval=0.1,colour='GREEN')

        for i, deck1 in enumerate(self.library['Deck'].values()):
            for j, deck2 in enumerate(self.library['Deck'].values()):
                if i < j and deck1.faction != deck2.faction: 
                    # Create both fusion combinations for the two decks , but only one deck add
                    cards = { **deck1.cards, **deck2.cards}                    
                    D1 = Deck(f"{deck1.name}_{deck2.name}", deck1.forgeborn, f"{deck1.faction}|{deck2.faction}", cards)
                    D2 = Deck(f"{deck2.name}_{deck1.name}", deck2.forgeborn, f"{deck1.faction}|{deck2.faction}", cards)

                    fusion1 = Fusion(D1.name, [D1])
                    fusion1.decks = [deck1,deck2]

                    fusion2 = Fusion(D2.name, [D2])
                    fusion2.decks = [deck2,deck1]
                                        
                    # Loop through the created fusions
                    for fusion in [fusion1, fusion2]:
                        if fusion.fused is not None and fusion.name not in self.library['Fusion']:
                            #print(f"+F {fusion.name}")
                            self.library['Fusion'][fusion.name] = fusion
                    progress_bar.update(2)
            time.sleep(0.001)
        progress_bar.close()

    @profileit("profile_for_update_001")
    def update(self, objects):        
        total_updates = len(objects)
        if total_updates == 0 : return 
        progress_bar = tqdm(total=total_updates, desc="Updating Library",mininterval=0.1, colour='MAGENTA')

        for obj in objects:
            obj_type = type(obj).__name__
            container = self.library[obj_type]
            if obj.name not in container:
                #print(f"+D {obj.name}")
                container[obj.name] = obj
            progress_bar.update(1)

        progress_bar.close()

        self.make_fusions()

    def to_json(self):
        return {
            'decks': [deck.to_json() for deck in self.library['Deck'].values()],
            'fusions': [fusion.to_json() for fusion in self.library['Fusion'].values()]         
        }


