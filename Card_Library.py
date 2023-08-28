# Fixed Version
import csv, json
from Interface import Interface, InterfaceCollection
from typing import List, Tuple, Dict
from copy import copy

class Entity:
    def __init__(self, name, faction, rarity, card_type, card_subtype, spliced, solbind, abilities, Collection):
        self.name = name
        self.faction = faction
        self.rarity = rarity
        self.card_type = card_type
        self.card_subtype = card_subtype
        self.spliced = spliced
        self.solbind = solbind        
        self.abilities = abilities        
        self.provides = {sub_type: 1 for subtype in card_subtype.split(',') for sub_type in subtype.split(' ')}
        self.provides.update({card_type : 1})
        self.ICollection = Collection
  
    def __str__(self):
        #trait_str = ", ".join([f"{trait}" for trait in self.sources.items()])
        #synergy_str = ", ".join([str(synergy) for synergy in self.targets.values()])
        return f"{self.name}"

class Forgeborn:
    def __init__(self, id, name, abilities):
        self.id = id 
        self.name = name
        self.abilities = abilities        
        self.ICollection = InterfaceCollection.from_forgeborn(self)

    def __str__(self):
        abilities_str = "\n".join([f"  {ability}: {text}" for ability, text in self.abilities.items()])
        return f"Forgeborn Name: {self.name}\nAbilities:\n{abilities_str}\n"


class Card():
    def __init__(self, card, modifier=None): 
        self.entities = [card]             
        self.faction  = card.faction
        if modifier:
            self.title = modifier.name + ' ' + card.name
            if isinstance(modifier, Entity):
                self.entities.append(modifier)        
        else:
            self.title = card.name        
        self.card_type = card.card_type
        self.card_subtype = card.card_subtype
        self.name = self.title
        self.ICollection = InterfaceCollection.from_card(self)        

    def get_rarities(self):
        return [item.rarity for item in self.entities]

    def __str__(self):
        return self.title

    def to_json(self):
        return {
            "name": self.name,            
        }

class Deck:
    
    def __init__(self, name: str, forgeborn, faction: str, cards: Dict[str, Card]):
        assert isinstance(name, str) and name, "Name must be a non-empty string"
        assert isinstance(faction, str) and faction, "Faction must be a non-empty string"
        assert isinstance(cards, dict), "Cards must be a dictionary"

        self.name = name        
        self.forgeborn = forgeborn
        self.faction = faction
        self.abilities = forgeborn.abilities 

        if not isinstance(self, Fusion):
            self.cards = self.associate_cards_with_factions(cards, faction)
        else:
            self.cards = cards
        
        self.composition = self.get_composition()        
        self.ICollectionDeck = InterfaceCollection.from_deck(self)                   
        self.ICollection = self.ICollectionDeck
        self.update_ICollection_with_forgeborn()
        
    @classmethod
    def empty(cls):
        return cls("", None, "", {})

    def get_composition(self):        
        composition = {}        
        for card in self.cards.values():                        
            for subtype in card.card_subtype.split(' '):                
                subtype = subtype.strip()
                composition[subtype] = composition.get(subtype, 0) + 1
            for cardtype in card.card_type.split(' '):
                composition[cardtype] = composition.get(cardtype, 0) + 1
        return composition
    
    def update_ICollection_with_forgeborn(self):
        """
        Update the ICollection of the Deck object by combining 
        the ICollectionDeck of the Deck object and the ICollection
        of the active Forgeborn.
        """
        self.ICollection = self.ICollectionDeck.copy()
        self.ICollection.update(self.forgeborn.ICollection)

    def associate_cards_with_factions(self, cards: Dict[str, Card], faction: str) -> Dict[str, Card]:
        """
        Associates each card in the input list with the corresponding deck's faction.
        Parameters:
        - cards (Dict[str, Card]): A dictionary of cards, where the key is the card name and the value is a Card object.
        - faction (str): The faction associated with these cards.
        
        Returns:
        - Dict[str, Card]: A dictionary where the keys are tuples (faction, card_name) and the values are Card objects.
        """
        faction_cards = {}
        for card_name, card in cards.items():
            faction_cards[(faction, card_name)] = card
        return faction_cards


