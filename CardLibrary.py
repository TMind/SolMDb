from itertools import count

from numpy import cross
from MongoDB.DatabaseManager import DatabaseObject
from copy import copy
from dataclasses import dataclass, field

import GlobalVariables

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
        card_entity_data =  GlobalVariables.commonDB.get_record_by_name('Entity', card_name)        
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
            modifier_entity_data = GlobalVariables.commonDB.get_record_by_name('Entity', modifier_title)
            card_entity_data = GlobalVariables.commonDB.get_record_by_name('Entity', card_name)

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
    xp: int = 0
    digital: str = ''
    elo: int = 0
    children_data: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)
    graph: dict = field(default_factory=dict)

class Deck(DatabaseObject):
    
    def __init__(self, data: DeckData):        
        super().__init__(data)         
        self._id = self.name  
        if self.data and self.cardIds: 
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
    currentForgebornId: str = ''
    ForgebornIds: list = field(default_factory=list)
    id: str = ''
    deckRank: str = ''
    CreatedAt: str = ''        
    tags: list = field(default_factory=list)
    children_data: dict = field(default_factory=dict)
    graph: dict = field(default_factory=dict)

class Fusion(DatabaseObject):
    def __init__(self, data=None):

        super().__init__(data) 
        self._id = self.name
        if self.data:
            if self.data.myDecks:
                #Check if myDecks contains only strings or objects 
                if isinstance(self.data.myDecks[0], str):
                    self.data.children_data = {deckName : 'CardLibrary.Deck' for deckName in self.data.myDecks}
                else:
                    self.data.children_data = {deck_data['name']: 'CardLibrary.Deck' for deck_data in self.data.myDecks}
                
                if not self.data.currentForgebornId:                                    
                    self.data.currentForgebornId = self.data.myDecks[0]['forgeborn']['id']
                self.data.children_data.update({self.currentForgebornId: 'CardLibrary.Forgeborn'})
        
        # Default Values 
        #fusion_name = "_".join([deck.name for deck in decks])        
        # Name and faction for the fusion

        # Sort the deck names alph1_".join(sorted([deck.name for deck in decks]))
        # Generate the fused faction name        
        #self.fused_faction = "|".join([deck.faction for deck in decks]) 
        #fused_cards = {**deck1.cards, **deck2.cards}
        #fused_card_ids = deck1.cardIds + deck2.cardIds
        
        # Additional properties specific to Fusion
        #self.deck1 = deck1
        #self.deck2 = deck2
        #self.forgeborn_options = self.inspire_forgeborn(deck1.forgeborn, deck2.forgeborn)
        #self.fused_abilities = [ability for forgeborn in self.forgeborn_options for ability in forgeborn.abilities]
        

        # Choosing a default forgeborn (frosm deck1 for simplicity)
        # Note: Here we're assuming that a 'forgeborn' variable exists in the 'Deck' class
        #self.active_forgeborn = self.forgeborn_options[0]

        # Call the Deck's constructor and exchange fused abilities 
        #super().__init__(DeckData(name or fusion_name, self.active_forgeborn, self.fused_faction,fused_card_ids, fused_cards))
        #self.abilities = self.fused_abilities
        
    def inspire_forgeborn(self, forgeborn1, forgeborn2):
        new_forgeborns = []
        
        for original_forgeborn, other_forgeborn in [(forgeborn1, forgeborn2), (forgeborn2, forgeborn1)]:
            
            inspire_abilities = [ability for ability in original_forgeborn.abilities.values() if 'Inspire' in ability.attributes['Name']]
            
            if inspire_abilities:
                new_abilities = original_forgeborn.abilities.copy()
                
                for inspire_ability in inspire_abilities:
                    level = inspire_ability.name[-3]
                    
                    for other_ability_name, other_ability in other_forgeborn.abilities.items():
                        if other_ability_name[-3].startswith(str(level)):
                            # Remove the old ability that has the same level 
                            ability_id_replace_name = next((ability_id for ability_id in new_abilities.keys() if ability_id[-3] == level), None)
                            if ability_id_replace_name:
                                new_abilities.pop(ability_id_replace_name)
                            new_abilities[other_ability.name] = other_ability
                            break  # Assuming you only want the first match
                new_forgeborn = Forgeborn(original_forgeborn.id, original_forgeborn.name)
                for name, ability in new_abilities.items():
                    id = name 
                    name = ability.attributes['Name']
                    new_forgeborn.add_ability(ForgebornAbility(id, name ,ability))                
            else:
                new_forgeborn = original_forgeborn
            
            new_forgeborns.append(new_forgeborn)    
        return new_forgeborns

    def set_forgeborn(self, idx_or_forgeborn_name):
            """
            Sets the active Forgeborn of the Fusion deck to the given index or Forgeborn object.
            Also updates the Fusion's name and faction based on the new active Forgeborn.
            """
            new_forgeborn = self.active_forgeborn
            if isinstance(idx_or_forgeborn_name, int):
                new_forgeborn = self.forgeborn_options[idx_or_forgeborn_name]
            else:
                new_forgeborn = self.get_forgeborn(idx_or_forgeborn_name)

            self.abilities = new_forgeborn.abilities
            # Check if the new Forgeborn is already the active one
            if self.active_forgeborn == new_forgeborn: return

            # Update the active Forgeborn
            self.active_forgeborn = new_forgeborn

            # Update the name and faction based on the active Forgeborn
            if self.active_forgeborn == self.forgeborn_options[0]:
                self.name    = f"{self.deck1.name}_{self.deck2.name}"
                self.faction = f"{self.deck1.faction}|{self.deck2.faction}"
            else:
                self.name    = f"{self.deck2.name}_{self.deck1.name}"
                self.faction = f"{self.deck2.faction}|{self.deck1.faction}"
            
            # Update the forgeborn in the parent (Deck) class
            self.forgeborn = self.active_forgeborn    
#            self.update_ICollection_with_forgeborn()
 

    def copyset_forgeborn(self, idx_or_forgeborn_name):

        final_fusion = copy(self)
        final_fusion.set_forgeborn(idx_or_forgeborn_name)

        return final_fusion

    def get_forgeborn(self, id_or_forgeborn_name):        
        if isinstance(id_or_forgeborn_name, int):
            return self.forgeborn_options[id_or_forgeborn_name]
        else :
            for forgeborn in self.forgeborn_options:
                if id_or_forgeborn_name == forgeborn.name:
                    return forgeborn
        return None

    def to_dict(self):
        fusion_dict = super().to_dict()
        fusion_dict.update({
            "fused_name": self.fused_name,
            "fused_faction": self.fused_faction,
            #"deck1": self.deck1.to_dict(),
            #"deck2": self.deck2.to_dict(),
            "forgeborn_options": [fb.to_dict() for fb in self.forgeborn_options],
            "fused_abilities": self.fused_abilities
        })
        return fusion_dict    
