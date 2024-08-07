from GlobalVariables import global_vars
from multiprocessing import Pool, cpu_count
from tqdm.notebook import tqdm

class MultiProcess:
    def __init__(self, func, data, additional_data=None, chunk_size=100):
        self.func = func
        self.num_items = len(data)
        self.num_processes = min(self.num_items, cpu_count()) 
        self.data = []
        for i in range(0, len(data), chunk_size):
            data_chunk = data[i:i+chunk_size]
            self.data.append((data_chunk, additional_data))
        
    def run(self):
        with Pool(processes=self.num_processes) as pool:                        
            global_vars.update_progress('MultiProcess Fusions', 0, self.num_items, 'Fusioning Decks')
            for chunk_size in pool.imap_unordered(self.func, self.data):                
                global_vars.update_progress('MultiProcess', chunk_size)
            
