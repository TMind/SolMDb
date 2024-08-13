from numpy import cross
from MongoDB.DatabaseManager import DatabaseManager, DatabaseObject
from copy import copy
from dataclasses import dataclass, field

from GlobalVariables import global_vars

@dataclass
class EntityData:
    name: str    = ''
    faction: str = ''
    attributes: dict = field(default_factory=dict)
    abilities: dict = field(default_factory=dict)
    range : str = "" 
    interfaceNames: list = field(default_factory=list)
    children_data: dict = field(default_factory=dict)
    
class Entity(DatabaseObject):
    def __init__(self, data: EntityData):        
        super().__init__(data)
        self._id = self.name
        if self.interfaceNames:
            self.data.children_data = {interfaceName: 'Interface.Interface' for interfaceName in self.interfaceNames}
    
@dataclass
class ForgebornData:    
    _id: str = ''
    id: str = ''
    name: str   = ''
    abilities: dict = field(default_factory=dict)    
    children_data: dict = field(default_factory=dict)
    

class ForgebornAbility :
    def __init__(self, id, name, entity):
        self.id = id
        self.name = name
        self.entity = entity     
        
class Forgeborn(DatabaseObject):
    def __init__(self, data: ForgebornData):        
        super().__init__(data)
        #self.data._id = self.id       
        if self.abilities:
            self.data.children_data = {entityName: 'CardLibrary.Entity' for entityName in self.abilities}  #TODO: Check if this is correct
            
    def add_ability(self, ability):
        #ability_permutation = ability.id[-4:]   # c3a2
        #ability_cycle = ability_permutation[1]
        #ability_number = ability_permutation[3]
        #ability_name = f"{ability_cycle}{ability.name}"

        if self.abilities:
            self.abilities[ability.id] = ability.entity                

    def get_permutation(self, forgeborn_id):
        # Extract ability information from forgeborn_id
        ability_ids = self._construct_ability_ids(forgeborn_id)
        
        # Create a new Forgeborn instance with a subset of abilities
        new_forgeborn = Forgeborn(self.data)
        new_forgeborn.data.id = forgeborn_id
        new_forgeborn.abilities = {aid: self.abilities[aid] for aid in ability_ids if aid in self.abilities}
        
        new_forgeborn.data.children_data = {entityName: 'CardLibrary.Entity' for entityName in new_forgeborn.abilities}
        
        return new_forgeborn

    def get_fraud_monster(self, fmid):
        ability_ids = self._construct_fraud_ability_ids(fmid)
        base_ability_id = ability_ids[0]
        modifier_ability_ids = ability_ids [1:]

        #base_ability = self.abilities[base_ability_id] if base_ability_id in self.abilities else None
        #modifier_abilities = { entity.name : entity for id, entity in self.abilities.items() if id in modifier_ability_ids }
        return base_ability_id, modifier_ability_ids
    
    def _construct_fraud_ability_ids(self, fmid):
        fraud_ability_ids = []

        # The first digit determines the legs
        first_digit = fmid[0]
        fraud_ability_ids.append(f"fraud-legs-{first_digit}")

        # The remaining digits determine the specific parts
        for position, digit in enumerate(fmid[1:], start=2):
            part_id = f"fraud-part-{digit}-p{position}"
            fraud_ability_ids.append(part_id)
        
        return fraud_ability_ids


    def _construct_ability_ids(self, forgeborn_id):
        # Parse the forgeborn_id to get ability IDs
        ability_prefix = self.id  # Assuming the prefix is the same as Forgeborn ID
        ability_ids = []
        ability_data = forgeborn_id[len(self.id):]  # Remove the Forgeborn ID part
        
        for i in range(0, len(ability_data)):
            number = ability_data[i]
            cycle = i+2
            ability_id = f"{ability_prefix}-c{cycle}a{number}"
            ability_ids.append(ability_id)
        
        return ability_ids
    
@dataclass
class CardData():
    name   : str   = ''
    title  : str   = ''
    faction : str   = ''    
    cardType: str   = ''
    cardSubType: str    =''    
    betrayer: bool = False
    sortValue: str = ''
    crossFaction: str = ''
    cardSetId: str = ''
    _id: str = ''
    rarity: str = ''
    provides: str = ''
    seeks: str = ''
    levels: dict = field(default_factory=dict)
    attack  : dict  =field(default_factory=dict)
    health  : dict  =field(default_factory=dict)   
    children_data: dict = field(default_factory=dict) 

