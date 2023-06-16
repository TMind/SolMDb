import os
import pickle

class CacheManager:
    def __init__(self, file_mappings):
        self.file_mappings = file_mappings

    def load_or_create(self, file_path, create_func):
        obj = self.load_object_from_cache(file_path)

        if obj is None or self.is_cache_invalid(file_path):
            obj = create_func()
            self.save_object_to_cache(file_path, obj)

        return obj

    def load_object_from_cache(self, file_path):
        obj = None
        if os.path.exists(file_path):
            with open(file_path, "rb") as file:
                obj = pickle.load(file)
        return obj

    def save_object_to_cache(self, file_path, obj):
        with open(file_path, "wb") as file:
            pickle.dump(obj, file)

    def is_cache_invalid(self, file_path):
        csv_mod_time = os.path.getmtime(self.file_mappings[file_path])
        pickle_mod_time = os.path.getmtime(file_path)
        return csv_mod_time > pickle_mod_time

    def clear_dependencies(self, file_path):
        dependent_files = [file_path]
        for dep_file, csv_file in self.file_mappings.items():
            if file_path == csv_file:
                dependent_files.append(dep_file)
        for dep_file in dependent_files:
            self.remove_cache_file(dep_file)

    def remove_cache_file(self, file_path):
        if os.path.exists(file_path):
            os.remove(file_path)
