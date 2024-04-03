from Card_Library import Deck, Fusion
from tqdm import tqdm 
from itertools import combinations
from multiprocessing import Pool, cpu_count, Event
import time

class DeckLibrary:
    def __init__(self, decks_or_fusions):
        self.library = {
            'Deck': {},
            'Fusion': {}
        }

        self.update(decks_or_fusions)

    def make_fusions(self):
        total_fusions = len(self.library['Deck']) * (len(self.library['Deck']) - 1) / 2
        if total_fusions == 0: return 0
        #progress_bar = tqdm(total=total_fusions, desc="Making Fusions", mininterval=0.1,colour='GREEN')

        deck_pairs = []

        for deck1, deck2 in combinations(self.library['Deck'].values(),2):
            if deck1.faction != deck2.faction:
                unique_fusion_name = "_".join(sorted([deck.name for deck in [deck1,deck2]]))
                if self.library['Fusion'].get(unique_fusion_name) is None :                                                
                    deck_pairs.append((deck1, deck2))

        with Pool(processes=cpu_count()) as pool:
            terminate_event = Event()
            fusion_results = []
            args_list = [(deck1, deck2) for (deck1, deck2) in deck_pairs ]
            # Initialize the progress bar
            pbar = tqdm(total=len(args_list), desc="Fusioning", mininterval=0.1, colour='BLUE')

            try:

                for fusion in pool.imap_unordered(process_decks, args_list):
                    if terminate_event.is_set():
                        print("Parent Process signaled termination. Exiting child processes!")
                        pool.terminate()
                        break

                    if fusion:
                        self.library['Fusion'][fusion.fused_name] = fusion
                        pbar.update()            

            except KeyboardInterrupt:
                print("Interrupter! Terminating processes...")
                pool.terminate()
                pool.join()

            pbar.close()

        return len(deck_pairs) or 0
        

    def update(self, objects):        
        total_updates = len(objects)
        if total_updates == 0 : return 
        progress_bar = tqdm(total=total_updates, desc="Updating Library",mininterval=0.1, colour='MAGENTA')

        num = 0
        for obj in objects:
            obj_type = type(obj).__name__
            container = self.library[obj_type]
            if container.get(obj.name) is None:
                #print(f"+D {obj.name}")
                num += 1
                container[obj.name] = obj
            progress_bar.update(1)

        progress_bar.close()

        num += self.make_fusions()
        return num 

    def filter(self, Filter):       
        self.library['Deck']   = Filter.apply(self.library['Deck'])
        self.library['Fusion'] = Filter.apply(self.library['Fusion'])

    def to_json(self):
        return {
            'decks': [deck.to_json() for deck in self.library['Deck'].values()],
            'fusions': [fusion.to_json() for fusion in self.library['Fusion'].values()]         
        }
    

def process_decks(decks):

    time.sleep(0.001)
    return Fusion(decks)
    