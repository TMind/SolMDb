from dataclasses import asdict
import Card_Library
#from CardLibrary import EntityData, Entity, Forgeborn, Deck, ForgebornData, Fusion, Card
from Interface import InterfaceCollection, Interface, InterfaceData
from pymongo.operations import UpdateOne
#from MongoDB.DatabaseManager import DatabaseManager
import GlobalVariables as gv
from typing import Tuple, List, Dict
import csv, json, re

class UniversalLibrary:

    entities = []

    def __init__(self, username, sff_path, fb_path, syn_path):        
        self.database = gv.commonDB
        # Check if the database is empty and fill it with the data from the csv files            
        numFB = self.database.count_documents('Forgeborn')
        numEnt = self.database.count_documents('Entity')

        if numFB <= 0 :
            self.database.ensure_unique_index('Forgeborn', 'id')
            self._read_forgeborn_from_csv(fb_path)
        
        if numEnt <= 0:
            self.database.ensure_unique_index('Entity', 'name')        
            self._read_entities_from_csv(sff_path)
        

    def _read_forgeborn_from_csv(self, csv_path):
        forgeborn_list = []
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                id = row['id']
                id = id.replace('0', '2')                
                re.sub(r'^a', 's', id)
                title =  row['Forgeborn']                                 
                abilities = []
                for level in range(3):                    
                    level += 2
                    name = row[f"{level}name"] if row.get(f"{level}name") else ""
                    text = row[f"{level}text"] if row.get(f"{level}text") else ""                 
                    name = f"{level}{name}"
                    abilities.append(name)

                # Add the class and module name to the forgeborn_list
                forgeborn = Card_Library.Forgeborn(Card_Library.ForgebornData(id, title, abilities))                       
                forgeborn_list.append(forgeborn.to_data())

        # Insert the forgeborn_list into the database        
        self.database.bulk_write('Forgeborn', [
            UpdateOne(
                {'_id': forgeborn['_id']}, 
                {'$setOnInsert': forgeborn}, 
                upsert=True
            ) for forgeborn in forgeborn_list
        ])              
        
    def _read_entities_from_csv(self, csv_path):   
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:    
                keys = ['rarity', 'cardType', 'cardSubType', 'spliced', 'solbind']            
                attributes = {k: row[k] for k in keys if k in row}
                entityName = row['Name']
                faction = row['faction']  
                abilities = {}
                
                for ability in row.keys():
                    if ability.endswith('text'):
                        level = ability[0]
                        attack = int(row[f"{level}attack"]) if row.get(f"{level}attack") else 0
                        health = int(row[f"{level}health"]) if row.get(f"{level}health") else 0
                        abilities[level] = {
                            'text': row[ability],
                            'attack': attack,
                            'health': health
                        }
                                                                 
                interfaceNames = []
                vrange = ''
                
                read_synergies = False
                for tag, value in row.items():
                    if tag == "3text":
                        read_synergies = True   
                    elif read_synergies:
                        vrange   = ""
                        if value is not None:                             
                            if not value.isnumeric():
                                if tag == "Free":                                    
                                    tag = f"Free {value}"            
                                    value = 1
                                    
                                else: 
                                    vrange = value
                                    if   value == '*':  value = 1                                        
                                    elif value == '+':  value = 1
                                    elif value == '.':  value = 0
                                    else:
                                        vrange = ''
                                        value = 0
                                    
                            if int(value) > 0:                                                                
                                    interface_data = InterfaceData(tag, value, vrange)
                                    Interface(interface_data).save()
                                    #ISyn.save()
                                    ##Add the class and module name to the children_data dictionary
                                    #class_name = ISyn.__class__.__name__
                                    #module_name = ISyn.__module__
                                    interfaceNames.append(tag) 
                                    #children_data[tag] = ISyn.getClassPath()
                
                #interfaceCollection_data = Collection.to_data()
                
                entity_data = Card_Library.EntityData(entityName, faction, attributes, abilities, vrange, interfaceNames)
                entity = Card_Library.Entity(entity_data)
                #self.entities.append(Entity(name, faction, attributes, abilities, Collection))
                result = entity.save()
                #result = self.database.upsert('Entity', {'name': entity.name}, data=entity.to_data())
            
        #return self.entities

    def get_entity(self,name, cardType=None):
        #print(f"Searching Entity: {name}")
        query = {'name': name}
        if cardType:
            query['attributes.cardType'] = cardType 
        entity_data = self.database.find_one('Entities', query)
        return Card_Library.Entity.from_data(entity_data)

    def get_forgeborn(self, id):
        query = {'id': id}
        forgeborn = self.database.find_one('Forgeborns',query)
        if forgeborn:
            return Card_Library.Forgeborn.from_data(forgeborn)
        else:
            print(f"Forgeborn {id} could not be found")
        return None

    def load_decks_from_file(self, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)            
        return self.load_decks_from_data(data)

    def load_decks_from_data(self, decks_data: List[Dict]) -> Tuple[List[Card_Library.Deck], List[Dict]]:

        decks = []
        incomplete_data = []
        
        for deck_data in decks_data:            
            try:
                forgebornId = deck_data['forgebornId']#[1:]
                forgebornId = forgebornId.replace('0','2')
                forgeborn = self.database.find_one('Forgeborns', {'id': forgebornId})
                #forgebornKey = [key for key in self.forgeborn if forgebornId in key]
                #forgeborn = self.forgeborn[forgebornKey[0]]
            

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

            deck = Card_Library.Deck(deck_data['name'], forgeborn, deck_data['faction'], cards)
            decks.append(deck)
            
        return decks, incomplete_data

        
    def load_fusions(self, fusions_data: List[Dict]) -> Tuple[List[Card_Library.Fusion], List[Dict]]:
        fusions = []
        incomplete_fusionsdata = []

        for fusion_data in fusions_data:            
                decks, incomplete_decksdata = self.load_decks_from_data(fusion_data['myDecks'])
                name = fusion_data['name'] if 'name' in fusion_data else ""
                if decks:
                    fusion = Card_Library.Fusion(decks, name)
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
        entity_data = self.database.get_record_by_name('Entities', card_title)        
        if entity_data:
            for key, value in card_data_additional.items():                
                setattr(entity_data, key, value)
            #return Card(card_entity)
            return Card_Library.Entity.from_data(entity_data)

        # If not found, try with decreasing title length
        parts = card_title.split(' ')
        for i in range(1, len(parts)):
            modifier_title = ' '.join(parts[:i])
            card_title = ' '.join(parts[i:])
            modifier_entity = self.database.get_record_by_name('Entities', modifier_title)
            entity_data = self.database.get_record_by_name('Entities', card_title)
            if modifier_entity and entity_data:
                for key, value in card_data_additional.items():
                    existing_value = getattr(entity_data, key)  # Get existing value or use an empty dictionary
                    if isinstance(existing_value, dict):
                        merged_value = {**existing_value, **value}  # Merge the dictionaries
                        setattr(entity_data, key, merged_value)
                    elif value:
                        setattr(entity_data, key, value)  # Set the new value directly
                
                return Card_Library.Entity.from_data(entity_data), Card_Library.Entity.from_data(modifier_entity)
        return None
                
    def __str__(self):
        entity_strings = []
        for entity in self.entities:
            entity_strings.append(str(entity))
        return "\n".join(entity_strings)    
  
