import os
import zlib
import base64
from tqdm import tqdm
import pickle
from pickle import Unpickler

class CacheManager:

    CHUNK_SIZE = 1024 * 1024  # 1 MB chunk size (adjust as needed)

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
                base64_encoded_obj = file.read()
                compressed_obj = base64.b64decode(base64_encoded_obj)                
                serialized_obj = decompress_with_progress(compressed_obj)
                bytes_reader = BytesReaderWrapper(serialized_obj)
                with TQDMBytesReader(bytes_reader, desc='Unpickle', total=len(serialized_obj), colour='BLUE', unit='B', unit_scale=True) as pbfd:                
                    up = Unpickler(pbfd)
                    obj = up.load()                                
        return obj


    def save_object_to_cache(self, file_path, obj):
        with open(file_path, "wb") as file:
            serialized_obj = pickle.dumps(obj)
            compressed_obj = zlib.compress(serialized_obj)            
            base64_encoded_obj = base64.b64encode(compressed_obj)
            file.write(base64_encoded_obj)

    def is_cache_invalid(self, file_path):
        csv_mod_times = [os.path.getmtime(path) for path in self.file_mappings[file_path]]
        pickle_mod_time = os.path.getmtime(file_path)
        return any(csv_mod_time > pickle_mod_time for csv_mod_time in csv_mod_times)

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

    with tqdm(total=total_bytes, desc="Decompressing", unit="B", unit_scale=True) as progress_bar:
        for i in range(0, total_bytes, chunk_size):
            chunk = compressed_data[i:i + chunk_size]
            decompressed_chunk = decompressor.decompress(chunk)
            decompressed_data.extend(decompressed_chunk)
            processed_bytes += len(chunk)
            progress_bar.update(len(chunk))

    remaining_data = decompressor.flush()
    decompressed_data.extend(remaining_data)

    return bytes(decompressed_data)