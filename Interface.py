from Synergy import SynergyTemplate

class InterfaceCollection:
    def __init__(self, name, interfaces=None):
        self.name = name
        self.interfaces = {}
        self._cache = {}  # Initialize the cache dictionary
        
        synergy_template = SynergyTemplate()  # Instantiate only once here
        self.synergies = synergy_template.synergies

        if self.synergies:
            self.interfaces = {syn: {} for syn in self.synergies}
        
        if interfaces:
            for interface in interfaces:
                for syn in interface.synergies:
                    if interface.tag in self.interfaces[syn]:
                        myInterface = self.interfaces[syn][interface.tag]
                        myInterface.types.update(interface.types)
                        myInterface.ranges.update(interface.ranges)
                    else:
                        self.interfaces[syn][interface.tag] = interface
             
    @classmethod
    def from_entities(cls, name, entities):        
        ICollection = InterfaceCollection(name)        

        for entity in entities:
            if type(entity).__name__ == 'Entity':
                ICollection.update(entity.ICollection)            
            else:
                raise ValueError(f"Not an Entity: {entity}")

        return ICollection

    @classmethod
    def from_card(cls, card):        
        return cls.from_entities(card.title, card.entities)

    @classmethod
    def from_deck(cls, deck):       
        entities = [ entity for card in deck.cards.values() for entity in card.entities ]
        return cls.from_entities(deck.name, entities)

    @classmethod
    def from_forgeborn(cls, forgeborn):    
        return cls.from_entities(forgeborn.name, forgeborn.abilities.values())

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
        for interface_dict in other.interfaces.values():            
            for interface in interface_dict.values():
                self.add(interface)      
        self._cache.clear()
        return self


    def add(self, interface):
        for syn in interface.synergies:
            if interface.tag in self.interfaces[syn.name]:
                existing_interface = self.interfaces[syn.name][interface.tag]
                existing_interface.types.update(interface.types)  # Add interface.types as a single item to the set
            else:
                self.interfaces[syn.name][interface.tag] = interface
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
        matched_synergies = {}
        
        #print(f"Match Collections: {collection1.name} <=> {collection2.name}")
        if collection1.name == collection2.name:
            restricted_collection = collection1.restrict_range('+')
            collection1 = restricted_collection
            #collection2 = restricted_collection
            
        input_interfaces2 = collection2.get_interfaces_by_type("I")
        output_interfaces1 = collection1.get_interfaces_by_type("O")
        
        for synergy, input_interfaces in input_interfaces2.items():            
            output_interfaces = output_interfaces1.get(synergy, [])
            
            if len(output_interfaces) > 0:

                factor = len(input_interfaces) * len(output_interfaces)
                input_ranges = set()
                for interface in input_interfaces:
                    input_ranges.update(interface.ranges) 
                if '*' in input_ranges:
                    factor *= 1
                if '+' in input_ranges:
                    factor *= 1                                            
                matched_synergies[synergy] = factor

        return matched_synergies


class Interface:
    def __init__(self, element_name, key=None, value=None, range=None):
        self.name = element_name
        self.tag = key
        self.value = value
        self.types = set()
        self.ranges = set(range) if range else set()
        self.synergies = []

        synergy_template = SynergyTemplate()  # Instantiate only once here
        if key:
            self.synergies = synergy_template.get_synergies_by_tag(key)
            if key in synergy_template.get_output_tags():
                self.types.add("O")
            if key in synergy_template.get_input_tags():
                self.types.add("I")            

    def get_type(self):
        return self.types
    
    def is_type(self, type):
        return type in self.types

    def get_synergies_by_type(self, type):
        return [synergy for synergy in self.synergies if self.has_tag_of_type(synergy, type)]

    def has_tag_of_type(self, synergy, type):
        if type == "I":
            return any(tag in synergy.get_target_tags() for tag in self.synergy_template.get_input_tags())
        elif type == "O":
            return any(tag in synergy.get_source_tags() for tag in self.synergy_template.get_output_tags())        
        else:
            return False