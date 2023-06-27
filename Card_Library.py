# Fixed Version
import csv, json
from re import A
from Interface import Interface, InterfaceCollection
from typing import List, Tuple, Dict
from collections import Counter

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
        self.seeks = {}
        self.ICollection = Collection
  
    def __str__(self):
        #trait_str = ", ".join([f"{trait}" for trait in self.sources.items()])
        #synergy_str = ", ".join([str(synergy) for synergy in self.targets.values()])
        return f"{self.name}"

class Deck:
    def __init__(self, name, forgeborn, faction, cards):
        self.name = name        
        self.forgeborn = forgeborn
        self.faction = faction
        self.cards = cards
        self.composition = self.get_composition()
        self.seeks = {}
        self.provides = {}                
        int_col_deck = InterfaceCollection.from_deck(self)
        int_col_fb   = InterfaceCollection.from_forgeborn(self.forgeborn)
        self.ICollection = int_col_deck.update(int_col_fb)
        self.populate()
        


    @classmethod
    def empty(cls):
        return cls("", None, "", {})

    def populate(self):

        for card_name, card in self.cards.items():            
            if card.provides :
                self.provides = dict(Counter(self.provides) + Counter(card.provides))
            if card.seeks :
                self.seeks    = dict(Counter(self.seeks) + Counter(card.seeks))

    def get_rarities(self):
        card_counter, forge_counter = 0, 0

        for card in self.cards.values():
            rarities = card.get_rarities()
            card_rarity, *forge_rarity = rarities

            card_counter += card_rarity.split(',')[0] == 'Rare'
            forge_counter += forge_rarity == ['Rare'] if forge_rarity else 0

        return [card_counter, forge_counter]

    def get_composition(self):        
        composition = {}        
        for card in self.cards.values():            
            #for synergy, interfaces in card.ICollection.get_interfaces_by_type('O').items():
            for subtype in card.card_subtype.split(' '):
                #composition[synergy] = composition.get(synergy, 0) + len(interfaces)
                subtype = subtype.strip()
                composition[subtype] = composition.get(subtype, 0) + 1
            for cardtype in card.card_type.split(' '):
                composition[cardtype] = composition.get(cardtype, 0) + 1
        return composition

        
    def __add__(self, other):      
        name = self.name + '|' + other.name
        if self.faction == other.faction : 
            #print(f"{name} : Deck fusion invalid. Same faction {self.faction}\n")
            return 
        forgeborn = self.forgeborn        
        faction = self.faction + '|' + other.faction                 
        cards = { **self.cards, **other.cards} 
        
        return Deck(name, forgeborn, faction, cards)

    def to_json(self):
        return {
            "name": self.name,
            "faction": self.faction,
            "forgeborn": self.forgeborn.to_json(),
            "cards": [str(card) for card in self.cards.values()]
        }    
    
    def __eq__(self, other):
        if isinstance(other, Deck):
            return self.name == other.name
        return False
    
    def __str__(self):     
        card_titles = [card.title for card in self.cards.values()]
        return f"Deck Name: {self.name}\nFaction: {self.faction}\nForgeborn: {self.forgeborn}\nCards:\n{', '.join(card_titles)}\n"   


class Fusion:
    def __init__(self, name, decks):
        self.name = name
        self.fused = self.decks_to_fusion(decks)
        self.decks = decks

    def decks_to_fusion(self, decks):
        fused = decks[0]
        for deck in decks[1:]:
            fused += deck
        return fused

    def getDeck(self):               
        return self.fused
    
    def to_json(self):
        return {
            "name": self.name,                        
            "decks": [deck.to_json() for deck in self.decks]            
        }


class Forgeborn:
    def __init__(self, name, faction, abilities):
        self.name = name
        self.faction = faction
        self.abilities = abilities        
        self.ICollection = InterfaceCollection.from_forgeborn(self)

    def __str__(self):
        abilities_str = "\n".join([f"  {ability}: {text}" for ability, text in self.abilities.items()])
        return f"Forgeborn Name: {self.name}\nFaction: {self.faction}\nAbilities:\n{abilities_str}\n"


    def to_json(self):
        return {
            "title": self.name,
            "faction": self.faction,
            "abilities": list(self.abilities.keys())
        }

class Card():
    def __init__(self, card, modifier=None): 
        self.entities = [card]             
        self.faction  = card.faction
        self.provides = card.provides
        self.seeks = card.seeks
        if modifier:
            self.title = modifier.name + ' ' + card.name
            if isinstance(modifier, Entity):
                self.entities.append(modifier)
                self.provides = dict(Counter(self.provides) + Counter(modifier.provides))
                self.seeks    = dict(Counter(self.seeks)    + Counter(modifier.seeks))
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
            "provides": self.provides,
            "seeks": self.seeks            
        }

class UniversalCardLibrary:

    entities = []

    def __init__(self, csv_path):        
        self.entities = self._read_entities_from_csv(csv_path)

    def _read_forgeborn_from_csv(self, csv_path):
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                id   = row['id']
                title =  row['Forgeborn']  
                card_type = 'Ability'                             
                abilities = {}
                for level in range(3):                    
                    level += 1
                    name = int(row[f"{level}name"]) if row.get(f"{level}name") else 0
                    text = int(row[f"{level}text"]) if row.get(f"{level}text") else 0
                    abilities[level] = {
                        'name': row[name],
                        'text': row[text]                                                        
                    }
                    Collection = InterfaceCollection(name)
                    #TODO: to continue ...

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
                forgeborn_data = deck_data['forgeborn']
                # If 'abilities' key is in forgeborn_data, use it.
                # Else, create a list from the keys 'a2n', 'a3n', 'a4n' if they exist.
                if 'abilities' in forgeborn_data:
                    abilities_data = forgeborn_data['abilities']
                else:
                    abilities_data = [forgeborn_data[code] for code in ['a2n', 'a3n', 'a4n'] if code in forgeborn_data]
                # Now abilities_data is always a list, so we can create the abilities.
                abilities = {ability_name: self.search_entity(ability_name,card_type='Ability') for ability_name in abilities_data}
       
                forgeborn_name = forgeborn_data['title'] if 'title' in forgeborn_data else forgeborn_data['name']
                forgeborn = Forgeborn(forgeborn_name, deck_data['faction'],abilities)
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

                        # Extract additional data from the card dictionary
                        default_value = 1
                        provides = card.get('provides')
                        seeks = card.get('seeks')
                        list_provides = provides.split(', ') if provides else {}
                        list_seeks = seeks.split(', ') if seeks else {}
                        
                        # Add the additional data to the cards_additional_data dictionary
                        #cards_additional_data.setdefault(card_title, {})['betrayer'] = card.get('betrayer')
                        cards_additional_data.setdefault(card_title, {})['provides'] = {key: default_value for key in list_provides}
                        cards_additional_data.setdefault(card_title, {})['seeks'] = {key: default_value for key in list_seeks}

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
                    fusion = Fusion(name, decks)
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
  




        
