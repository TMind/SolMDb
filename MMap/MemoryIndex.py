import json
import os

class MemoryIndex:
    def __init__(self, index_filename, start_offset, end_offset=None):
        self.index_filename = f"{index_filename}.idx.{start_offset}.json"
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.total_size = self.end_offset - self.start_offset
        self.index = {}
       # self.total_size = num_objects # Set to None if not provided
        self.load()

    def load(self):
        if os.path.exists(self.index_filename):           
            with open(self.index_filename, 'r') as f:
                index_data = json.load(f)
                self.index = index_data.get("objects", {})
                self.start_offset = index_data.get("start_offset", 0)
                self.end_offset   = index_data.get("end_offset", None)
                self.total_size = index_data.get("total_size", self.total_size)
        else:
            self.save()

    def save(self):
        index_data = {
            "objects": self.index,
            "start_offset" : self.start_offset,
            "end_offset" : self.end_offset,
            "total_size": self.total_size
        }
        with open(self.index_filename, 'w') as f:
            json.dump(index_data, f, separators=(',', ':'))

    def add_entry(self, identifier, offset):
        if identifier in self.index:
            raise ValueError(f"Identifier '{identifier}' already exists.")
        self.index[identifier] = offset
        self.save()

    def remove_entry(self, identifier):
        if identifier in self.index:
            del self.index[identifier]
            self.save()

    def get_offset(self, identifier):
        entry = self.index.get(identifier)
        if entry:
            return entry[0]  # Return only the start offset
        return None

    def find_next_available_offset(self):
        """Finds the next available offset in the mmap to write a new object."""
        if not self.index:
            return 0  # If the index is empty, start at the beginning

        # Assuming the index is a dictionary with keys as identifiers and values as (offset, end) tuples
        _, last_end_offset = max(self.index.values(), key=lambda x: x[1])
        return last_end_offset  # The next offset is right after the last object's end


    def get_all_identifiers(self):
        return list(self.index.keys())