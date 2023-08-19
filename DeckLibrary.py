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
        total_fusions = len(self.library['Deck']) * (len(self.library['Deck']) - 1) / 2
        if total_fusions == 0: return 
        progress_bar = tqdm(total=total_fusions, desc="Making Fusions", mininterval=0.1,colour='GREEN')

        for i, deck1 in enumerate(self.library['Deck'].values()):
            for j, deck2 in enumerate(self.library['Deck'].values()):
                if i < j and deck1.faction != deck2.faction:                    
                    fusion_name = "_".join(sorted([deck.name for deck in [deck1,deck2]]))
                    if self.library['Fusion'].get(fusion_name) is None :                            
                            self.library['Fusion'][fusion_name] = Fusion([deck1, deck2])
                    progress_bar.update(1)
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
            if container.get(obj.name) is None:
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


