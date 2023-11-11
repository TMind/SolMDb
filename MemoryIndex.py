import json
import os
import pickle
import numpy as np

class MemoryIndex:
    def __init__(self, filename, obj_size=65536):
        self.filename = filename + '.idx.json'
        self.index_offsets = {}
        self.index_names = {}
        self.object_size = obj_size
        self.load()

    def load(self):
        """Load the index from a file."""
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                loaded_index = json.load(f)
                # Assuming the index file has a structure with keys as "(row, col)" strings and values as [start_offset, end_offset]
                self.index_offsets = {tuple(map(int, key.strip('()').split(', '))): value for key, value in loaded_index.items()}
                # Extract and store names if available (you might need to adjust this based on your actual data structure)
                self.index_names = {self.get_name_from_data(value): key for key, value in self.index_offsets.items()}

    def get_name_from_data(self, data):
        """Extract name from serialized data. Implement this based on how names are stored in your objects."""
        # This is a placeholder function. You need to implement the logic based on your data structure.
        obj = pickle.loads(data)
        return obj.name

    def get_by_name(self, name):
        """Retrieve the position and offsets of an object given its name."""
        position = self.index_names.get(name)
        if position is not None:
            return self.index_offsets[position]
        return None

    def get_by_position(self, position):
        """Retrieve the offsets for a given position."""
        return self.index_offsets.get(position)

    def get(self, identifier):
        """General get method that can handle both names and position tuples."""
        if isinstance(identifier, str):
            return self.get_by_name(identifier)
        elif isinstance(identifier, tuple):
            return self.get_by_position(identifier)
        else:
            raise ValueError("Identifier must be a name (str) or position (tuple).")

    def set(self, name, position, offsets):
        """Set the index entry for a given name and position."""
        if position in self.index_offsets:
            raise ValueError(f"Position {position} is already used.")
        if name in self.index_names:
            raise ValueError(f"Name {name} is already used.")
        self.index_offsets[position] = offsets
        self.index_names[name] = position
        self.save()

    def save(self):
        """Save the index to a file."""
        serialized_index = {str(key): value for key, value in sorted(self.index_offsets.items())}
        with open(self.filename, 'w') as f:
            json.dump(serialized_index, f, separators=(',', ':'))

    # ... additional methods as needed ...
