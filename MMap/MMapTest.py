from MMap.MemoryMap import MemoryMap

class MemoryMapObject:
    def __init__(self, name, data=""):
        self.name = name
        self.data = data

# Usage:
filename = 'TestCollection.mmap'
sample_obj = MemoryMapObject("SampleName", data="a" * 1000)

# Initialize the MemoryMap with the filename
# The size will be determined by the MemoryMap itself based on the existing file or provided upon creation
memory_map = MemoryMap(filename,10)

# Try to retrieve the object first to check if it exists
retrieved_obj = memory_map.get_object("SampleName")
if retrieved_obj:
    print(f"Retrieved object name: {retrieved_obj.name}")
else:
    print("Object not found. Adding new object.")
    # Add an object to the memory map
    memory_map.add_object(sample_obj, sample_obj.name)

# Always close the MemoryMap object
memory_map.close()
