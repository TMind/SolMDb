from more_itertools import value_chain
from dataclasses import dataclass, field
from Synergy import SynergyTemplate
from CardLibrary import Entity, Deck, Card
from dataclasses import field
from typing import List

@dataclass 
class InterfaceCollectionData:
    name: str
    interfaces: dict = field(default_factory=dict)

class InterfaceCollection:
    def __init__(self, name):
        self.name = name
        self.interfaces = {}
        self._cache = {}  # Initialize the cache dictionary
        
        synergy_template = SynergyTemplate()  # Instantiate only once here
        self.synergies = synergy_template.synergies

        if self.synergies:
            self.interfaces = {syn: {} for syn in self.synergies}        

    @classmethod
    def from_interfaces(cls, name, interfaces):
        ICollection = InterfaceCollection(name)
        for interface in interfaces:
            ICollection.add(interface)
        return ICollection

    @classmethod
    def from_collections(cls, name, collections):
        ICollection = InterfaceCollection(name)
        for collection in collections:
            ICollection.update(collection)
        return ICollection
    
    @classmethod
    def from_entities(cls, name, entity_names):
        ICollection = InterfaceCollection(name)

        # Consider fetching all entities in one go if possible
        entities = [Entity.load(entity_name) for entity_name in entity_names]

        for entity in entities:
            if entity:     
                #Add items from interfaceCollection_data to ICollection.
                interfaceCollectionData = entity.interfaceCollection_data 
                ICollection.add_data(interfaceCollectionData)                                 
        return ICollection


    @classmethod
    def from_card(cls, card):      
        if type(card) is dict:
            card = Card.from_data(card)
        return cls.from_entities(card.title, card.entity_names)

    @classmethod
    def from_deck(cls, deck):       
        if type(deck) is dict:
            deck = Deck.from_dict(deck['forgeborn'], deck['faction'], deck['cards'])
        entities = [ entity for card in deck.cards.values() for entity in card.entities ]
        return cls.from_entities(deck.name, entities)

    @classmethod
    def from_forgeborn(cls, forgeborn):    
        return cls.from_entities(forgeborn.name, forgeborn.abilities.values())


    def add_data(self, data):
        # Assuming data is a dictionary where keys are interface names and values are Interface instances
        self.interfaces.update(data)

    def _update_cache(self, interface_types, synergy=None):
        """
        Update the cache with interfaces of given types and synergy.
        """
        cache_key = self._get_cache_key(interface_types, synergy)
        
        interfaces_to_cache = {}
        
        if synergy is None:
            for syn, interface_dict in self.interfaces.items():
                matched_interfaces = [interface for interface in interface_dict.values() if any(type_ in interface.types for type_ in interface_types)]
                if matched_interfaces:
                    interfaces_to_cache[syn] = matched_interfaces
        else:
            if synergy in self.interfaces:
                matched_interfaces = [interface for interface in self.interfaces[synergy].values() if any(type_ in interface.types for type_ in interface_types)]
                if matched_interfaces:
                    interfaces_to_cache[synergy] = matched_interfaces
    
        if interfaces_to_cache:
            self._cache[cache_key] = interfaces_to_cache


    def update(self, other):
        
        for interface_dict in other.collection_data:
            for interface in interface_dict.values():
                self.add(interface)      
        self._cache.clear()
        return self


    def add(self, interface):
        for synergy_name in interface.synergyNames:
            if interface.tag in self.interfaces[synergy_name]:
                existing_interface = self.interfaces[synergy_name][interface.tag]
                #existing_interface.types.update(interface.types)  # Add interface.types as a single item to the set
            else:
                self.interfaces[synergy_name][interface.tag] = interface
        self._cache.clear() # Clear the cache whenever the collection is updated.

    def copy(self):
        """
        Return a new instance of InterfaceCollection that is a shallow copy of the current instance.
        """
        new_collection = InterfaceCollection(self.name)        
        new_collection.interfaces = {k: v for k, v in self.interfaces.items()}
        new_collection._cache = self._cache
        return new_collection

    def restrict_range(self, range):
        ICollection = InterfaceCollection(self.name)

        ICollection.interfaces = {
            synergy: {
                name: interface 
                for name, interface in interfaces.items() 
                if range not in interface.ranges
            } 
            for synergy, interfaces in self.interfaces.items()
        }

        # Filter out empty interface dictionaries
        ICollection.interfaces = {
            synergy: interfaces 
            for synergy, interfaces in ICollection.interfaces.items() 
            if interfaces
        }

        return ICollection

    def get_max_ranges(self):
        return [synergy for synergy, interfaces in self.interfaces.items() 
                for _, interface in interfaces.items() 
                if any(range_char in r for r in interface.ranges for range_char in ['*', '+'])]

    def get_interfaces_by_type(self, interface_types, synergy=None):
        cache_key = self._get_cache_key(interface_types, synergy)
        
        # Check the cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # If not in cache, update the cache
        self._update_cache(interface_types, synergy)
        
        # Return the cached value
        return self._cache.get(cache_key, {})
    
    def get_synergies(self):
        return [synergy for synergy in self.interfaces if self.interfaces[synergy]]

    def _get_cache_key(self, interface_types, synergy=None):
        """
        Generate a unique cache key using interface_types and synergy.
        """
        interface_types = frozenset(interface_types)  # Convert set to frozenset for hashability
        return (interface_types, synergy)


    def get_members(self, type=None):        
        members = [f"{synergy} :: {interface_tag.name} - {interface_tag}" for synergy, interfaces in self.interfaces.items() for interface_tag in interfaces if type in interfaces[interface_tag].types]

        return members


    def __str__(self):        
        synergies_str = "Synergies:\n"
        for synergy in self.interfaces.values():                        
            synergies_str += f"{str(synergy)}\n"
        return synergies_str 

    @staticmethod
    def match_synergies(collection1, collection2):        
        """
        Matches synergies between two collections.

        Args:
        collection1: The first collection object.
        collection2: The second collection object.

        Returns:
        A dictionary of matched synergies and their associated factor.
        """
        # Restrict range if collections are the same
        if collection1.name == collection2.name:
            collection1 = collection2 = collection1.restrict_range('+')
            
        synergies = collection2.get_synergies()

        matched_synergies = {}
        unmatched_input_interfaces = {}

        for synergy in synergies:

            input_interfaces_by_syn = collection2.get_interfaces_by_type("I", synergy)
            output_interfaces_by_syn = collection1.get_interfaces_by_type("O", synergy)

            if not input_interfaces_by_syn: 
                continue

            if output_interfaces_by_syn:
                matched_synergies[synergy] = {
                    'input' : input_interfaces_by_syn[synergy], 
                    'output': output_interfaces_by_syn[synergy]
                }
            else:
                unmatched_input_interfaces[synergy] = input_interfaces_by_syn[synergy]

        return matched_synergies , unmatched_input_interfaces

    def to_data(self):
        """
        Convert the InterfaceCollection to a dictionary that is JSON serializable.
        """
        interfaces_dict = {}
        for synergy, interface_dict in self.interfaces.items():
            for name, interface in interface_dict.items():
                #idict = interface.to_data()
                interfaces_dict[synergy] = name #{name: idict}
        return {
            "name": self.name,
            "interfaces": interfaces_dict,            
        }
    @classmethod
    def from_data(cls, data):
        """
        Create an InterfaceCollection from a dictionary.
        """
        name = data['name']
        interfaces = data['interfaces']
        ICollection = cls(name)
        for synergy, interface_dict in interfaces.items():
            for name, interface in interface_dict.items():
                ICollection.add(interface)
        return ICollection

