import csv, json
from Interface import Interface, InterfaceCollection
from typing import List, Tuple, Dict
from copy import copy

class Entity:
    def __init__(self, name, faction, attributes, abilities, Collection):
        self.name = name
        self.attributes = attributes
        self.faction = faction      
        self.abilities = abilities        
        self.provides = {sub_type: 1 for subtype in attributes['cardSubType'].split(',') for sub_type in subtype.split(' ')}
        self.provides.update({attributes['cardType']: 1})
        self.ICollection = Collection
  
    def __str__(self):
        return f"{self.name}"

class ForgebornAbility:
    def __init__(self, id, name, entity):
        self.id = id
        self.name = name
        self.entity = entity 

class Forgeborn:
    def __init__(self, id, name):
        self.id = id 
        self.name = name
        self.abilities = {}        
        self.ICollection = {} 

    def add_ability(self, ability):
        self.abilities[ability.id] = ability.entity        
        self.create_interface_collection()

    def get_permutation(self, forgeborn_id):
        ability_ids = self._construct_ability_ids(forgeborn_id)
        new_forgeborn = Forgeborn(self.id, self.name)
        new_forgeborn.abilities = {aid: self.abilities[aid] for aid in ability_ids if aid in self.abilities}
        new_forgeborn.create_interface_collection()
        return new_forgeborn

    def _construct_ability_ids(self, forgeborn_id):
        ability_prefix = self.id 
        ability_ids = []
        ability_data = forgeborn_id[len(self.id):]
        
        for i in range(0, len(ability_data)):
            number = ability_data[i]
            cycle = i + 2
            ability_id = f"{ability_prefix}-c{cycle}a{number}"
            ability_ids.append(ability_id)
        
        return ability_ids

    def create_interface_collection(self):
        self.ICollection = InterfaceCollection.from_entities(self.name, self.abilities.values())

    def __str__(self):
        abilities_str = "\n".join([f"  {ability}: {text}" for ability, text in self.abilities.items()])
        return f"Forgeborn Name: {self.name}\nAbilities:\n{abilities_str}\n"

