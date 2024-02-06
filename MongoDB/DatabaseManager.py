import importlib
from math import e
from MongoDB.MongoDB import MongoDB
import GlobalVariables
from dataclasses import dataclass, fields, asdict
from typing import Any, Dict


class DatabaseManager:
    _instances = {}

    def __new__(cls, db_name: str = None, host='localhost', port=27017):
        if db_name is None:
            # Create an empty instance without a database name
            return super().__new__(cls)

        if db_name not in cls._instances:
            cls._instances[db_name] = super().__new__(cls)
            cls._instances[db_name].set_database_name(db_name, host, port)
        return cls._instances[db_name]

    def set_database_name(self, db_name: str, host='localhost', port=27017):
        if not 'mdb' in self.__dict__: 
            self.mdb = MongoDB(db_name, host, port)
        else:
            self.mdb.set_db(db_name)

    def __getattr__(self, attr):
        if 'mdb' in self.__dict__:
            mdb = self.__dict__['mdb']                                    
            return getattr(mdb, attr)
        raise AttributeError("Database name not set. Call set_database_name first.")

    # Database functions 
    def get_record_by_name(self, collection_name, name):
        return self.find_one(collection_name, {'name': name})

class DatabaseObject:
    _db_manager = None

    @property
    def db_manager(self):
        if self._db_manager is None:
            # Determine the database name based on data class
            data_class = self.get_data_class()
            if data_class.__name__ in ['EntityData', 'ForgebornData', 'CardData']:
                self.db_name = 'local'
            else:
                self.db_name = GlobalVariables.username or 'user_specific'
            
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

        if data_class.__name__ in ['EntityData', 'ForgebornData', 'CardData']:
            self.db_name = 'local'
        else:
            self.db_name = GlobalVariables.username or 'user_specific'

        if self.db_manager:
                self.db_manager.set_database_name(self.db_name)

    def get_data_class(self):
        if self.__class__.DataClass is None:
            module_name = self.__class__.__module__
            module = importlib.import_module(module_name)
            data_class_name = self.__class__.__name__ + "Data"
            self.__class__.DataClass = getattr(module, data_class_name)
        return self.__class__.DataClass

    #@classmethod
    #def initialize_db_manager(cls):
    #    if cls.db_manager is None:
    #        cls.db_manager = DatabaseManager(GlobalVariables.username or 'Default')

    @classmethod
    def _get_class_db_manager(cls):
        db_name = 'local' if cls.__name__ in ['Entity', 'Forgeborn', 'Card'] else GlobalVariables.username or 'user_specific'
        return DatabaseManager(db_name)


    @classmethod
    def from_data(cls, data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise TypeError("data must be a dict")
        
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
    
    def get_collection(self):
        # Import here to avoid circular imports
        from Interface import InterfaceCollection
        
        data = None        
        object = self
        if not isinstance(object, InterfaceCollection):
            classname = object.__class__.__name__
            if classname == 'Fusion':
                object = InterfaceCollection.from_deck(self)
            if classname == 'Entity':
                object = InterfaceCollection.from_entities(self.name, [self])
            if classname == 'Forgeborn':
                object = InterfaceCollection.from_forgeborn(self.id)
            if classname == 'Deck':
                object = InterfaceCollection.from_deck(self)
            if classname == 'Card':
                object = InterfaceCollection.from_card(self)
            else:
                object = None
        return object 


    def save(self, name, collection_name=None):
        collection_name = collection_name or self.__class__.__name__
        data_to_save = self.to_data() if isinstance(self.to_data(), dict) else vars(self.to_data())
        #DatabaseObject.db_manager.upsert(collection_name, {'name' : name }, data_to_save)     
        self.db_manager.upsert(collection_name, {'name' : name }, data_to_save)     


    def to_data(self):
        if isinstance(self.data, dict):
            return self.data
        elif self.data is not None:
            return asdict(self.data)        
        
    @classmethod
    def lookup(cls, name, type='name', collection_name=None):
        db_manager = cls._get_class_db_manager()
        collection_name = collection_name or cls.__name__
        data = db_manager.find_one(collection_name, {type: name})
        if data:    return cls.from_data(data)
        else:       return None    

    @classmethod
    def load(cls, name, collection_name=None):
        db_manager = cls._get_class_db_manager()
        collection_name = collection_name or cls.__name__
        data = db_manager.get_record_by_name(collection_name, name)
        
        if data:    return cls.from_data(data)
        else:       return None
        
#Initialize the DatabaseManager 
#DatabaseObject.initialize_db_manager()