@dataclass
class InterfaceData:
    tag:  str       = ''
    value: any      = 0
    ranges: str     = ''
    children_data: dict = field(default_factory=dict)
    #synergyNames: list = field(default_factory=list)    

from MongoDB.DatabaseManager import DatabaseObject
class Interface(DatabaseObject):
    def __init__(self, data: InterfaceData):
        # Initialize the base class first if it does important setup
        super().__init__(data)
        
        # Then do the specific initialization for Interface
        if data : self._initialize_types_and_synergies()            

    def _initialize_types_and_synergies(self):
        synergy_template = SynergyTemplate()        
        if self.data:
            self._id = self.tag
            self.data.children_data = { synergy.name: 'Synergy.Synergy' for synergy in synergy_template.get_synergies_by_tag(self.tag) }
                    
    def get_synergies_by_type(self, type):
        return [synergyName for synergyName in self.children_data.keys() if self.has_tag_of_type(synergyName, type)]

    def has_tag_of_type(self, synergy, type):
        if type == "I":
            return any(tag in synergy.get_target_tags() for tag in SynergyTemplate().get_input_tags())
        elif type == "O":
            return any(tag in synergy.get_source_tags() for tag in SynergyTemplate().get_output_tags())        
        else:
            return False
    
    def __str__(self):
        string = f"{self.name} {self.tag} {self.value} {[synergyName for synergyName in self.synergyNames]}"
        return string