import CardLibrary
from Interface import Interface, InterfaceData
from typing import Tuple, List, Dict
import csv, json, re, os

from MongoDB.DatabaseManager import DatabaseManager, BufferManager
from GlobalVariables import global_vars as gv 

class UniversalLibrary:

    entities = []

    def __init__(self, username, worksheet, fb_path, syn_path):        
        self.database = DatabaseManager('common')
        self.forgeborns = {}
        self.fb_map = {} 

        # Check if the database is empty and fill it with the data from the csv files            
        numFB = self.database.count_documents('Forgeborn')
        numEnt = self.database.count_documents('Entity')

        if numFB <= 1 or numEnt <= 0:
            #self.database.ensure_unique_index('Forgeborn', 'id')                    
            #self.database.ensure_unique_index('Entity', 'name') 
            buffer_manager = BufferManager(os.getenv('MONGODB_URI', None))
            with buffer_manager:       
                print("Using the buffer manager") 
                self.fb_map = self._read_forgeborns_from_csv()
                buffer_manager.write_buffers()
                self._read_entities_from_csv()           
            
    def _read_entities_from_csv(self):   
        """
        Fetches and processes entities from a Google Sheet using the GoogleSheetsClient.
        """
        # Get the rows from the CMManager
        sff_path = gv.cm_manager.local_sff_path if gv.cm_manager else 'csv/sff.csv'
        if not os.path.exists(sff_path):
            if gv.cm_manager:
                gv.cm_manager.update_local_csv('Card Database')
            else:
                raise FileNotFoundError(f"Local CSV {sff_path} not found. Download it from the Google Sheet first.")
            
        with open(sff_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            rows_list = list(reader)  # Store all rows in a list
            for row in rows_list:
                gv.progress_manager.update_progress('Process Entity Row', total=len(rows_list), message='Processing CM entity: ' + row['Name'])
                self._process_row(row)
        
    def _read_forgeborns_from_csv(self):
        fb_path = gv.cm_manager.local_fb_path if gv.cm_manager else 'csv/forgeborn.csv'
         # Get the rows from the CMManager
        if not os.path.exists(fb_path):
            if gv.cm_manager:
                gv.cm_manager.update_local_csv('FB Abilities Map')
            else:
                raise FileNotFoundError(f"Local CSV {fb_path} not found. Download it from the Google Sheet first.")
            
        fb_map = {}
        with open(fb_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            rows_list = list(reader)  # Store all rows in a list
            
            # Iterate over the rows
            for row in rows_list:
                gv.progress_manager.update_progress('Process FB Row', total=len(rows_list), message='Processing CM ForgebornID: ' + row['forgebornID'])
                forgeborn_ability_id = row['forgebornID']
                actual_forgeborn_ability_id = self.update_fb_faction_id(forgeborn_ability_id)
                card_id = row['cardId']
                if card_id not in fb_map:
                    fb_map[card_id] = []
                fb_map[card_id].append(actual_forgeborn_ability_id)
        return fb_map  

    def update_fb_faction_id(self, forgeborn_id):
        """Updates the Forgeborn faction ID by inserting the correct faction identifier."""

        if len(forgeborn_id) < 7:
            return forgeborn_id

        set_prefix = forgeborn_id[:2]
        forgeborn = forgeborn_id[2:-5]
        fb_ability_id = forgeborn_id[-5:]

        forgeborn_faction_dict = {
            # 's1': {
            #     'aa1': ['ironbeard', 'steel-rosetta', 'crux-cobalt'],
            #     'nn1': ['nix-nekia', 'cercee'],
            #     'tt1': ['sunder', 'korok'],
            #     'uu1': ['oros', 'nova']
            # },
            's4': {
                'aa1': ['ironbeard' , 'steel-rosetta' , 'crux-cobalt' ,          'blighted-sunder' , 'blighted-cercee'],
                'nn1': ['nix-nekyia', 'toxys-mori'    ,                          'blighted-sunder' , 'blighted-cercee'],
                'tt1': ['korok'                       ,                          'blighted-sunder' , 'blighted-cercee'],
                'uu1': ['oros'      , 'nova'          ,  'tyran'      ,'tundra', 'blighted-sunder' , 'blighted-cercee']
            }
        }

        # Check if the set prefix exists in the dictionary
        if set_prefix in forgeborn_faction_dict:
            for faction_id, ids in forgeborn_faction_dict[set_prefix].items():
                for fb_name in ids:
                    if fb_name in forgeborn:
                        return f"{set_prefix}{faction_id}{fb_name}{fb_ability_id}"

        return forgeborn_id  # Return original if no match is found

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
                                  
        interfaces = {}                          
        vrange = ''
        
        read_synergies = False
        for tag, value in row.items():
            if tag == "3text":
                read_synergies = True   
            elif read_synergies:
                vrange   = ""
                if value is not None:  
                    # Replace comma with dot if exists  
                    value = value.replace(',', '.')  
            
                    # Check for special values  
                    if value == '*':  
                        value = 1  
                    elif value == '+':  
                        value = 1  
                    elif value == '.':  
                        value = 0  
                    else:  
                        # Try to convert to float  
                        try:  
                            value = float(value)  
                        except ValueError:  
                            value = 0 
                            
                    if value > 0:                                                                
                            interface_data = InterfaceData(tag, value, vrange)
                            Interface(interface_data).save()        
                            interfaces[tag] = value 

        is_forgeborn_ability = attributes['cardType'] == 'forgeborn-ability'
        is_fraud_ability = attributes['cardType'] == 'Fraud' or 'fraud-legs' in attributes['id']

        name = entityName
        entity_data = CardLibrary.EntityData(name, faction, attributes, abilities, vrange, interfaces)
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
        """
        Processes a Forgeborn ability by identifying the associated Forgeborn ID and name, 
        then updates the database accordingly.

        Args:
            ability: Object containing ability details, including an 'id' and 'name'.
        """
        forgeborn_ability_ids = self.fb_map.get(ability.id)
        
        if not forgeborn_ability_ids:
            print(f"Could not find Forgeborn abilities for {ability.id}")
            return
        
        for forgeborn_ability_id in forgeborn_ability_ids:
            if not forgeborn_ability_id:
                print(f"Could not find Forgeborn ability for {ability.id}")
                continue

            # Determine where the Forgeborn name starts based on faction ID
            faction_prefixes = {'aa', 'nn', 'uu', 'tt'}
            forgeborn_name_position = 5 if forgeborn_ability_id[2:4] in faction_prefixes else 2

            # Extract Forgeborn ID and name
            forgeborn_id = forgeborn_ability_id[:-5]
            forgeborn_name = forgeborn_id[forgeborn_name_position:]

            # Check if Forgeborn entry exists in the database
            fb_entry = self.database.find_one('Forgeborn', {'id': forgeborn_id})

            # If the Forgeborn does not exist, create an entry
            if not fb_entry:
                self.database.insert(
                    'Forgeborn',
                    {'id': forgeborn_id, 'name': forgeborn_name, 'abilities': {}}
                )

            # Update the Forgeborn abilities field using $set to avoid overwriting existing data
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
  
