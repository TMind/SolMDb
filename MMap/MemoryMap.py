import mmap
import os
import pickle
from MMap.MemoryIndex import MemoryIndex

class MemoryMap:

    DEFAULT_OBJ_SIZE = 65536  #Default maximum size for each object

    @staticmethod
    def calculate_map_size(num_objects, max_object_size=DEFAULT_OBJ_SIZE):
        """Calculate the required size of the memory map based on the number of objects and the maximum size of each object."""
        return num_objects * max_object_size

    def __init__(self, filename, num_objects=None, max_object_size=DEFAULT_OBJ_SIZE, start_offset=0, length=None):
        self.filename = filename
        self.max_object_size = max_object_size        
        self.index = MemoryIndex(filename + '.'+ start_offset  + '.json', num_objects)        
        self.map_size = self.calculate_map_size(num_objects or self.index.total_size, max_object_size)
        self.start_offset = start_offset
        self.length = length or self.map_size - self.start_offset  # Length of the mmap region
        #self.end_offset = end_offset or self.map_size
        self._open()


    def _open(self):
        # Ensure the file exists and is of the correct size
        if not os.path.exists(self.filename):
            # Create file and set it to the calculated map size
            with open(self.filename, 'wb') as f:
                f.truncate(self.map_size)
        # Open the existing file with the correct size
        self.file = open(self.filename, 'r+b')
        #self.mmap = mmap.mmap(self.file.fileno(), self.map_size)
        self.mmap = mmap.mmap(self.file.fileno(), length=self.length, offset=self.start_offset)

        

    def close(self):
        # Close the memory map and file
        self.mmap.close()
        self.file.close()

    def add_object(self, obj, identifier):
        """Adds a new object to the memory map and updates the index."""
        serialized_obj = pickle.dumps(obj)
        size = len(serialized_obj)

        if size > self.max_object_size:
            raise ValueError(f"Object size exceeds the maximum allowed size of {self.max_object_size} bytes.")

        # Find the next available offset based on the index
        next_offset = self.index.find_next_available_offset()
        if next_offset + size > self.start_offset + self.length:
            # Expand the memory map if there is not enough space
            raise ValueError("Not enough space in the assigned mmap region.")
            #self._expand_mmap(next_offset + size)

        # Write the object to the memory map at the next available offset
        self.mmap[next_offset - self.start_offset:next_offset - self.start_offset + size] = serialized_obj

        # Update the index with the new object's offset and size
        self.index.add_entry(identifier, (next_offset, next_offset + size))

    def get_object(self, identifier):
        # Get the start offset for the identifier from the index
        start_offset = self.index.get_offset(identifier)
        if start_offset is None:
            return None

        # Read the object from the memory map
        self.mmap.seek(start_offset)
        serialized_obj = self.mmap.read()  # You need to know the size of the object to read or have a delimiter
        return pickle.loads(serialized_obj)

    def _expand_mmap(self, new_size):
        """Expand the memory map to a new size."""
        # Close the current mmap and file
        self.mmap.close()
        self.file.close()

        # Open the file in append mode to change the file size
        with open(self.filename, 'ab') as f:
            f.truncate(new_size)

        # Re-open the file and mmap with the new size
        self._open()

    def __enter__(self):
        self._open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()