class Card:
    def __init__(self, card, modifier=None): 
        self.entities = [card]             
        self.faction  = card.faction
        if modifier:
            self.title = modifier.name + ' ' + card.name
            if isinstance(modifier, Entity):
                self.entities.append(modifier)        
        else:
            self.title = card.name        
        self.cardType = card.attributes['cardType']
        self.cardSubType = card.attributes['cardSubType']
        self.name = self.title
        self.ICollection = InterfaceCollection.from_card(self)        
        
        def aggregate_attribute(attribute_name):
            aggregated = {}
            for entity in self.entities:                
                for level in entity.abilities:
                    aggregated[level] = aggregated.get(level, 0) + entity.abilities[level][attribute_name]  
            return aggregated      

        self.attack = aggregate_attribute('attack')
        self.health = aggregate_attribute('health')
        self.above_stat = {'attack': {}, 'health': {}}

        for stat in self.above_stat.keys():
            stats = getattr(self, stat)
            for level in stats: 
                self.above_stat[stat][level] = stats[level] >= 3 * (level + 1)

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
            for subtype in card.cardSubType.split(' '):                
                subtype = subtype.strip()
                composition[subtype] = composition.get(subtype, 0) + 1
            for cardtype in card.cardType.split(' '):
                composition[cardtype] = composition.get(cardtype, 0) + 1
            for stat in card.above_stat.keys():
                for level in card.above_stat[stat]:
                    entry = f"{level}{stat}"
                    composition[entry] = composition.get(entry, 0) + int(card.above_stat[stat][level])
        return composition
    
    def update_ICollection_with_forgeborn(self):
        self.ICollection = self.ICollectionDeck.copy()
        self.ICollection.update(self.forgeborn.ICollection)

    def associate_cards_with_factions(self, cards: Dict[str, Card], faction: str) -> Dict[str, Card]:
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

        fusion_name = "_".join([deck.name for deck in decks])        
        self.fused_name = name or "_".join(sorted([deck.name for deck in decks]))
        self.fused_faction = "|".join([deck.faction for deck in decks]) 
        fused_cards = {**deck1.cards, **deck2.cards}
        
        self.deck1 = deck1
        self.deck2 = deck2
        self.forgeborn_options = self.inspire_forgeborn(deck1.forgeborn, deck2.forgeborn)
        self.fused_abilities = [ability for forgeborn in self.forgeborn_options for ability in forgeborn.abilities]

        self.active_forgeborn = self.forgeborn_options[0]
        super().__init__(name or fusion_name, self.active_forgeborn, self.fused_faction, fused_cards)        
        self.abilities = self.fused_abilities
        
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
                            ability_id_replace_name = next((ability_id for ability_id in new_abilities.keys() if ability_id[-3] == level), None)
                            if ability_id_replace_name:
                                new_abilities.pop(ability_id_replace_name)
                            new_abilities[other_ability.name] = other_ability
                            break
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
        new_forgeborn = self.active_forgeborn
        if isinstance(idx_or_forgeborn_name, int):
            new_forgeborn = self.forgeborn_options[idx_or_forgeborn_name]
        else:
            new_forgeborn = self.get_forgeborn(idx_or_forgeborn_name)
        self.abilities = new_forgeborn.abilities
        if self.active_forgeborn == new_forgeborn:
            return
        self.active_forgeborn = new_forgeborn
        if self.active_forgeborn == self.forgeborn_options[0]:
            self.name = f"{self.deck1.name}_{self.deck2.name}"
            self.faction = f"{self.deck1.faction}|{self.deck2.faction}"
        else:
            self.name = f"{self.deck2.name}_{self.deck1.name}"
            self.faction = f"{self.deck2.faction}|{self.deck1.faction}"
        self.forgeborn = self.active_forgeborn    
        self.update_ICollection_with_forgeborn()
 
    def copyset_forgeborn(self, idx_or_forgeborn_name):
        final_fusion = copy(self)
        final_fusion.set_forgeborn(idx_or_forgeborn_name)
        return final_fusion

    def get_forgeborn(self, id_or_forgeborn_name):        
        if isinstance(id_or_forgeborn_name, int):
            return self.forgeborn_options[id_or_forgeborn_name]
        else:
            for forgeborn in self.forgeborn_options:
                if id_or_forgeborn_name == forgeborn.name:
                    return forgeborn
        return None