class Fusion(Deck):
    def __init__(self, decks, name=None):
        if len(decks) == 1:
            super().__init__(decks[0].name, decks[0].forgeborn, decks[0].faction, decks[0].cards)
            self.forgeborn_options = [decks[0].forgeborn]
            self.decks = decks
            return
        
        deck1, deck2 = decks[0], decks[1]

        if deck1.faction == deck2.faction:
            raise ValueError("Cannot fuse decks of the same faction")

        
        # Default Values 
        fusion_name = "_".join([deck.name for deck in decks])        
        # Name and faction for the fusion

        # Sort the deck names alphabetically and then join them with an underscore
        self.fused_name = name or "_".join(sorted([deck.name for deck in decks]))
        # Generate the fused faction name        
        self.fused_faction = "|".join([deck.faction for deck in decks]) 
        fused_cards = {**deck1.cards, **deck2.cards}
        
        # Additional properties specific to Fusion
        self.deck1 = deck1
        self.deck2 = deck2
        self.forgeborn_options = self.inspire_forgeborn(deck1.forgeborn, deck2.forgeborn)
        self.fused_abilities = [ability for forgeborn in self.forgeborn_options for ability in forgeborn.abilities]
        

        # Choosing a default forgeborn (frosm deck1 for simplicity)
        # Note: Here we're assuming that a 'forgeborn' variable exists in the 'Deck' class
        self.active_forgeborn = self.forgeborn_options[0]

        # Call the Deck's constructor and exchange fused abilities 
        super().__init__(name or fusion_name, self.active_forgeborn, self.fused_faction, fused_cards)        
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
            self.update_ICollection_with_forgeborn()
 

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



