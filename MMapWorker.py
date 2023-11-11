import mmap, os
from multiprocessing import Process, shared_memory
from Card_Library import Fusion

class MMapWorker(Process):
    def __init__(self, worker_id, mmap_file, half_deck_list, mm_chunk):
        super().__init__()
        self.worker_id = worker_id
        self.mmap_file = mmap_file
        self.half_deck_list = half_deck_list
        self.start_offset = mm_chunk[0]
        self.end_offset   = mm_chunk[1]
        #self.get_index_offsets()
        
    def run(self):
        # Open the memory map file for writing
        with open(self.mmap_file, 'r+b') as f:
            # Get the actual file size
            file_size = os.fstat(f.fileno()).st_size

            # Ensure the offset is a multiple of the system's allocation granularity
            allocation_granularity = mmap.ALLOCATIONGRANULARITY
            if self.start_offset % allocation_granularity != 0:
                raise ValueError(f"Offset must be a multiple of {allocation_granularity}")

            # Calculate the length of the mapping
            mmap_length = min(self.end_offset - self.start_offset, file_size - self.start_offset)

            # Create the memory map
            with mmap.mmap(f.fileno(), length=mmap_length, offset=self.start_offset) as mm:
                # Process each index range in the chunk and write fusions to the memory map
                num_of_objects = mmap_length / 65536
                for position in range(num_of_objects):
                    row = position // self.num_columns
                    col = position % self.num_columns
                
                    fusion = None
                    deckID1 , deckID2 = row, col
                    if deckID1 != deckID2:
                        deck1 = self.half_deck_list[deckID1]
                        deck2 = self.half_deck_list[deckID2]
                        fusion = Fusion([deck1, deck2])

                    if fusion: 
                        print(f"Write Fusion into memorymap")                    

    # The rest of the methods would be implemented here

    def get_index_offsets(self):
        # Now find the min and max byte offsets
        self.start_offset = min(self.index_chunk.values(), key=lambda x: x[0])[0]
        self.end_offset = max(self.index_chunk.values(), key=lambda x: x[1])[1]

        print(f"Start Offset: {self.start_offset}, End Offset: {self.end_offset}")

