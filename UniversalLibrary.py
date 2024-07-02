from dataclasses import asdict
import CardLibrary
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
        self.forgeborns = {}
        self.fb_map = {} 

        # Check if the database is empty and fill it with the data from the csv files            
        numFB = self.database.count_documents('Forgeborn')
        numEnt = self.database.count_documents('Entity')

        if numFB <= 1 or numEnt <= 0:
            self.database.ensure_unique_index('Forgeborn', 'id')                    
            self.database.ensure_unique_index('Entity', 'name')        
            self.fb_map = self._read_forgeborns_from_csv(fb_path)
            self._read_entities_from_csv(sff_path)           
        
    def _read_entities_from_csv(self, csv_path):   
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:    
                self._process_row(row)

    def _read_forgeborns_from_csv(self, fb_path):
        fb_map = {}
        with open(fb_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                forgeborn_ability_id = row['forgebornID']
                card_id = row['cardId']
                #forgeborn_id = forgeborn_ability_id[:-5]
                #if forgeborn_id not in self.forgeborns:
                #    forgeborn_name = forgeborn_id[5:].capitalize()
                #    self.forgeborns[forgeborn_id] = Forgeborn(forgeborn_id, forgeborn_name)
                if card_id not in fb_map:
                    fb_map[card_id] = []
                fb_map[card_id].append(forgeborn_ability_id)
        return fb_map  

    def _process_row(self, row):
        keys = ['id', 'Name', 'rarity', 'cardType', 'cardSubType', 'spliced', 'solbind']            
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
                            interfaceNames.append(tag) 

        is_forgeborn_ability = attributes['cardType'] == 'forgeborn-ability'
        is_fraud_ability = attributes['cardType'] == 'Fraud' or 'fraud-legs' in attributes['id']

        name = entityName
        entity_data = CardLibrary.EntityData(name, faction, attributes, abilities, vrange, interfaceNames)
        entity = CardLibrary.Entity(entity_data)        
        result = entity.save()

        # Process Forgeborn abilities
        if is_forgeborn_ability:
            ability = CardLibrary.ForgebornAbility(attributes['id'], name, entity)
            self._process_forgeborn_ability(ability)
        elif is_fraud_ability:
            ability = CardLibrary.ForgebornAbility(attributes['id'], name, entity)
            self._process_fraud_ability(ability)


    def _process_fraud_ability(self, ability):
        
        fraud = self.database.find_one('Forgeborn', {'id': 'fraud'})
        if not fraud:
            self.database.insert('Forgeborn', {'id': "fraud", 'name': "Fraud's Experiment", 'abilities': {}} )

        self.database.update_one( 'Forgeborn', 
            {'id': 'fraud'},
            {f'abilities.{ability.id}': ability.name}
        )

    def _process_forgeborn_ability(self, ability):
        forgeborn_ability_ids = self.fb_map.get(ability.id, [])
        
        for forgeborn_ability_id in forgeborn_ability_ids:
            forgeborn_id = forgeborn_ability_id[:-5]
            forgeborn_name = forgeborn_id[5:]

            # Handle Forgeborn
            # Create or update Forgeborn entry
            fb = self.database.find_one('Forgeborn', {'id': forgeborn_id})

            if not fb:
                self.database.insert('Forgeborn', {'id': forgeborn_id, 'name': forgeborn_name, 'abilities': {}})            

            self.database.update_one( 'Forgeborn', 
                {'id': forgeborn_id},
                {f'abilities.{forgeborn_ability_id}': ability.name}
            )

    def get_entity(self,name, cardType=None):
        #print(f"Searching Entity: {name}")
        query = {'name': name}
        if cardType:
            query['attributes.cardType'] = cardType 
        entity_data = self.database.find_one('Entities', query)
        return CardLibrary.Entity.from_data(entity_data)

    def get_forgeborn(self, id):
        query = {'id': id}
        forgeborn = self.database.find_one('Forgeborns',query)
        if forgeborn:
            return CardLibrary.Forgeborn.from_data(forgeborn)
        else:
            print(f"Forgeborn {id} could not be found")
        return None

    def load_decks_from_file(self, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)            
        return self.load_decks_from_data(data)

    def load_decks_from_data(self, decks_data: List[Dict]) -> Tuple[List[CardLibrary.Deck], List[Dict]]:

        decks = []
        incomplete_data = []
        
        for deck_data in decks_data:            
            try:
                print(f"Original forgebornId from deck_data: {deck_data['forgebornId']}")
                forgebornId = deck_data['forgebornId']
                forgebornId = forgebornId.replace('0','2')
                print(f"forgebornId after replacement: {forgebornId}")
                forgeborn_unique_id = forgebornId[:-3]
                print(f"forgeborn_unique_id extracted: {forgeborn_unique_id}")
                forgeborn_unique = self.database.find_one('Forgeborns', {'id': forgeborn_unique_id})
                print(f"Document found for forgeborn_unique_id: {forgeborn_unique}")
                unique_forgeborn = CardLibrary.Forgeborn.from_data(forgeborn_unique)
                print(f"unique_forgeborn object created: {unique_forgeborn}")
                forgeborn = unique_forgeborn.get_permutation(forgebornId)
                print(f"Final forgeborn object after permutation: {forgeborn}")

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
            deckData = CardLibrary.DeckData(name=deck_data['name'], forgebornId=forgebornId, faction=deck_data['faction'], cards=cards)
            deck = CardLibrary.Deck(deckData)
            decks.append(deck)
            
        return decks, incomplete_data

        
    def load_fusions(self, fusions_data: List[Dict]) -> Tuple[List[CardLibrary.Fusion], List[Dict]]:
        fusions = []
        incomplete_fusionsdata = []

        for fusion_data in fusions_data:            
                decks, incomplete_decksdata = self.load_decks_from_data(fusion_data['myDecks'])
                name = fusion_data['name'] if 'name' in fusion_data else ""
                if decks:
                    fusion = CardLibrary.Fusion(decks, name)
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
            return CardLibrary.Entity.from_data(entity_data)
        elif "Fraud's Experiment" in card_title:
            # Assemble Fraud parts from Forgeborn Fraud's Experiment
            fraud_parts = card_title.split(" ")
            fraud_id = fraud_parts[-1]
            fraud_data = self.database.find_one('Forgeborn', {'id': 'fraud'})
            fraud = CardLibrary.Forgeborn.from_data(fraud_data)
            fraud_base_id, fraud_modifier_ids = fraud.get_fraud_monster(fraud_id)
            
            fraud_base_entity = self.database.find_one('Entity', {'id' : fraud_base_id })
            fraud_modifier_entities = {id: self.database.find_one('Entity', {'id': id}) for id in fraud_modifier_ids}
            
            if fraud_base_entity and fraud_modifier_entities:
                return fraud_base_entity, fraud_modifier_entities
            else:
                print(f"Unable to find fraud abilities for: {card_title}")
                return None

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
                
                return CardLibrary.Entity.from_data(entity_data), CardLibrary.Entity.from_data(modifier_entity)
        return None
                
    def __str__(self):
        entity_strings = []
        for entity in self.entities:
            entity_strings.append(str(entity))
        return "\n".join(entity_strings)    
  
