import csv
from http.client import NETWORK_AUTHENTICATION_REQUIRED
import json
from Synergy import SynergyTemplate
from Interface import Interface, InterfaceCollection

class UniversalCardLibrary:

    entities = []

    def __init__(self, csv_path):
        self.synergy_template = SynergyTemplate()
        self.entities = self._read_entities_from_csv(csv_path)

    def _read_entities_from_csv(self, csv_path):   
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
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
                                  
               # sources = {}
               # targets = {}
                Collection = InterfaceCollection()
                range   = ""
                read_synergies = False
                for key, value in row.items():
                    if key == "3text":
                        read_synergies = True   
                    elif read_synergies:
                        if value is not None:                            
                            if not value.isnumeric():
                                if key == "Free":                                    
                                    key = f"Free {value}"            
                                    value = 1
                                else: 
                                    if value == '*':
                                        range = '*'
                                        value = 1                                        
                                    if value == '+': 
                                        range = '+'
                                        value = 1
                                    if value == '.': 
                                        range = '.'     
                                        value = 0
                                    
                            elif int(value) > 0:                                                                    
                                # if key in self.synergy_template.get_source_tags():
                                #     sources.setdefault(key, 0)
                                #     sources[key] += 1  
                                    ISyn = Interface(name, key, value)
                                    ISyn.range = range
                                    Collection.add(ISyn)
                                # if key in self.synergy_template.get_target_tags():                                
                                #     targets.setdefault(key, 0)  
                                #     targets[key] += 1                               
                                    

                self.entities.append(Entity(name, faction, rarity, card_type, card_subtype, spliced, solbind, abilities, Collection))
        return self.entities

    def search_entity(self,name):
        #print(f"Searching Entity: {name}")
        for entity in self.entities:
            if entity.name == name:
                return entity
        return None

    def load_decks(self,filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)

        decks = {}

        for deck_data in data:
            forgeborn_data = deck_data['forgeborn']
            abilities = {}
            for ability_name in forgeborn_data['abilities']:
                ability = self.search_entity(ability_name)
                abilities[ability_name] = ability
            forgeborn = Forgeborn(forgeborn_data['title'], deck_data['faction'],abilities)
                                  #forgeborn_data['abilities'])

            cards = {}
            card_titles = deck_data['cards']
            for card_title in card_titles:
                card = self.create_card_from_title(card_title)
                cards[card_title] = card
            deck = Deck(deck_data['name'], forgeborn, deck_data['faction'], cards)
            decks[deck.name] = (deck)
            
        return decks


    def load_decks_online(self,filename):
        with open(filename, 'r') as f:
            content = f.read()
            data = json.loads(content)

        decks_data = data['Items']
        decks = []
        

        for deck_data in decks_data:
            forgeborn_data = deck_data['forgeborn']
            abilities = {}
            for ability_code in ['a2n','a3n','a4n']:
                ability_name = forgeborn_data[ability_code]
                ability = self.search_entity(ability_name)
                abilities[ability_name] = ability
                #print(f"Ability Code: {ability_code} -> {ability_name} -> {ability}")
                

            forgeborn = Forgeborn(forgeborn_data['title'], deck_data['faction'],abilities)

            cards_data = deck_data['cards']
            cards = {}

            for card_data in cards_data.values():
                card_title = str(card_data['title'])                                
                card = self.create_card_from_title(card_title)
                cards[card_title] = card;

            deck = Deck(deck_data['name'], forgeborn, deck_data['faction'], cards)
            decks.append(deck)

        return decks
    
    def create_card_from_title(self, card_title):
        # First try with full title
        card_entity = self.search_entity(card_title)
        if card_entity:
            return Card(card_entity)

        # If not found, try with decreasing title length
        parts = card_title.split(' ')
        for i in range(1, len(parts)):
            modifier_title = ' '.join(parts[:i])
            card_title = ' '.join(parts[i:])
            modifier_entity = self.search_entity(modifier_title)
            card_entity = self.search_entity(card_title)
            if modifier_entity and card_entity:
                return Card(card_entity, modifier_entity)

        # If no entities found, create a card with just the card title
        return Card(Entity(name=card_title, card_type='Unknown'))
                
    def __str__(self):
        entity_strings = []
        for entity in self.entities:
            entity_strings.append(str(entity))
        return "\n".join(entity_strings)    
  


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
        self.ICollection = Collection
        #self.sources = sources
        #self.targets = targets or {}
  
    def __str__(self):
        trait_str = ", ".join([f"{trait}" for trait in self.sources.items()])
        synergy_str = ", ".join([str(synergy) for synergy in self.targets.values()])
        return f"{self.name} ({self.card_type} - {self.card_subtype})\nTraits: {trait_str}\nSynergies: {synergy_str}"
    
    def to_json(self):
        return {
            "title": self.name
        }

class Deck:
    def __init__(self, name, forgeborn, faction, cards):
        self.name = name
        self.forgeborn = forgeborn
        self.faction = faction
        self.cards = cards      
        int_col_deck = InterfaceCollection.from_deck(self,SynergyTemplate())
        int_col_fb   = InterfaceCollection.from_forgeborn(self.forgeborn, SynergyTemplate())
        self.ICollection = int_col_deck.update(int_col_fb)

    def __add__(self, other):      
        name = self.name + '|' + other.name
        if self.faction == other.faction : 
            #print(f"{name} : Deck fusion invalid. Same faction {self.faction}\n")
            return 
        forgeborn = self.forgeborn
        faction = self.faction + '|' + other.faction 
        cards = { **self.cards, **other.cards} 
        #cards = dict(list(self.cards.items()) + list(other.cards.items()))
        return Deck(name, forgeborn, faction, cards)

    def to_json(self):
        return {
            "name": self.name,
            "faction": self.faction,
            "forgeborn": self.forgeborn.to_json(),
            "cards": [str(card) for card in self.cards.values()]
        }    
    
    def __str__(self):     
        card_titles = [card.title for card in self.cards.values()]
        return f"Deck Name: {self.name}\nFaction: {self.faction}\nForgeborn: {self.forgeborn}\nCards:\n{', '.join(card_titles)}\n"   


class Forgeborn:
    def __init__(self, name, faction, abilities):
        self.name = name
        self.faction = faction
        self.abilities = abilities        
        self.ICollection = InterfaceCollection.from_forgeborn(self, SynergyTemplate())

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
        if modifier:
            self.title = modifier.name + ' ' + card.name
            if isinstance(modifier, Entity):
                self.entities.append(modifier)
        else:
            self.title = card.name
        self.ICollection = InterfaceCollection.from_entities(self.entities)

    def __str__(self):
        return self.title

    def to_json(self):
        return {
            "title": self.title
        }

        
