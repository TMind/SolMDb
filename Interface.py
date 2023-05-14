import math
import collections
from Synergy import SynergyTemplate

class InterfaceCollection:
    def __init__(self, interfaces=None, synergy_template=None):
        self.interfaces = {}
        self.synergy_template = synergy_template or SynergyTemplate()

        if self.synergy_template is not None:
            for syn in self.synergy_template.synergies:
                self.interfaces[syn] = {}       

        if interfaces is not None:
            for interface in interfaces:
                syns = interface.synergies
                for syn in syns:
                    self.interfaces[syn.name][interface.name] = interface

        #TODO: self.matchInterfaces()


    @classmethod
    def from_elements(cls, output, input, synergy_template=None):

        synergy_template = synergy_template or SynergyTemplate()
        Interfaces = {}

        for key, value in output.update(input):
            syns = synergy_template.get_synergies_by_tag(key)
            for syn in syns:
                Interfaces[syn.name].append(Interface(key,value))
        return cls(Interfaces,synergy_template)
     
    @classmethod
    def from_entities(cls, entities, synergy_template=None):        
        ICollection = InterfaceCollection()

        for entity in entities:   
            ICollection.update(entity.ICollection)            

        return ICollection

    @classmethod
    def from_card(cls, card, synergy_template=None):        
        return cls.from_entities(card.entities, synergy_template=synergy_template)

    @classmethod
    def from_deck(cls, deck, synergy_template=None):       
        entities = [ entity for card in deck.cards.values() for entity in card.entities ]
        return cls.from_entities(entities, synergy_template=synergy_template)

    @classmethod
    def from_forgeborn(cls, forgeborn, synergy_template=None):
        entities = [ability for ability in forgeborn.abilities.values()]
        return cls.from_entities(entities, synergy_template=synergy_template)


    def update(self, other):
        for interface_dict in other.interfaces.values():            
            for interface in interface_dict.values():
                self.add(interface)            
        return self


    def add(self, interface):
        for syn in interface.synergies:
            self.interfaces[syn.name][interface.name] = interface

    def get_interfaces_by_type(self, interface_type, synergy=None):
        result = {}
        if synergy is None:
            for synergy, interface_dict in self.interfaces.items():
                interfaces = [interface for interface in interface_dict.values() if interface.is_type(interface_type)]
                if interfaces: result[synergy] = interfaces
        else:
            if synergy in self.interfaces:
                interfaces = [interface for interface in self.interfaces[synergy].values() if interface.is_type(interface_type)]
                if interfaces: result[synergy] = interfaces
                
        return result  

    def __str__(self):
        output_str = f"output: {self.output}\n" if isinstance(self.output, dict) else ""
        input_str = f"input: {self.input}\n" if isinstance(self.input, dict) else ""
        synergies_str = "Synergies:\n"
        for synergy in self.synergies.values():                        
            synergies_str += f"{str(synergy)}\n"
        return synergies_str # + output_str + input_str

    @staticmethod
    def match_synergies(collection1, collection2):
        matched_synergies = {}
        
        input_interfaces1 = collection1.get_interfaces_by_type("IN")
        output_interfaces2 = collection2.get_interfaces_by_type("OUT")

        for synergy, input_interfaces in input_interfaces1.items():
            output_interfaces = output_interfaces2.get(synergy, [])
            num_connections = len(input_interfaces) * len(output_interfaces)
            matched_synergies[synergy] = num_connections

        return matched_synergies


class Interface:

    def __init__(self, element_name , tag=None, value=None):
        self.name = element_name
        self.tag = tag 
        self.value = value
        self.types = []
        self.range = ""
        self.synergies = []
        if tag:  
            self.synergies = SynergyTemplate().get_synergies_by_tag(tag)                        
            if tag in SynergyTemplate().get_output_tags():
                self.types.append("OUT")            
            if tag in SynergyTemplate().get_input_tags():
                self.types.append("IN")                

    def get_type(self):
        return self.types
    
    def is_type(self, type):
        return type in self.types

    def get_synergies_by_type(self, type):
        return [synergy for synergy in self.synergies if self.has_tag_of_type(synergy, type)]

    def has_tag_of_type(self, synergy, type):
        if type == "IN":
            return any(tag in synergy.get_target_tags() for tag in SynergyTemplate().get_input_tags())
        elif type == "OUT":
            return any(tag in synergy.get_source_tags() for tag in SynergyTemplate().get_output_tags())        
        else:
            return False

            
