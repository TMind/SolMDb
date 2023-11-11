import mmap
import os
import pickle, json
import numpy as np
from Card_Library import Fusion

OBJ_SIZE = 65536
class NameIndex:
    def __init__(self):
        # 2D ndarray to store names and their corresponding position in the index
        self._data = np.empty((0, 2), dtype=object)  # Name, position in index

    def set(self, name, position):
        """Add a name and its corresponding position in the index to the ndarray."""
        if self.get_position_by_name(name):  # Ensure name is unique
            raise ValueError(f"Name '{name}' already exists in NameIndex.")
        new_entry = np.array([[name, position]])
        self._data = np.vstack([self._data, new_entry])

    def get_position_by_name(self, name):
        """Retrieve the position in the index of an object given its name."""
        rows = np.where(self._data[:, 0] == name)[0]
        return int(self._data[rows[0], 1]) if len(rows) > 0 else None

    def get_name_by_position(self, position):
        """Retrieve the name of an object given its position in the index."""
        rows = np.where(self._data[:, 1] == position)[0]
        return self._data[rows[0], 0] if len(rows) > 0 else None    

    def calculate_positions(self, name):
        names = name.split('_')
        positions = [self.get_position_by_name(name) for name in names]
        return positions

    def keys(self):
        """Return all the names stored in the NameIndex."""
        return self._data[:, 0].tolist()

    def __len__(self):
        return len(self._data)

    def __str__(self):
        return str(self._data)

class IndexFile:
    def __init__(self, filename, obj_size = OBJ_SIZE):
        self.filename = filename + '.idx.json'
        self.index = {}
        self.object_size = obj_size
        self.load()

    def load(self):
        """Load the index from a file."""
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                loaded_index = json.load(f)
                self.index = {tuple(map(int, key.strip('()').split(', '))): value for key, value in loaded_index.items()}
            self.object_size = self.get_max_object_size()

    def save(self):
        """Save the index to a file."""
        serialized_index = {str(key): value for key, value in sorted(self.index.items())}
        with open(self.filename, 'w') as f:
            json.dump(serialized_index, f, separators=(',', ':'))  # Compact JSON
 
    def add_entry(self, row, col, offsets):
        """Add an entry to the index."""        
        key = (row, col)
        self.index[key] = offsets
        self.save()

    def get_entry(self, row, col):
        """Retrieve the offsets for a given position."""
        return self.index.get((row, col))

    def __len__(self):
        return len(self.index)
    
    def items(self):
        return self.index.items()

    def get_max_object_size(self):
        # Extract all the offsets from the index
        offsets = [value[0] for value in self.index.values()] # Assuming value[0] is the offset of the object
        
        # Sort the offsets
        sorted_offsets = sorted(offsets)
        
        # Calculate the difference between any two consecutive offsets to get max_object_size
        if len(sorted_offsets) > 1:
            return sorted_offsets[1] - sorted_offsets[0]
        else:
            # Handle case where there's only one or no offsets in the index
            return OBJ_SIZE 

    def split_index_data(self, num_workers):
        """ Splits the index data into chunks for workers.
        
        Args:
            index_data (dict): The parsed index data.
            num_workers (int): The number of workers to split the data for.

        Returns:
            list: A list of index data chunks (each chunk is a dict).
        """
        
        # Convert the index data dictionary to a list of items for easy chunking
        index_items = list(self.index.items())
        # Calculate the size of each chunk
        chunk_size = len(index_items) // num_workers
        
        # Use a list comprehension to create chunks
        # Note: the last chunk will take the remaining items in case of an uneven split
        index_chunks = [dict(index_items[i * chunk_size:(i + 1) * chunk_size])
                        for i in range(num_workers)]
        
        # Add remaining items to the last chunk if the split isn't even
        remaining_items = len(index_items) % num_workers
        if remaining_items:
            index_chunks[-1].update(index_items[-chunk_size - remaining_items:])
        
        return index_chunks


    def remove(self):        
        os.remove(self.filename)
        self.filename = ''