class Card(DatabaseObject):

    def __init__(self, data: CardData):                 
        super().__init__(data)
                
        if self.data is not None:
            if data.name :  
                self.data.title = data.name 
                self.data.name = data.name 
            elif data.title:                
                self.data.name = data.title
                self.data.title = data.name 

            #print(f"Data Name: {self.data.name}")
            entityNames = self.get_entity_names_from_title(self.data.name)   
            if entityNames:
                #print(f"Entity Names: {entityNames}")
                self.data.children_data = {entityName: 'CardLibrary.Entity' for entityName in entityNames}
                    
        # self.above_stat = None
        # def aggregate_attribute(attribute_name):
        #     aggregated = {}
        #     for entity_name in self.entity_names:
        #         entity = self.lookup(entity_name, collection_name='Entity')
        #         for level in entity.abilities:
        #             aggregated[level] = aggregated.get(level,0) + entity.abilities[level][attribute_name]  
        #     return aggregated
        
                # self.above_stat ={'attack' : {}, 'health' : {}}

        # for stat in self.above_stat.keys():
        #     stats = getattr(self, stat)
        #     for level in stats: 
        #         self.above_stat[stat][level] = stats[level] >= 3 * ( level + 1 )


    def get_entity_names_from_title(self, card_name):        
        if not card_name or card_name == '': return None

        # First try with full title   
        commonDB = DatabaseManager('common')     
        card_entity_data =  commonDB.get_record_by_name('Entity', card_name)        
        if card_entity_data:          
            #print(f"Card Entity Data found : {card_entity_data['name']}")
            return [card_entity_data['name']]

        # If not found, try with decreasing title length
        parts = card_name.split(' ')
        entities_data = []
        for i in range(1, len(parts)):
            modifier_title = ' '.join(parts[:i])
            card_name = ' '.join(parts[i:])
            #print(f"Modifier Title: {modifier_title} - Card Name: {card_name}")
            modifier_entity_data = commonDB.get_record_by_name('Entity', modifier_title)
            card_entity_data = commonDB.get_record_by_name('Entity', card_name)

            if modifier_entity_data:
                #print(f"Modifier Entity Data found : {modifier_entity_data['name']}")
                entities_data.append(modifier_entity_data['name'])
            if card_entity_data:
                #print(f"Card Entity Data found : {card_entity_data['name']}")
                entities_data.append(card_entity_data['name'])
                
            return entities_data
        # If no entities found, return card_title
        return [card_name]

@dataclass
class DeckData:    
    name        : str
    forgebornId : str
    faction     : str    
    cardIds     : list  # Card ids from Net API
    cards       : dict           
    cardSetName: str   = ''
    cardSetId: str   = ''
    cardSetNo: str   = ''
    registeredDate: str = ''
    pExpiry: str = ''
    UpdatedAt: str = ''
    oldDisplayName: str = ''
    xp: int = 0
    digital: str = ''
    elo: int = 0
    deckRank: str = ''
    level: int = 0
    _id: str = ''
    children_data: dict = field(default_factory=dict)
    deckStats: dict = field(default_factory=dict)
    tags: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)
    graph: dict = field(default_factory=dict)
    node_data: dict = field(default_factory=dict)

class Deck(DatabaseObject):
    
    def __init__(self, data: DeckData):        
        super().__init__(data)         
        self._id = self.name  
        if self.data and self.cardIds: 
            self.data._id = self.name
            self.data.children_data = {cardId: 'CardLibrary.Card' for cardId in self.cardIds}
            self.calculate_stats()
            self.calculate_averages()


    def calculate_stats(self):
        #Calculate the amount of creature types and the number of spells
        stats = {'set': self.cardSetName, 'card_types' : {}, 'average_stats' : {}}
        card_types = {}
        for card_id, card in self.data.cards.items():            
            card_type = card['cardType']
            if card_type not in card_types:
                card_types[card_type] = {'count': 1}
            else:
                card_types[card_type]['count'] += 1
                        
            if 'cardSubType' in card:
                card_sub_types = card['cardSubType'].split(' ')
                for card_sub_type in card_sub_types:
                    card_sub_type = f"{card_sub_type} Type"
                    if card_sub_type not in card_types[card_type]:
                        card_types[card_type][card_sub_type] = 1
                    else:
                        card_types[card_type][card_sub_type] += 1    
                            
        if not self.data.stats :
            self.data.stats = {}
        
        self.data.stats['card_types'] = card_types

            
    def calculate_averages(self):
        if self.data.cards is None:
            return

        # Calculate the amount of creature types and their average stats per level
        stats = {'count' : 0, 'creature_types' : {}, 'average_stats' : {}}
        creature_count = 0        
        creature_average_stats = {'attack' : {'1' : 0.0 , '2' : 0.0, '3' : 0.0} , 'health' : {'1' : 0.0 , '2' : 0.0, '3' : 0.0}}
        for card_id, card in self.data.cards.items():
            if card['cardType'] == 'Creature':
                creature_count += 1                                
                for level in card['levels']:                    
                    creature_average_stats['attack'][str(level)] += card['levels'][level]['attack']
                    creature_average_stats['health'][str(level)] += card['levels'][level]['health']

        for type in creature_average_stats:
            for level in range(3):
                creature_average_stats[type][str(level+1)] = float(creature_average_stats[type][str(level+1)] / creature_count)
                        
        self.data.stats['creature_averages'] = creature_average_stats        


@dataclass
class FusionData:
    name: str = ''    
    myDecks: list = field(default_factory=list)    
    faction: str = ''
    crossFaction: str = ''
    currentForgebornId: str = ''
    ForgebornIds: list = field(default_factory=list)
    id: str = ''
    deckRank: str = ''
    CreatedAt: str = ''   
    UpdatedAt: str = ''     
    tags: list = field(default_factory=list)
    children_data: dict = field(default_factory=dict)
    graph: dict = field(default_factory=dict)
    node_data: dict = field(default_factory=dict)

class Fusion(DatabaseObject):
    def __init__(self, data=None):

        super().__init__(data) 
        self._id = self.name
        if self.data:
            if self.data.myDecks:
                #Check if myDecks contains only strings or objects 
                if isinstance(self.data.myDecks[0], str):
                    self.data.children_data = {deckName : 'CardLibrary.Deck' for deckName in self.data.myDecks}
                    if not self.data.currentForgebornId:
                        self.data.currentForgebornId = self.data.ForgebornIds[0]
                else:                    
                    if not self.data.currentForgebornId:                                    
                        self.data.currentForgebornId = self.data.myDecks[0]['forgeborn']['id']
                    self.data.children_data = {deck_data['name']: 'CardLibrary.Deck' for deck_data in self.data.myDecks}                
            
                self.data.children_data.update({self.currentForgebornId: 'CardLibrary.Forgeborn'})