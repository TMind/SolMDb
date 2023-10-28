from Card_Library import Fusion
from tqdm import tqdm 
from itertools import combinations
from multiprocessing import Pool, cpu_count, Event
import time, signal
from MemoryMap import MemoryMapManager

class DeckLibrary:
    def __init__(self, decks_or_fusions, filename='decklibrary.mmap'):
        #self.library = {
        #    'Deck': {},
        #    'Fusion': {}
        #}
        self.memorymap = MemoryMapManager(filename)

        self.update(decks_or_fusions)

    def make_fusions(self, fusion_limit=None):
        #total_fusions = len(self.library['Deck']) * (len(self.library['Deck']) - 1) / 2
        total_fusions = self.memorymap.size()
        if total_fusions == 0:
            return 0

        deck_pairs = []

        #for deck1, deck2 in combinations(self.library['Deck'].values(), 2):
        for deckname1, deckname2 in combinations(self.memorymap.keys(), 2):
            #if deckname1.faction != deck2.faction:
            unique_fusion_name = "_".join(sorted([deckname1,deckname2]))
            #if self.library['Fusion'].get(unique_fusion_name) is None:
            if self.memorymap._get(unique_fusion_name) is None:
                deck_pairs.append((deckname1, deckname2))

        if fusion_limit is not None:
            deck_pairs = deck_pairs[:fusion_limit]  # Limit the deck pairs to the specified fusion limit


        with Pool(processes=cpu_count()) as pool:
            terminate_event = Event()
            fusion_results = []
            args_list = [(self.memorymap._get(deckname1), self.memorymap._get(deckname2)) for (deckname1, deckname2) in deck_pairs ]
            # Initialize the progress bar
            pbar = tqdm(total=len(args_list), desc="Fusioning", mininterval=0.1, colour='BLUE')

            try:
                def signal_handler(sig, frame):
                    terminate_event.set()
                    signal.signal(signal.SIGINT, signal.SIG_DFL)

                signal.signal(signal.SIGINT, signal_handler)

                for fusion in pool.imap_unordered(process_decks, args_list):
                    if terminate_event.is_set():
                        print("Parent Process signaled termination. Exiting child processes!")
                        pool.terminate()
                        break

                    if fusion:
                        self.memorymap.add(fusion)
                        #self.library['Fusion'][fusiox.fused_name] = fusion
                        pbar.update()            

            except KeyboardInterrupt:
                print("Interrupter! Terminating processes...")
                pool.terminate()
                pool.join()

            pbar.close()

        return len(deck_pairs) or 0
        

    def update(self, objects, limit=None):        
        total_updates = len(objects)
        if total_updates == 0 : return 
        progress_bar = tqdm(total=total_updates, desc="Updating Library",mininterval=0.1, colour='MAGENTA')

        num = 0
        #for obj in objects:
            #obj_type = type(obj).__name__
            #container = self.library[obj_type]
            #if container.get(obj.name) is None:
                #print(f"+D {obj.name}")
            #    num += 1
            #    container[obj.name] = obj
        self.memorymap.update(objects)
        progress_bar.update(len(objects))

        progress_bar.close()

        num += self.make_fusions(limit)
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
    