class MemoryMap:
    def __init__(self, filename, num_rows=12, num_columns=12, max_object_size=OBJ_SIZE):
        self.filename = filename                
        self.index_file = IndexFile(filename)
        if self.index_file.index:            
            self.num_rows = len(self.index_file)
            self.num_columns = len(self.index_file)       
            self.max_object_size = self.index_file.get_max_object_size()
        else:
            # Store rows and columns
            self.num_rows = num_rows
            self.num_columns = num_columns            
            self.max_object_size = max_object_size or OBJ_SIZE
        self.name_index = NameIndex()
        
        expected_size = self.num_rows * self.num_columns * self.max_object_size
        if not os.path.exists(filename):
            # If file doesn't exist, or was deleted due to not finding an index, recreate everything
            self.file = open(filename, 'wb+')
            self.file.truncate(expected_size)
            self.mmap = mmap.mmap(self.file.fileno(), 0)
            self.index_file = IndexFile(filename)            
        else:
            # File exists, just load it
            self.file = open(filename, 'r+b')
            current_size = os.path.getsize(filename)

            if current_size != expected_size:
                if current_size > expected_size:
                    # If the new size is smaller, delete and recreate                    
                    self.file.close()
                    os.remove(filename) 
                    self.file = open(filename, 'wb+')
                    self.file.truncate(expected_size)
                    self.mmap = mmap.mmap(self.file.fileno(), 0)
                    self.index_file.remove()
                    self.index_file = IndexFile(filename)                    
                else:
                    # If the new size is bigger, simply extend the file
                    self.file.truncate(expected_size)
                    self.mmap = mmap.mmap(self.file.fileno(), 0)
                    # The index was already loaded at the start
            else:
                self.mmap = mmap.mmap(self.file.fileno(), 0)        
                # The index was already loaded at the start
        # Now, after mmap is initialized, synchronize with NameIndex
        self.ni_sync()

    def _flatten_position(self, row, col):
        """Convert 2D position to a 1D position."""
        return row * self.num_columns + col

    def _unflatten_position(self, position):
        """Convert 1D position to a 2D (row, col) position."""
        row = position // self.num_columns
        col = position % self.num_columns
        return row, col

    def get_slices(self, num_workers):
        mm_size = os.path.getsize(self.filename)
        chunk_size = mm_size // num_workers
        mm_chunks_offsets = []

        for i in range(num_workers):
            mm_chunk_offset_start = chunk_size * i
            mm_chunk_offset_end = mm_chunk_offset_start + chunk_size
            if i == num_workers - 1:  # Make sure to include the remainder in the last chunk
                mm_chunk_offset_end = mm_size
            mm_chunk_offsets = (mm_chunk_offset_start, mm_chunk_offset_end)
            mm_chunks_offsets.append(mm_chunk_offsets)

        return mm_chunks_offsets

    def set(self, row, col, obj):
        serialized = pickle.dumps(obj)
        size = len(serialized)
        if size > self.max_object_size:
            raise ValueError("Serialized object is larger than max object size.")
        
        flattened_position = row * self.num_columns + col
        offset = flattened_position * self.max_object_size
        
        self.mmap[offset:offset + self.max_object_size] = b'\0' * self.max_object_size
        self.mmap[offset:offset + size] = serialized        
        end_offset = offset + size
        
        self.index_file.add_entry(row, col, (offset, end_offset))
        # Update the NameIndex
        if hasattr(obj, "name"):
            self.name_index.set(obj.name, flattened_position)
        else:
            print(f"Object {obj} has no name attribute\n")        


    def _get_data(self, row, col, mode='unserialized'):
        """Private method to get the data for the given position, raw or pickled."""
        offsets = self.index_file.get_entry(row, col)
        if offsets is None:
            return None

        start_offset, end_offset = offsets
        data = self.mmap[start_offset:end_offset]
        if mode   == 'serialized':         return data
        elif mode == 'unserialized':       return pickle.loads(data)
        else:          raise ValueError(f"Unsupported mode: {mode}")

    def get(self, row, col, mode='unserialized'):        
        return self._get_data(row, col, mode)

    def get_diagonal(self, mode='unserialized'):
        diagonal = []
        for i in range(len(self)) :
            data = self.get(i,i,mode)
            if data is not None:
                diagonal.append(data)
        return diagonal
    
    def _find_next_available_slot(self):
        for i in range(self.num_rows):
            if self.index_file.get_entry(i, i) is None:
                return i, i
        raise ValueError("MemoryMap is full!")


    def __len__(self):
        return len(self.index_file)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        self.mmap.close()

    # Functions for NameIndex Interface

    def ni_sync(self):
        """Synchronize the NameIndex with the current mmap index."""
        for (row,col), offsets in self.index_file.items():            
            obj = self.get(row, col)
            if obj:
                pos = self._flatten_position(row, col)
                self.name_index.set(obj.name, pos)

    def ni_add(self, obj):
        # Check if the name already exists in the NameIndex
        if self.name_index.get_position_by_name(obj.name) is None:
            #raise ValueError(f"An object with name '{obj.name}' already exists in MemoryMap.")
            # Find the next available slot.
            # Since the slots are sequential and 0-indexed, the next available slot is just the current length of the MemoryMap.
            row, col = self._find_next_available_slot()
            # Use the `set` method to store the object
            self.set(row, col, obj)

    def ni_get(self,name):
        pos = self.name_index.get_position_by_name(name)
        row, col = self._unflatten_position(pos)
        return self.get(row, col)
    
    def add_fusion(self, fusion):
        decknames = fusion.name.split('_')

        # Get the position of each deck
        pos1 = self._unflatten_position(self.name_index.get_position_by_name(decknames[0]))
        pos2 = self._unflatten_position(self.name_index.get_position_by_name(decknames[1]))

        # Use the row of the first deck and the column of the second as the fusion's position
        fusion_row = pos1[0]
        fusion_col = pos2[1]

        # Store the fusion in the calculated position
        self.set(fusion_row, fusion_col, fusion)

    def ni_fuse(self, fusion_name):
        decknames = fusion_name.split('_')
        decks = [self.ni_get(deckname) for deckname in decknames]
        fusion = Fusion(decks)  # Assuming Fusion returns None if not a valid fusion
        return fusion


    def ni_keys(self):
        return self.name_index.keys()
    
    def ni_exists(self, name):
        return self.name_index.get_position_by_name(name)