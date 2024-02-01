from MongoDB.DatabaseManager import DatabaseObject
from copy import copy
from dataclasses import dataclass, field

@dataclass
class EntityData:
    name: str    
    faction: str
    attributes: dict
    abilities: dict
    interfaceCollection_data: dict

class Entity(DatabaseObject):
    def __init__(self, data: EntityData):
        super().__init__(data)
        
    def get_collection_names(self):
        return self.interfaceCollection_data
        
    
@dataclass
class ForgebornData:
    id: str = ''
    name: str   = ''
    entity_names: list = field(default_factory=list)

class Forgeborn(DatabaseObject):
    def __init__(self, data: ForgebornData):
        super().__init__(data)
            
    def __str__(self):
        abilities_str = "\n".join([f"  {ability}: {text}" for ability, text in self.entity_names.items()])
        return f"Forgeborn Name: {self.name}\nAbilities:\n{abilities_str}\n"
    
    def get_collection_names(self):
        return self.entity_names

@dataclass
class CardData():
    name    : str  = ''
    faction : str   = ''
    cardType: str   = ''
    cardSubType: str    =''
    attack  : dict  =field(default_factory=dict)
    health  : dict  =field(default_factory=dict)
    entity_names : list = field(default_factory=list)

class Card(DatabaseObject):

    def __init__(self, data: CardData):         
        super().__init__(data)
        
        if self.data is not None:
            self.data.entity_names = self.get_entity_names_from_title(self.name)   
        
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


    def get_entity_names_from_title(self, card_title):
        # First try with full title        
        card_entity_data = self.db_manager.get_record_by_name('Entity', card_title)        
        if card_entity_data:          
            return card_entity_data['name']

        # If not found, try with decreasing title length
        parts = card_title.split(' ')
        for i in range(1, len(parts)):
            modifier_title = ' '.join(parts[:i])
            card_title = ' '.join(parts[i:])
            modifier_entity_data = self.db_manager.get_record_by_name('Entity', modifier_title)
            card_entity_data = self.db_manager.get_record_by_name('Entity', card_title)
            if modifier_entity_data and card_entity_data:
                return [entity_name for entity_name in [modifier_entity_data['name'], card_entity_data['name']]]
    
        # If no entities found, create a card with just the card title
        return [card_title]

    def get_collection_names(self):
        return self.entity_names

@dataclass
class DeckData:
    name        : str
    forgebornId : str
    faction     : str    
    cardIds     : list
    cards       : dict              # Card ids from Net API

class Deck(DatabaseObject):
    
    def __init__(self, data: DeckData):
        super().__init__(data)
        
    # def __init__(self, name: str='', forgebornId : str='0', faction: str='', cardIds: list=[], cards: dict={}):        

    #     self.data = DeckData(
    #         name = name,
    #         forgebornId = forgebornId,
    #         faction = faction,
    #         cardIds = cardIds,
    #         cards = cards
    #     )      
    def get_collection_names(self):
        return self.cards

class Fusion(Deck):
    def __init__(self, decks, name=None):
        if len(decks) == 1:            
            super().__init__(DeckData(decks[0].name, decks[0].forgebornId, decks[0].faction, decks[0].cardIds, decks[0].cards))
            self.forgeborn_options = [decks[0].forgeborn]
            self.decks = decks
            return
        
        deck1, deck2 = decks[0], decks[1]
        

        if deck1.faction == deck2.faction:
            #raise ValueError("Cannot fuse decks of the same faction")
            return None

        # Default Values 
        fusion_name = "_".join([deck.name for deck in decks])        
        # Name and faction for the fusion

        # Sort the deck names alphabetically and then join them with an underscore
        self.fused_name = name or "_".join(sorted([deck.name for deck in decks]))
        # Generate the fused faction name        
        self.fused_faction = "|".join([deck.faction for deck in decks]) 
        fused_cards = {**deck1.cards, **deck2.cards}
        fused_card_ids = deck1.cardIds + deck2.cardIds
        
        # Additional properties specific to Fusion
        self.deck1 = deck1
        self.deck2 = deck2
        self.forgeborn_options = self.inspire_forgeborn(deck1.forgeborn, deck2.forgeborn)
        self.fused_abilities = [ability for forgeborn in self.forgeborn_options for ability in forgeborn.abilities]
        

        # Choosing a default forgeborn (frosm deck1 for simplicity)
        # Note: Here we're assuming that a 'forgeborn' variable exists in the 'Deck' class
        self.active_forgeborn = self.forgeborn_options[0]

        # Call the Deck's constructor and exchange fused abilities 
        super().__init__(DeckData(name or fusion_name, self.active_forgeborn, self.fused_faction,fused_card_ids, fused_cards))
        self.abilities = self.fused_abilities
        
    def inspire_forgeborn(self, forgeborn1, forgeborn2):
        new_forgeborns = []
        
        for original_forgeborn, other_forgeborn in [(forgeborn1, forgeborn2), (forgeborn2, forgeborn1)]:
            
            inspire_abilities = [ability for ability in original_forgeborn.abilities if 'Inspire' in ability]
            
            if inspire_abilities:
                new_abilities = original_forgeborn.abilities.copy()
                
                for inspire_ability in inspire_abilities:
                    level = inspire_ability[0]
                    
                    for other_ability_name, other_ability in other_forgeborn.abilities.items():
                        if other_ability_name[0].startswith(str(level)):
                            new_abilities[other_ability_name] = other_ability
                            break  # Assuming you only want the first match
                    
                new_forgeborn = Forgeborn(original_forgeborn.id, original_forgeborn.name, new_abilities)
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