class UniversalCardLibrary:
    def __init__(self, sff_path, fb_path, syn_path):        
        self.entities = []
        self.forgeborns = {}
        self.unique_forgeborns = {}
        self.fb_map = self._read_forgeborns_from_csv(fb_path)
        self._read_entities_from_csv(sff_path)

    def _read_forgeborns_from_csv(self, fb_path):
        fb_map = {}
        with open(fb_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                forgeborn_ability_id = row['forgebornID']
                card_id = row['cardId']
                forgeborn_id = forgeborn_ability_id[:-5]
                if forgeborn_id not in self.unique_forgeborns:
                    forgeborn_name = forgeborn_id[5:].capitalize()
                    self.unique_forgeborns[forgeborn_id] = Forgeborn(forgeborn_id, forgeborn_name)
                if card_id not in fb_map:
                    fb_map[card_id] = []
                fb_map[card_id].append(forgeborn_ability_id)
        return fb_map                

    def _read_entities_from_csv(self, csv_path):
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                self._process_row(row)

    def _process_row(self, row):
        keys = ['Name', 'rarity', 'cardType', 'cardSubType', 'spliced', 'solbind']
        attributes = {k: row[k] for k in keys if k in row}
        name = row['Name']
        faction = row['faction']
        abilities = {}

        for key in row.keys():
            if key.endswith('text'):
                level = int(key[0])
                attack = int(row[f"{level}attack"]) if row.get(f"{level}attack") else 0
                health = int(row[f"{level}health"]) if row.get(f"{level}health") else 0
                abilities[level] = {
                    'text': row[key],
                    'attack': attack,
                    'health': health
                }

        Collection = InterfaceCollection(name)

        read_synergies = False
        for key, value in row.items():
            if key == "3text":
                read_synergies = True
            elif read_synergies:
                range = None  
                if value is not None:
                    if not value.isnumeric():
                        if key == "Free":
                            key = f"Free {value}"
                            value = 1
                        else:
                            range = value
                            if value == '*':
                                value = 1
                            elif value == '+':
                                value = 1
                            elif value == '.':
                                value = 0
                            else:
                                range = ''
                                value = 0

                    if int(value) > 0:
                        ISyn = Interface(name, key=key, value=value, range=range)
                        Collection.add(ISyn)

        is_forgeborn_ability = attributes['cardType'] == 'forgeborn-ability'
        
        entity = Entity(name if not is_forgeborn_ability else row['id'], faction, attributes, abilities, Collection)
        self.entities.append(entity)

        if is_forgeborn_ability:
            ability = ForgebornAbility(row['id'], name, entity)
            self._process_forgeborn_ability(ability)

    def _process_forgeborn_ability(self, ability):
        forgeborn_ability_ids = self.fb_map.get(ability.id, [])
        for forgeborn_ability_id in forgeborn_ability_ids:
            forgeborn_id = forgeborn_ability_id[:-5]
            if forgeborn_id in self.unique_forgeborns:
                ability.id = forgeborn_ability_id
                self.unique_forgeborns[forgeborn_id].add_ability(ability)

    def search_entity(self, name, cardType=None):
        for entity in self.entities:
            if cardType is None or entity.attributes['cardType'] == cardType:
                if entity.name == name:
                    return entity
        return None

    def get_forgeborn(self, id):
        if id in self.forgeborns:
            return self.forgeborns[id]
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
                forgeborn_id = deck_data.get('forgebornId') or deck_data['forgeborn']['id']
                forgeborn_id = forgeborn_id.replace('0', '2')
                forgeborn_key = [key for key in self.unique_forgeborns if forgeborn_id[:-3] in key]
                forgeborn_unique = self.unique_forgeborns[forgeborn_key[0]]
                forgeborn = forgeborn_unique.get_permutation(forgeborn_id)
            except Exception as e:
                print(f"Exception: {e}")
                print(f"Could not load Forgeborn data: {deck_data['name'] if 'name' in deck_data else 'unknown'}")
                incomplete_data.append(deck_data)
                continue

            try: 
                cards_data = deck_data['cards']
                cards_title = []
                cards_additional_data = {}

                if isinstance(cards_data, dict):
                    for card in cards_data.values():
                        card_title = str(card.get('title')) if 'title' in card else str(card.get('name'))
                        cards_title.append(card_title)
                else:
                    cards_title = cards_data

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
        card_entity = self.search_entity(card_title)        
        if card_entity:
            for key, value in card_data_additional.items():                
                setattr(card_entity, key, value)
            return Card(card_entity)

        parts = card_title.split(' ')
        for i in range(1, len(parts)):
            modifier_title = ' '.join(parts[:i])
            card_title = ' '.join(parts[i:])
            modifier_entity = self.search_entity(modifier_title, 'Modifier')
            card_entity = self.search_entity(card_title)
            if modifier_entity and card_entity:
                for key, value in card_data_additional.items():
                    existing_value = getattr(card_entity, key)
                    if isinstance(existing_value, dict):
                        merged_value = {**existing_value, **value}
                        setattr(card_entity, key, merged_value)
                    elif value:
                        setattr(card_entity, key, value)
                return Card(card_entity, modifier_entity)

        print(f"Entity not found: {card_title}")
        return Card(Entity(name=card_title, cardType='Unknown'))

    def __str__(self):
        entity_strings = []
        for entity in self.entities:
            entity_strings.append(str(entity))
        return "\n".join(entity_strings)
