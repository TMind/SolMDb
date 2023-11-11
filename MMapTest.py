from MemoryMap import MemoryMap
import pickle, os

class MemoryMapObject:
    def __init__(self, name, data=""):
        self.name = name
        self.data = data

# Usage:
filename = 'TestCollection.mmap'
sample_obj = MemoryMapObject("SampleName", data="a" * 1000)
max_serialized_size = len(pickle.dumps(sample_obj))

if not os.path.exists(filename):
     with MemoryMap(filename, num_diagonal_elements=10, max_object_size=max_serialized_size) as storage:
         storage.set(5, MemoryMapObject("Nataliya"))
else:
    with MemoryMap(filename) as storage:
        #storage.set(3, MemoryMapObject("Nataliya"))
        name = 'The Abundant Champs'
        deck = storage.get(5)
        print(deck.name)