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
        total_fusions = len(self.library['Deck']) ** 2 - len(self.library['Deck'])
        if total_fusions == 0: return 
        progress_bar = tqdm(total=total_fusions, desc="Making Fusions", mininterval=0.1,colour='GREEN')

        for deck1 in self.library['Deck'].values():
            for deck2 in self.library['Deck'].values():
                if deck1 is not deck2:
                    fusion_name = f"{deck1.name}_{deck2.name}"
                    if fusion_name not in self.library['Fusion']:
                        fusion = Fusion(fusion_name, [deck1, deck2])
                        if fusion.fused is not None:
                            #print(f"+F {fusion_name}")
                            self.library['Fusion'][fusion_name] = fusion
                    time.sleep(0.001)
                    progress_bar.update(1)
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


