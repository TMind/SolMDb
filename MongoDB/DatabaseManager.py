import importlib, os
from MongoDB.MongoDB import MongoDB
import pymongo
import pymongo.errors
from dataclasses import dataclass, fields, asdict
from typing import Any, Dict

# Global variable to hold the active BufferManager instance
_active_buffer_manager = None
class DatabaseManager:
    _instances = {}
    _credentials = None

    def __new__(cls, db_name = None, host='localhost', port=27017, uri=None, force_new=False):  
        if cls._credentials is None:  
            # Load from environment variables if not provided
            if host is None:
                host = os.getenv('MONGODB_HOST', 'localhost')
            if port is None:
                port = int(os.getenv('MONGODB_PORT', 27017))
            if uri is None:
                uri = os.getenv('MONGODB_URI')
                
            cls._credentials = {'host': host, 'port': port, 'uri': uri}  
  
        if db_name is None:  
            # Create an empty instance without a database name  
            print("DatabaseManager:new() : Database name not set. Call set_database_name first.")
            return super().__new__(cls)  
  
        if force_new or db_name not in cls._instances:  
            host, port, uri = cls._credentials.values()  
            if force_new:  
                new_instance = super().__new__(cls)  
                new_instance.mdb = MongoDB(db_name, host, port, uri)  
                return new_instance  
            else:  
                cls._instances[db_name] = super().__new__(cls)  
                cls._instances[db_name].mdb = MongoDB(db_name, host, port, uri)  
          
        return cls._instances[db_name]  
    
    def add_to_buffer(self, collection_name, identifier, data_to_save):
        global _active_buffer_manager
        if _active_buffer_manager:
            # Use the active buffer manager if it exists
            _active_buffer_manager.add_to_buffer(self.mdb.get_db_name(), collection_name, identifier, data_to_save)
        else:
            # Directly write to the database if no buffer manager is active
            self.bulk_write(collection_name, [pymongo.UpdateOne(identifier, {'$set': data_to_save}, upsert=True)])

    def set_database_name(self, db_name: str, host='localhost', port=27017, uri = None):        
        if not 'mdb' in self.__dict__: 
            if self._credentials is None:
                self._credentials = {'host': host, 'port': port, 'uri': uri}
            host, port, uri = self._credentials.values()
            self.mdb = MongoDB(db_name, host, port, uri)
        else:
            self.mdb.set_db(db_name)

    def get_current_db_name(self):
        return self.mdb.get_db_name()

    def __getattr__(self, attr):
        if 'mdb' in self.__dict__:
            mdb = self.__dict__['mdb']                                    
            return getattr(mdb, attr)
        raise AttributeError("Database name not set. Call set_database_name first.")

    # Database functions 
    def get_record_by_name(self, collection_name, name):
        #print(f"Getting record by name: {name} from db - collection: {self.get_current_db_name()} - {collection_name}")
        return self.find_one(collection_name, {'name': name})

class BufferManager:
    def __init__(self, uri, max_buffer_size=500):
        self.uri = uri
        self.buffers = {}
        self.max_buffer_size = max_buffer_size  # Maximum number of operations before automatic flush

    def add_to_buffer(self, database_name, collection_name, identifier, data_to_save):
        buffer_key = (database_name, collection_name)
        if buffer_key not in self.buffers:
            self.buffers[buffer_key] = []

        operation = pymongo.UpdateOne(identifier, {'$set': data_to_save}, upsert=True)
        self.buffers[buffer_key].append(operation)

        # Automatically flush the buffer if it exceeds the max_buffer_size
        if len(self.buffers[buffer_key]) >= self.max_buffer_size:
            self.write_buffer(database_name, collection_name)

    def write_buffer(self, database_name, collection_name):
        """Writes the current buffer for the given database and collection."""
        buffer_key = (database_name, collection_name)
        if buffer_key in self.buffers and self.buffers[buffer_key]:
            db = DatabaseManager(database_name)
            db.bulk_write(collection_name, self.buffers[buffer_key])
            self.buffers[buffer_key] = []  # Clear the buffer after writing

    def write_buffers(self):
        """Writes all buffers across all database and collection combinations."""
        for (database_name, collection_name) in list(self.buffers.keys()):
            self.write_buffer(database_name, collection_name)

    def __enter__(self):
        global _active_buffer_manager
        _active_buffer_manager = self  # Activate this buffer manager
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write_buffers()  # Write all buffered data on exit
        global _active_buffer_manager
        _active_buffer_manager = None  # Deactivate the buffer manager

