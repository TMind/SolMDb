import os
import zlib
import base64
from tqdm import tqdm
import pickle
from pickle import Unpickler

class CacheManager:

    CHUNK_SIZE = 1024 * 1024  # 1 MB chunk size (adjust as needed)

    def __init__(self, file_paths, dependencies):
        self.file_paths = file_paths
        self.dependencies = dependencies

    def get_filepath(self, keyword):
        return self.file_paths.get(keyword, None)

    def get_dependencies(self, keyword):
        return self.dependencies.get(keyword, None)

    def load_or_create(self, keyword, create_func):
        file_path = self.get_filepath(keyword)
        obj = self.load_object_from_cache(file_path)

        if obj is None or self.is_cache_invalid(keyword): # Notice we use keyword here
            obj = create_func()
            self.save_object_to_cache(file_path, obj)

        return obj


    def load_object_from_cache(self, keyword_or_path):
        # Convert keyword to file path if needed
        file_path = self.get_filepath(keyword_or_path) if keyword_or_path in self.file_paths else keyword_or_path
        
        obj = None
        if os.path.exists(file_path):
            with open(file_path, "rb") as file:
                base64_encoded_obj = file.read()
                compressed_obj = base64.b64decode(base64_encoded_obj)                
                serialized_obj = decompress_with_progress(compressed_obj)
                bytes_reader = BytesReaderWrapper(serialized_obj)
                with TQDMBytesReader(bytes_reader, desc=f'Unpickle {os.path.basename(file_path)}', total=len(serialized_obj), colour='BLUE', unit='B', unit_scale=True) as pbfd:                
                    up = Unpickler(pbfd)
                    obj = up.load()                                
        return obj



    def save_object_to_cache(self, keyword_or_path, obj):
        file_path = self.get_filepath(keyword_or_path) if keyword_or_path in self.file_paths else keyword_or_path
        
        if file_path is None:
            raise ValueError(f"No file path associated with the keyword: {keyword_or_path}")
            
        with open(file_path, "wb") as file:
            serialized_obj = pickle.dumps(obj)
            compressed_obj = zlib.compress(serialized_obj)            
            base64_encoded_obj = base64.b64encode(compressed_obj)
            file.write(base64_encoded_obj)


    def is_cache_invalid(self, keyword):
        # Helper function to get the path from a dependency
        def get_path_from_dependency(dep):
            # If the dependency is a keyword, return its associated file path
            # Otherwise, assume it's a direct path and return it as is
            return self.get_filepath(dep) if dep in self.file_paths else dep

        # First, retrieve the dependencies for the given keyword
        dependencies_keywords_and_paths = self.get_dependencies(keyword)
        
        # Convert these to actual file paths
        dependencies_filepaths = [get_path_from_dependency(dep) for dep in dependencies_keywords_and_paths]

        # If the keyword itself represents a cache file, add its modification time to the list
        pickle_mod_time = os.path.getmtime(self.get_filepath(keyword))

        # Get the modification times of the dependencies
        dep_mod_times = [os.path.getmtime(dep_filepath) for dep_filepath in dependencies_filepaths]

        # Check if any dependency has a modification time later than the pickle file
        return any(dep_mod_time > pickle_mod_time for dep_mod_time in dep_mod_times)




    def clear_dependencies(self, keyword):
        # First, retrieve the dependencies for the given keyword
        dependencies = self.get_dependencies(keyword)

        # If the keyword itself represents a cache file, add it to the list of files to remove
        files_to_remove = [self.get_filepath(keyword)] + dependencies

        for file_path in files_to_remove:
            self.remove_cache_file(file_path)


    def remove_cache_file(self, file_path):
        if os.path.exists(file_path):
            os.remove(file_path)

class BytesReaderWrapper:
    def __init__(self, serialized_obj):
        self.data = serialized_obj
        self.offset = 0

    def read(self, size=-1):
        result = self.data[self.offset:self.offset + size]
        self.offset += len(result)
        return result

class TQDMBytesReader(object):

    def __init__(self, fd, **kwargs):
        self.fd = fd
        from tqdm import tqdm
        self.tqdm = tqdm(**kwargs)

    def read(self, size=-1):
        bytes = self.fd.read(size)
        self.tqdm.update(len(bytes))
        return bytes

    def readline(self):
        bytes = self.fd.readline()
        self.tqdm.update(len(bytes))
        return bytes

    def __enter__(self):
        self.tqdm.__enter__()
        return self

    def __exit__(self, *args, **kwargs):
        return self.tqdm.__exit__(*args, **kwargs)


def decompress_with_progress(compressed_data, chunk_size=8192):
    decompressor = zlib.decompressobj()
    decompressed_data = bytearray()
    
    total_bytes = len(compressed_data)
    processed_bytes = 0

    with tqdm(total=total_bytes, desc="Decompressing", unit="B", unit_scale=True, colour='RED') as progress_bar:
        for i in range(0, total_bytes, chunk_size):
            chunk = compressed_data[i:i + chunk_size]
            decompressed_chunk = decompressor.decompress(chunk)
            decompressed_data.extend(decompressed_chunk)
            processed_bytes += len(chunk)
            progress_bar.update(len(chunk))

    remaining_data = decompressor.flush()
    decompressed_data.extend(remaining_data)

    return bytes(decompressed_data)