class UniversalCardLibrary:

    entities = []

    def __init__(self, sff_path, fb_path):        
        self.entities  = self._read_entities_from_csv(sff_path)
        self.forgeborn = self._read_forgeborn_from_csv(fb_path)


    def _read_forgeborn_from_csv(self, csv_path):
        forgeborn = {}
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                id   = row['id']
                id   = id.replace('0', '2')
                title =  row['Forgeborn']                                  
                abilities = {}
                for level in range(3):                    
                    level += 2
                    name = row[f"{level}name"] if row.get(f"{level}name") else ""
                    text = row[f"{level}text"] if row.get(f"{level}text") else ""                 
                    name = f"{level}{name}"   
                    abilities[name] = self.search_entity(name,'Ability')
                #print(f"Forgeborn:  [{id}] {title} {','.join(ability.name for ability in abilities.values())}")
                forgeborn[id] = Forgeborn(id, title, abilities)
        return forgeborn
        

    def _read_entities_from_csv(self, csv_path):   
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:                
                name = row['Name']
                faction = row['faction']
                rarity = row['rarity']
                card_type = row['cardType']
                card_subtype = row['cardSubType']
                spliced = bool(row['spliced'])
                solbind = bool(row['solbind'])
                abilities = {}
                
                for ability in row.keys():
                    if ability.endswith('text') and row[ability]:
                        level = int(ability[0])
                        attack = int(row[f"{level}attack"]) if row.get(f"{level}attack") else 0
                        health = int(row[f"{level}health"]) if row.get(f"{level}health") else 0
                        abilities[level] = {
                            'text': row[ability],
                            'attack': attack,
                            'health': health
                        }
                                                 
                Collection = InterfaceCollection(name)
                
                read_synergies = False
                for key, value in row.items():
                    if key == "3text":
                        read_synergies = True   
                    elif read_synergies:
                        range   = None                # Default: Any                           
                        if value is not None:                             
                            if not value.isnumeric():
                                if key == "Free":                                    
                                    key = f"Free {value}"            
                                    value = 1
                                    
                                else: 
                                    range = value
                                    if   value == '*':  value = 1                                        
                                    elif value == '+':  value = 1
                                    elif value == '.':  value = 0
                                    else:
                                        range = ''
                                        value = 0

                                    
                            if int(value) > 0:                                                                    
                                
                                    ISyn = Interface(name, key=key, value=value, range=range)                                    
                                    Collection.add(ISyn)
                                                                    
                self.entities.append(Entity(name, faction, rarity, card_type, card_subtype, spliced, solbind, abilities, Collection))
        return self.entities

    def search_entity(self,name, card_type=None):
        #print(f"Searching Entity: {name}")
        for entity in self.entities:
            if card_type is None or entity.card_type == card_type:
                if entity.name == name:
                    return entity
        #print(f"Entity not found: {name} , {card_type}")
        return None

    def get_forgeborn(self, id):
        if id in self.forgeborn:
            return self.forgeborn[id]
        print(f"Forgeborn {id} could not be found")
        return None

    def load_decks_from_file(self, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)            
        return self.load_decks_from_data(data)

    def load_data(self, filename):
        with open(filename, 'r') as f:
            content = f.read()
            data = json.loads(content)

        if 'Items' in data:
            return data['Items']
        else:                                
            return [data]

    def load_decks_from_data(self, decks_data: List[Dict]) -> Tuple[List[Deck], List[Dict]]:

        decks = []
        incomplete_data = []
        
        for deck_data in decks_data:            
            try:
                forgebornId = deck_data['forgebornId'][1:]
                forgebornId = forgebornId.replace('0','2')
                forgebornKey = [key for key in self.forgeborn if forgebornId in key]
                forgeborn = self.forgeborn[forgebornKey[0]]
            

            except Exception as e:
                print(f"Exception: {e}")
                print(f"Could not load Forgeborn data: {deck_data['name'] if 'name' in deck_data else 'unknown'}")
                
                incomplete_data.append(deck_data)
                continue

            try: 
                cards_data = deck_data['cards']

                cards_title = []
                cards_additional_data = {}

                # Handle the case when cards_data is a dictionary
                if isinstance(cards_data, dict):
                    for card in cards_data.values():
                        card_title = str(card.get('title')) if 'title' in card else str(card.get('name'))
                        cards_title.append(card_title)

                else:
                    cards_title = cards_data

                # Create the cards dictionary with additional data
                cards = {card_title: self.create_card_from_title(card_title, cards_additional_data.get(card_title, {})) for card_title in cards_title}

                
            except Exception as e:
                print(f"Could not load Cards data: {deck_data['name'] if 'name' in deck_data else 'unknown'}")
                print(f"Exception: {e}")
                incomplete_data.append(deck_data)
                continue

            deck = Deck(deck_data['name'], forgeborn, deck_data['faction'], cards)
            decks.append(deck)
            
        return decks, incomplete_data

        
    def load_fusions(self, fusions_data: List[Dict]) -> Tuple[List[Fusion], List[Dict]]:
        fusions = []
        incomplete_fusionsdata = []

        for fusion_data in fusions_data:            
                decks, incomplete_decksdata = self.load_decks_from_data(fusion_data['myDecks'])
                name = fusion_data['name'] if 'name' in fusion_data else ""
                if decks:
                    fusion = Fusion(decks, name)
                    fusions.append(fusion)
                if incomplete_decksdata:
                   incomplete_fusionsdata.append(
                        {
                            'name': name, 
                            'myDecks': incomplete_decksdata
                        }
                    )
                
        return fusions, incomplete_fusionsdata

    def create_card_from_title(self, card_title, card_data_additional):
        # First try with full title
        card_entity = self.search_entity(card_title)        
        if card_entity:
            for key, value in card_data_additional.items():                
                setattr(card_entity, key, value)
            return Card(card_entity)

        # If not found, try with decreasing title length
        parts = card_title.split(' ')
        for i in range(1, len(parts)):
            modifier_title = ' '.join(parts[:i])
            card_title = ' '.join(parts[i:])
            modifier_entity = self.search_entity(modifier_title, 'Modifier')
            card_entity = self.search_entity(card_title)
            if modifier_entity and card_entity:
                for key, value in card_data_additional.items():
                    existing_value = getattr(card_entity, key)  # Get existing value or use an empty dictionary
                    if isinstance(existing_value, dict):
                        merged_value = {**existing_value, **value}  # Merge the dictionaries
                        setattr(card_entity, key, merged_value)
                    elif value:
                        setattr(card_entity, key, value)  # Set the new value directly

                return Card(card_entity, modifier_entity)

        # If no entities found, create a card with just the card title
        return Card(Entity(name=card_title, card_type='Unknown'))
                
    def __str__(self):
        entity_strings = []
        for entity in self.entities:
            entity_strings.append(str(entity))
        return "\n".join(entity_strings)    
  