class DatabaseObject:
    _db_manager = None

    @property
    def db_manager(self):
        if self._db_manager is None:
            # Determine the database name based on data class
            data_class = self.get_data_class()
            if data_class.__name__ in ['EntityData', 'ForgebornData', 'InterfaceData','SynergyData']:
                self.db_name = 'common'
            else:
                self.db_name = os.getenv('SFF_USERNAME', None)
                if self.db_name is None:
                    self.db_name ='user_specific'
                    raise ValueError("Database name not set. Call set_database_name first.")
            
            # Initialize the db_manager for this instance
            self._db_manager = DatabaseManager(self.db_name)
        
        return self._db_manager


    def __init__(self, data=None):
    
        data_class = self.get_data_class()

        #print(f"Data class: {data_class}, Data: {data}, Type of Data: {type(data)}")

        if data_class is not None and isinstance(data, data_class):
            self.data = data            
        else:
            self.data = None

        if data_class.__name__ in ['EntityData', 'ForgebornData', 'InterfaceData', 'SynergyData']:
            self.db_name = 'common'
        else:
            self.db_name = os.getenv('SFF_USERNAME', None)
            
            if self.db_name is None:
                self.db_name ='user_specific'
                raise ValueError("DatabaseObject:init() Database name not set. Set username first.")
            
        if self.db_manager:
                self.db_manager.set_database_name(self.db_name)

    def get_data_class(self):
        if self.__class__.DataClass is None:
            module_name = self.__class__.__module__
            module = importlib.import_module(module_name)
            data_class_name = self.__class__.__name__ + "Data"
            self.__class__.DataClass = getattr(module, data_class_name)
        return self.__class__.DataClass

    @classmethod
    def _get_class_db_manager(cls):
        username = os.getenv('SFF_USERNAME', None)
        db_name = 'common' if cls.__name__ in ['Entity', 'Forgeborn', 'Interface', 'Synergy'] else username
        return DatabaseManager(db_name)


    @classmethod
    def from_data(cls, data: Dict[str, Any]):
        
        # Get DataClass and get the fields from the dataclass
        dataclass = cls(None).get_data_class()
        dataclass_fields = {field.name for field in fields(dataclass)}

        # Extract valid data and extra data
        valid_data = {k: v for k, v in data.items() if k in dataclass_fields}
        extra_data = {k: v for k, v in data.items() if k not in dataclass_fields}
        
        # Create an instance with the valid data as dataclass
        instance = cls(dataclass(**valid_data)) if valid_data else cls()

        # If there's extra data, handle it as needed (e.g., store in a specific attribute)
        if extra_data:
            instance.extra_data = extra_data

        return instance

    DataClass = None
    extra_data = None  # Placeholder for extra data

    def __getattr__(self, name):
        # Check if the attribute exists as a member variable
        if name in self.__dict__:
            return self.__dict__[name]
                
        # If not found, check if it exists in the data dictionary
        if 'data' in self.__dict__:
            data = self.__dict__['data']
            if isinstance(data, dict) and name in data:                
                return data[name]
            elif hasattr(data, name):
                return getattr(data, name)
        
        #print(f"{self.__class__.__name__} object has no attribute '{name}'")            
        return None
    
    def save(self, collection_name=None):
        collection_name = collection_name or self.__class__.__name__
        data = self.to_data()
        data_to_save = data if isinstance(data, dict) else vars(data)
        # Exclude '_id' from data_to_save if it's None or an empty string
        if '_id' in data_to_save and (data_to_save['_id'] == '' or data_to_save['_id'] is None):
            del data_to_save['_id']
        identifier = {'_id': self._id} if hasattr(self, '_id') and self._id not in [None, ''] else {'name': self.name}
        self.db_manager.add_to_buffer(collection_name, identifier, data_to_save)

    def to_data(self):        
        if isinstance(self.data, dict):            
            return self.data
        elif self.data is not None:
            return asdict(self.data)        
        
    @classmethod
    def get_instance(cls, name, field='_id', collection_name=None):
        """
        Retrieves an instance from the database based on the identifier type.
        
        Args:
            name (str): The identifier for the object to be retrieved.
            type (str): The type of identifier ('_id' for ID-based lookup or 'name' for name-based lookup). 
                        Default is '_id'.
            collection_name (str, optional): The name of the collection. Default is the class name.
        
        Returns:
            instance or None: The retrieved instance, or None if not found.
        """
        db_manager = cls._get_class_db_manager()
        collection_name = collection_name or cls.__name__
        data = db_manager.find_one(collection_name, {field : name})

        if data:
            return cls.from_data(data)
        else:
            dbname = db_manager.get_current_db_name()
            print(f"{cls.__name__} with {field} = {name} not found in the database {dbname}.")
            return None
        
    @classmethod
    def lookup(cls, name, type='_id', collection_name=None):
        db_manager = cls._get_class_db_manager()
        collection_name = collection_name or cls.__name__
        data = db_manager.find_one(collection_name, {type : name})
        
        if data:    return cls.from_data(data)
        else:       
            dbname = db_manager.get_current_db_name()
            print(f"{cls.__name__} with {type} = {name} not found in the database {dbname} .")
            return None    

    @classmethod
    def load(cls, name, collection_name=None):
        db_manager = cls._get_class_db_manager()
        collection_name = collection_name or cls.__name__
        data = db_manager.get_record_by_name(collection_name, name)
        
        if data:    return cls.from_data(data)
        else:       return None
    
    def getClassPath(self):
        return self.__module__ + '.' + self.__class__.__name__


   
            
        