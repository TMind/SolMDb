import importlib
from MongoDB.MongoDB import MongoDB
from MyGraph import MyGraph
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
            if data_class.__name__ in ['EntityData', 'ForgebornData', 'CardData','InterfaceData','SynergyData']:
                self.db_name = 'local'
            else:
                if GlobalVariables.username: 
                    self.db_name = GlobalVariables.username 
                else:
                    self.db_name ='user_specific'
            
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

        if data_class.__name__ in ['EntityData', 'ForgebornData', 'CardData', 'InterfaceData', 'SynergyData']:
            self.db_name = 'local'
        else:
            if GlobalVariables.username: 
                self.db_name = GlobalVariables.username 
            else:
                self.db_name ='user_specific'
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
        db_name = 'local' if cls.__name__ in ['Entity', 'Forgeborn', 'Card', 'Interface', 'Synergy'] else GlobalVariables.username or 'user_specific'
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
    
    def save(self, collection_name=None):
        collection_name = collection_name or self.__class__.__name__
        data = self.to_data()
        data_to_save = data if isinstance(data, dict) else vars(data)
        # Exclude '_id' from data_to_save if it's None or an empty string
        if '_id' in data_to_save and (data_to_save['_id'] == '' or data_to_save['_id'] is None):
            del data_to_save['_id']
        identifier = {'_id': self._id} if hasattr(self, '_id') and self._id not in [None, ''] else {'name': self.name}
        self.db_manager.upsert(collection_name, identifier, data_to_save)     


    def to_data(self):        
        if isinstance(self.data, dict):            
            return self.data
        elif self.data is not None:
            return asdict(self.data)        
        
    @classmethod
    def lookup(cls, name, type='_id', collection_name=None):
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
    
    def getClassPath(self):
        return self.__module__ + '.' + self.__class__.__name__

    def hash_children(self):
        myHash = {}
        if self.children_data:
            for child_name, full_class_path in self.children_data.items():
                
                # Assume full_class_path is in the format "module_name.ClassName"
                if '.' not in full_class_path:
                    print(f"No Module found: {child_name} {full_class_path}")
                    return full_class_path                  

                module_name, class_name = full_class_path.rsplit('.', 1)  # Split on last dot
                   
                try:
                    module = importlib.import_module(module_name)
                    cls = getattr(module, class_name)
                except (ModuleNotFoundError, AttributeError) as e:
                    print(f"Error loading {full_class_path}: {e}")
                    continue                    
                # Assuming lookup is a class method that returns an instance or None
                if class_name == 'Synergy': 
                    child_object = cls.load(child_name)                        
                    myHash.setdefault(class_name, {})['Input']  = child_object.input_tags
                    myHash.setdefault(class_name, {})['Output'] = child_object.output_tags
                    return myHash
                else:
                    child_object = cls.lookup(child_name)
            
                if child_object:                    
                    # Add or update the child_name key under child_type
                    # Ensure child_type dict exists, initializing as an empty dict if not
                    myHash.setdefault(class_name, {})[child_name] = child_object.hash_children()
                    
        return myHash
        
    def create_graph_children(self, G=None, parent=None, currentType=None):        
        if G is None:
            G = MyGraph(self)
            parent = self

        def get_class_from_path(full_class_path):
            if '.' not in full_class_path:
                print(f"No Module found: {full_class_path}")
                return None, None

            module_name, class_name = full_class_path.rsplit('.', 1)  # Split on last dot

            try:
                module = importlib.import_module(module_name)
                cls = getattr(module, class_name)
                return cls, class_name
            except (ModuleNotFoundError, AttributeError) as e:
                print(f"Error loading {full_class_path}: {e}")
                return None, None

        if self.children_data:
            for child_name, full_class_path in self.children_data.items():
                color = '#97c2fc'
                # Assume full_class_path is in the format "module_name.ClassName"
                
                cls , class_name = get_class_from_path(full_class_path)
                if not cls or not class_name: continue

                if class_name == 'Synergy': 
                    # Change child_object appearance
                    child_object = cls.load(child_name)
                    G.add_node(child_object, color='greenyellow')
                    G.add_edge(parent, child_object)  
                    nodeId = G.get_nodeId(child_object)
                    G.G.nodes[nodeId]['shape'] = 'diamond'

                    return G                                              

                # Assuming lookup is a class method that returns an instance or None
                child_object = cls.lookup(child_name)
            
                if child_object:

                    if class_name == 'Entity' and currentType == 'Card' :
                        child_object.create_graph_children(G, parent, currentType)
                        return G

                    if class_name == 'Interface':             
                        #color = 0x0
                        #MyNode['shape'] = 'circle'
                        if 'O' in child_object.types:
                            color = "gainsboro" #color | 0xcc00
                        if 'I' in child_object.types: 
                            color = "gold" #color | 0xcc0000
                        
                    # Add the child_object as a node and connect it to the parent                    
                    elif class_name == 'Card':     color = 'skyblue'
                    elif class_name == 'Fusion': color = 'violet'
                    elif class_name == 'Deck':   color = 'cornflowerblue'                    
                    else : color = '#97c2fc'
                    
                    # Add child_object to Graph 
                    G.add_node(child_object, color=color, title=class_name)
                    G.add_edge(parent, child_object)  # Connect the child_object to its parent

                    MyNode = G.G.nodes[G.get_nodeId(child_object)]                

                    # Add parent to child's parents list
                    MyNode.setdefault('parents', [])
                    MyNode['parents'].append(G.get_nodeId(parent))

                    #print(f"Adding {G.get_nodeId(parent)} -> {G.get_nodeId(child_object)} \n")

                    # Recursively create the graph for the child_object
                    child_object.create_graph_children(G, child_object, class_name)  # Pass the child_object as the new parent                    
                    
        return G


   
            
        