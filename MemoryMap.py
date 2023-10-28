import numpy as np
import pickle, json
import os
from Card_Library import Fusion
from memory_profiler import profile

class MemoryMapManager:

    # Manages the Memory Map 
    def __init__(self, filename, length=100):
        self.filename = filename
        self.object_dtype = 'object'
        self.memory_map = None
        self.index = {}
        self.length = length
        self.shape = (length,length)
        self._load()
        self._open(self.shape)

    def __del__(self):
        if self.memory_map is not None:
            self._save()
            del self.memory_map

    def _open(self, shape):
        
        if os.path.exists(self.filename):        
            # Load existing map 
            self.memory_map = np.memmap(self.filename, dtype=self.object_dtype, mode='r+', shape=self.shape)
        else:        
            # Create new map with specified shape 
            self.shape = shape
            self.memory_map = np.memmap(self.filename, dtype=self.object_dtype, mode='w+', shape=self.shape)
            
        # If a shape is provided and it's larger than the existing shape, resize the memory map
        if shape > self.shape:
            self._resize(shape)        

        #return self.memory_map

    def _save(self):
        if self.memory_map is not None:
            self.memory_map.flush()

            # Save the class object, including index and shape
            data = {
                "index": self.index,
                "shape": self.shape
            }

            # Pickle the entire class object and save it
            with open(f"{self.filename}.json", "w") as obj_file:
                json.dump(data, obj_file)
        else:
            raise ValueError("Memory map is not initialized.")

    def _load(self):
        try:
            with open(f"{self.filename}.json", "r") as obj_file:
                data = json.load(obj_file)
                self.index = data.get("index", {})
                self.shape = tuple(data.get("shape", (self.length, self.length)))

        except FileNotFoundError:
            # Handle the case where the index file doesn't exist yet
            #self.shape = (100, 100)  # Default shape
            return

    def _resize(self, new_shape):
            if self.memory_map is not None:
                current_shape = self.memory_map.shape
                if new_shape != current_shape:
                    # Create a temporary MemoryMapManager for resizing
                    with MemoryMapManager(self.filename + ".tmp", self.object_dtype) as new_memory_map:
                        new_memory_map.open(new_shape)  # Create the new memory map
                                            
                    # Copy data from the current memory map to the new one
                        min_rows = min(current_shape[0], new_shape[0])
                        min_cols = min(current_shape[1], new_shape[1])
                        new_memory_map.memory_map[:min_rows, :min_cols] = self.memory_map[:min_rows, :min_cols]

                        # Close the new memory map 
                        new_memory_map.close()  
                    self.__del__()

                    # Update the shape attribute
                    self.shape = new_shape

                    # Rename the temporary memory-mapped file to the original filename
                    os.rename(new_memory_map.filename, self.filename)
                    os.remove(new_memory_map.filename)

                    self._open(self.shape)

                else:
                    print("Memory map already has the specified shape.")
            else:
                raise ValueError("Memory map is not initialized.")

    def _nameToIndex(self, name):
        indices = ()
        # Handle Fusion objects by splitting their name and finding indices for each part
        titles = name.split('_')
        if len(titles) == 1:
            titles.append(titles[0])
        for title in titles:
            if title in self.index:
                indices = indices + (self.index[title][0],)  # Note the comma
            else:
                raise ValueError(f"Name part '{title}' not found in the index.")
        return tuple(indices)            

# Works with single Decks 
    def add(self, obj, key=None):
        if self.memory_map is not None:
            if not key:
            # Check if the object has a 'name' attribute
                if hasattr(obj, 'name'):
                    key = obj.name
                else:            
                    raise ValueError("Object must have a 'name' attribute.")
                
            serialized_object = serialize(obj)    
            if not self.index.get(key, None):
                # Construct Indices
                indices = []
                if isinstance(obj, Fusion):
                    # Handle Fusion objects by splitting their name and finding indices for each part
                    parts = obj.name.split('_')
                    for part in parts:
                        if part in self.index:
                            indices.append(self.index[part][0])
                        else:
                            raise ValueError(f"Name part '{part}' not found in the index.")
                else:
                    # For other objects, use the 'name' attribute as the key in the index dictionary
                    index = len(self.index)  # The next available index
                    indices = (index, index)
                    self.index[obj.name] = indices

                # Store the object in the memory-mapped array at the corresponding indices
                self.memory_map[indices] = serialized_object

            else:
                index = self.index[key]
                self.memory_map[index] = serialized_object
                #print(f"Object already indexed {obj.name}")
        else:
            raise ValueError("Add: Memory map is not initialized.")

    def update(self, objects):
        if self.memory_map is not None:
            for object in objects:
                self.add(object)
        else:
            raise ValueError("Update: Memory map is not initialized.")
        
    @profile
    def _get(self, name):
        if self.memory_map is not None:
            index = self._nameToIndex(name)
            if index:                
                return deserialize(self.memory_map[index])
            else:
                raise ValueError(f"Object with name '{name}' not found in the index.")
        else:
            raise ValueError("Memory map is not initialized.")


# Returns Objects from the Memory Map 

    def objects(self):
        object_list = []
        for index in self.index:
            obj = self._get(index) 
            object_list.append(obj)
        return object_list

    def print_index(self):
        print("Index List:")
        for i, item in self.index.items():
            print(f"Index {i}: {item}")
    
# Implement the dictionary-like methods

    def __getitem__(self, key):
        return self._get(key)

    def __setitem__(self, key, value):
        self.add(value, key)

    def __delitem__(self, key):
        if key in self.index:
            del self.index[key]
        else:
            raise KeyError(f"Key '{key}' not found in index.")

    def __len__(self):
        return len(self.index)

    def __iter__(self):
        return iter(self.index)

    def keys(self):
        return self.index.keys()

    def values(self):
        return self.index.values()

    def items(self):
        return self.index.items()

def deserialize(object):
    try:
        deserialized_object = pickle.loads(object)  # Try to deserialize with pickle
        return deserialized_object                  # The object is deserializable
    except (TypeError, pickle.UnpicklingError):
        return object     

def serialize(object):
    try:
        serialized_object = pickle.dumps(object)  # Try to serialize with pickle
        return serialized_object                  # The object is serializable
    except (TypeError, pickle.PickleError):
        return object  

