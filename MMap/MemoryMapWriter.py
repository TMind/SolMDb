from multiprocessing import Process
from MMap.MemoryMap import MemoryMap
from tqdm import tqdm 


class MemoryMapWriter(Process):
    def __init__(self, mmap_file, queue, offset_start, offset_end):
        super().__init__()
        self.mmap_file = mmap_file
        self.queue = queue
        self.offset_start = offset_start
        self.offset_end = offset_end


    # def run(self):
    #     # Open its own MemoryMap instance        
    #     with MemoryMap(self.mmap) as mmap:
    #         num_objects = mmap.map_size/mmap.max_object_size
    #         with tqdm(total=num_objects, desc="Fusioning", mininterval=0.1, colour='GREEN') as pbar:
    #             while True:
    #                 task = self.queue.get()
    #                 if task is None:
    #                     break  # None is our signal to stop the process
    #                 identifier, obj = task
    #                 if not mmap.index.index.get(identifier,None):
    #                     mmap.add_object(obj, identifier)
    #                 pbar.update()
    #         pbar.close()


    def run(self):
        num_objects = (self.offset_end - self.offset_start) / 65536
        with MemoryMap(self.mmap_file) as mmap:
            while not self.queue.empty():
                # Synchronize dequeuing
                try:
                    obj, identifier = self.queue.get_nowait()
                except Empty:
                    break

                # Calculate where to write obj
                offset = self.calculate_offset(identifier)
                if offset >= self.offset_start and offset < self.offset_end:
                    # Serialize and write obj to mmap at the correct offset
                    mmap.add_object(obj, identifier, self.offset_start, self.offset_end)

    def calculate_offset(self, identifier):
        # Calculate the offset for the object based on the identifier
        pass

    def write_to_mmap(self, obj, offset):
        # Write the serialized object to the mmap at the given offset
        pass
