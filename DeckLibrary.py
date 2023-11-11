from Card_Library import Fusion
from tqdm import tqdm 
from itertools import combinations
from multiprocessing import Pool, cpu_count, shared_memory
import time
from MemoryMap import MemoryMap
import pickle
from math import comb
from MMapWorker import MMapWorker

class DeckLibrary:
    def __init__(self, decks_or_fusions, filename='DeckLibrary.mmap'):
        maxsize = len(pickle.dumps(decks_or_fusions[0])) if decks_or_fusions else 65536
        self.memorymap = MemoryMap(filename, len(decks_or_fusions),len(decks_or_fusions))
        self.update(decks_or_fusions)

    def make_fusions(self, fusion_limit=None):
        total_decks = len(self.memorymap)
        if total_decks == 0:
            return 0
        
        # Create shared memory with diagonal decks
        half_deck_list = self.memorymap.get_diagonal()  
        #deck_data_size = sum(len(deck) for deck in serialized_decks)
        #shm = shared_memory.SharedMemory(create=True, size=deck_data_size)

        #offset = 0
        #for serialized_deck in serialized_decks:
        #    shm.buf[offset:offset + len(serialized_deck)] = serialized_deck
        #    offset += len(serialized_deck)
        
        #shared_deck_memory_name = shm.name

        # Usage example, assuming shared deck memory and index chunks are set up
        workers = []        
        #index_chunks = self.memorymap.index_file.split_index_data(cpu_count())
        mm_chunks = self.memorymap.get_slices(cpu_count())
        # Now create workers with the determined start_offset and end_offset
        for worker_id, mm_chunk in enumerate(mm_chunks):
            worker = MMapWorker(worker_id, self.memorymap.filename, half_deck_list, mm_chunk)
            workers.append(worker)
            worker.start()

        # Wait for all workers to finish
        for worker in workers:
            worker.join()

        #shm.unlink
        #shared_deck_memory_name = ''

        # Prepare the arguments for the fusion_task
        # args = [(self.memorymap.ni_get(deckname1), self.memorymap.ni_get(deckname2)) for deckname1, deckname2 in combinations(self.memorymap.ni_keys(), 2)]
        # total_combinations = len(args)

        # with tqdm(total=total_combinations, desc="Fusioning", mininterval=0.1, colour='GREEN') as pbar:
        #     with Pool(processes=cpu_count()) as pool:
        #         try:
        #             for fusion in pool.imap_unordered(create_fusion, args):
        #                 if fusion:
        #                     self.memorymap.add_fusion(fusion)
        #                     pbar.update()
        #         except KeyboardInterrupt:
        #             print("Interrupted! Terminating processes...")
        #             pool.terminate()
        #             pool.join()

        #     pbar.close()


    def update(self, objects, limit=None):        
        total_updates = len(objects)
        #if total_updates == 0 : return 
        progress_bar = tqdm(total=total_updates, desc="Updating Library",mininterval=0.1, colour='MAGENTA')

        num = 0
        for obj in objects:
            self.memorymap.ni_add(obj)
            progress_bar.update(1)
        progress_bar.close()

        self.make_fusions(limit)
        return num 

    def filter(self, Filter):       
        self.library['Deck']   = Filter.apply(self.library['Deck'])
        self.library['Fusion'] = Filter.apply(self.library['Fusion'])

    def to_json(self):
        return {
            'decks': [deck.to_json() for deck in self.library['Deck'].values()],
            'fusions': [fusion.to_json() for fusion in self.library['Fusion'].values()]         
        }

def create_fusion(decks):    
    deck1, deck2 = decks
    fusion = None
    if deck1.faction != deck2.faction:
        fusion = Fusion(decks)
    return fusion


