import ipywidgets as widgets
from gridfs import GridFS
import os
import logging
import pandas as pd

from CMManager import CMManager
from CustomCss import CSSManager
from GSheetsClient import GoogleSheetsClient

# Configure logging
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("app.log"),
                        logging.StreamHandler()
                    ])

# Suppress pymongo debug logs
logging.getLogger('pymongo').setLevel(logging.WARNING)

class GlobalVariables:
  
    _instance = None
    _initialized = False  # Flag to track initialization

    _universal_library_instance = None

    @classmethod  
    def get_instance(cls):  
        if cls._instance is None:  
            cls._instance = cls()  
        return cls._instance

    def __new__(cls,):
        if cls._instance is None:
            cls._instance = super(GlobalVariables, cls).__new__(cls)
            cls._instance._initialize_env()
            cls._instance._initialize_objects()
        return cls._instance

    def get_universal_library(self):
        if self._universal_library_instance is None:
            logging.info("Initializing UniversalLibrary.")
            from UniversalLibrary import UniversalLibrary  # Import here to avoid partial import
            self._universal_library_instance = UniversalLibrary(self._username, *self.ucl_paths)
        return self._universal_library_instance

    def reset_universal_library(self):
        from UniversalLibrary import UniversalLibrary  # Import here to avoid partial import
        self.commonDB.drop_collection('Entities')
        self.commonDB.drop_collection('Forgeborns')
        self._universal_library_instance = UniversalLibrary(self._username, *self.ucl_paths)
        

    def _initialize_env(self):
        logging.info("Initializing Environment.")
        self.current_date = pd.Timestamp.now().strftime('%Y-%m-%d')
        self._username = os.getenv('SFF_USERNAME', 'sff')
        self._host = os.getenv('HOST', 'localhost')
        self._port = os.getenv('MONGODB_PORT', 27017)
        self.uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')        
        self.debug = os.getenv('DEBUG_MODE', 'False').lower() in ('true', '1', 't')        
        self.sheet_url = os.getenv('SHEET_URL', 'https://docs.google.com/spreadsheets/d/17aYAWS5R1hg-8mxFEjQEcNlMZ9kocJhnDTjLU9anzw8')
        self.rotate_suffix = rotate_suffix
        
        self.myDB = None
        self.fs = None 
        self.ucl_paths = [ 'Card Database', os.path.join('csv', 'forgeborn.csv'), os.path.join('csv', 'synergies.csv')]
        self.commonDB = None
        self.progress_containers = {}
        self.out_debug = None        
        self.data_selection_sets = data_selection_sets               
        self._set_environment_variables()
        self.GoogleSheetsClient = None
        self.cm_manager = None
        self.rotated_column_definitions = rotated_column_defs
        self.non_rotated_column_definitions = non_rotated_column_defs
        self.all_column_definitions = {**self.rotated_column_definitions, **self.non_rotated_column_definitions}

    def _initialize_objects(self):
        if not self._initialized:
            logging.info("Initializing objects.")
            
            self.commonDB = self._initialize_commonDB()
            self.out_debug = widgets.Output()
            self.progressbar_container = widgets.VBox([])  # Initially empty
            # If there are already progress containers, add them to the progressbar_container
            for identifier, container_dict in self.progress_containers.items():
                self.progressbar_container.children += (container_dict['container'],)  # Add to VBox        
            
            self.css_manager = CSSManager()
            
            # Initialize CMManager for handling the CM sheet
            self.GoogleSheetsClient = GoogleSheetsClient()
            self.cm_manager = CMManager(self.commonDB, self.sheet_url, local_copy_path='csv/sff.csv', sheets_client=self.GoogleSheetsClient)
            self.update_all_column_definitions()
            if self.cm_manager.cm_tags :
                self.data_selection_sets['CM Tags'].update( {tag : True for tag in self.cm_manager.cm_tags} )
            self._initialized = True
        else:
            logging.info("Objects already initialized.")
        
    def update_all_column_definitions(self):
        """
        Update all_column_definitions by combining existing columns and new columns from the CM sheet.
        """
        try:
                    
            # Read the local CSV file to get the columns            
            cm_columns = self.cm_manager.cm_tags or [] # Get the CM sheet columns
            
            # Add the CM sheet columns to the rotated/non-rotated definitions
            cm_column_definitions = {col: {'width': rotated_width , 'headerCssClass' : rotate_suffix } for col in cm_columns}  # Adjust width as necessary
            
            # Combine with existing column definitions
            self.rotated_column_definitions = { **self.rotated_column_definitions, **cm_column_definitions } 
            self.all_column_definitions = {
                **self.rotated_column_definitions,
                **self.non_rotated_column_definitions,            
            }
            
            #print(f"Updated all_column_definitions: {self.all_column_definitions}")
        except Exception as e:
            print(f"Error updating column definitions: {e}")    
                   
    def _set_environment_variables(self):
        """Set environment variables based on the current values."""
        os.environ['SFF_USERNAME'] = self._username
        os.environ['HOST'] = self._host
        os.environ['MONGODB_PORT'] = str(self._port)
        os.environ['MONGODB_URI'] = self.uri
        os.environ['DEBUG_MODE'] = 'true' if self.debug else 'false'
        
    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        self._username = value
        os.environ['SFF_USERNAME'] = value
        if value == 'enterUsernameHere': return
        self.set_myDB()

    def set_myDB(self):
        from MongoDB.DatabaseManager import DatabaseManager
        # Logic to set myDB based on the new username
        self.myDB = DatabaseManager(self._username)
        self.fs = GridFS(self.myDB.mdb.db)  # Set GridFS for the user-specific DB

    def _initialize_commonDB(self):
        from MongoDB.DatabaseManager import DatabaseManager  # Lazy import
        return DatabaseManager('common')

    def get_or_create_progress_container(self, identifier, description=None):
        if identifier not in self.progress_containers:
            # Create a new IntProgress widget
            progress_bar = widgets.IntProgress(
                description=description or identifier,
                value=0, min=0, max=100,
                bar_style='info', style={'bar_color': 'lightblue', 'description_width': '150px'},
                layout=widgets.Layout(width='25%')  # Relative width
            )
            # Create a label widget
            label = widgets.Label(description, layout=widgets.Layout(width='auto'))
            # Create an HBox to hold both the label and the progress bar
            hbox = widgets.HBox([progress_bar, label])
            self.progress_containers[identifier] = {'container': hbox, 'progress_bar': progress_bar, 'label': label}
            # Display the new HBox
            #display(hbox)
            # Add the new progress bar container to the main progressbar container
            self.progressbar_container.children += (hbox,)  # Add the HBox to the VBox
        return self.progress_containers[identifier]

    def update_progress(self, identifier, value=None, total=None, set=False, message=None):
        container = self.get_or_create_progress_container(identifier)
        progress_bar = container['progress_bar']
        label = container['label']
        
        if total is not None:
            progress_bar.max = total
        if value is not None:
            if set : progress_bar.value = value
            else:    progress_bar.value += value
            if value == 0:
                progress_bar.bar_style = 'info'
                progress_bar.style.bar_color = 'lightblue'
        else:
            progress_bar.value += 1  # Auto-increment if no value provided
            
        if progress_bar.max and message:
            count = progress_bar.value
            total = progress_bar.max
            percentage_message = f"[{count: >5}/{total:<5}] "
            label.value = f"{percentage_message}{message}"

        if progress_bar.value >= progress_bar.max:
            progress_bar.bar_style = 'success'
            progress_bar.style.bar_color = 'lightgreen'
            percentage_message = f"[{progress_bar.max: >5}/{progress_bar.max:<5}] "
            label.value = f"{percentage_message}{message}!"
            
    def reset_progress(self, identifier):
        container = self.get_or_create_progress_container(identifier)
        progress_bar = container['progress_bar']
        label = container['label']
        progress_bar.value = 0
        progress_bar.bar_style = 'info'
        progress_bar.style.bar_color = 'lightblue'
        label.value = ''

# Global variables 

default_width = 150
rotated_width = 20

rotate_suffix = '_rotate_'

rotated_column_defs = {
    # Creatures 
    'Creature':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Abomination':      {'width': rotated_width, 'headerCssClass': rotate_suffix},    
    'Beast':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Beast Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'BEAST Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dinosaur':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dinosaur Synergy': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'DINOSAUR Combo':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dragon':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dragon Synergy':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'DRAGON Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Elemental':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Elemental Synergy':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Elemental Type':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'ELEMENTAL Combo':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Mage':             {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Mage Synergy':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'MAGE Combo':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Plant':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Plant Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Plant Type':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'PLANT Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},    
    'Robot':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Robot Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'BanishRobot':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'ROBOT Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Scientist':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Scientist Synergy':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'SCIENTIST Combo':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spirit':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spirit Synergy':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'BanishSpirit':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'BanishSpirit Synergy':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'SPIRIT Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'BANISH SPIRIT Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Warrior':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Warrior Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'WARRIOR Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Zombie':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Zombie Synergy':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Zombie Type':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'ZOMBIE Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    # Minion 
    'Minion':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Minion Synergy':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'MINION Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Activate / Ready / Deploy 
    'Activate':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'ACTIVATION Combo': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Ready':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'READY Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Deploy':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'DEPLOY Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Damage 
    
    'Destruction Others'   :{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Good Destroyed':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'DESTROYED Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Destruction Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Destruction Self'     :{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'DESTRUCTION Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},    
    'Face Burn':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'FB Creature':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'FB Creature Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'FACE DMG Combo':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Self Damage Payoff':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Self Damage Activator':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'SELFDAMAGE Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Spell / Exalts
    'Exalts':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Exalt Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'EXALT Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spell':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spell Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'SPELL Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Utility
    'Armor':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Armor Giver':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Armor Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'ARMOR Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    'Disruption':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Healing Source':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Healing Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'HEALING Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Movement':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Movement Benefit': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'MOVEMENT Combo':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Reanimate':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Reanimate Activator': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'REANIMATE Combo':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Replace Setup':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Replace Profit':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'REPLACE Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
   
    'Upgrade':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Upgrade Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'UPGRADE Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Free 
    'Free':             {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Free Attack Buff': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Free Healing Source':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Free Mage':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Free Spell':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Free Replace':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Free Self Damage': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Free SelfDestruction': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Free Upgrade':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Removal 
    'Removal':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Silence':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Keywords 
    'Aggressive':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Aggressive Giver': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Breakthrough':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Breakthrough Giver':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Defender':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Defender Giver':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Stealth':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Stealth Giver':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Stats
    'Stat Buff':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Attack Buff':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Health Buff':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Stat Debuff':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Attack Debuff':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Health Debuff':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Attack 
    'Increased A':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Increased A Synergy': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'INC ATTACK Combo': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Battle':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Battle Synergy' :  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Slay':             {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Sets
    'Last Winter':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'White Fang':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Other 
    'Spicy':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Cool':             {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Fun':              {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Annoying':         {'width': rotated_width, 'headerCssClass': rotate_suffix}
}
 
non_rotated_column_defs = {
    'index':            {'width': 50},
    'Name':             {'width': 250},
    'DeckName':         {'width': 250},
    'type':             {'width': 60},
    'Deck A':           {'width': 250},
    'Deck B':           {'width': 250},
    'id':               {'width': 200},
    'registeredDate':   {'width': 200},
    'CreatedAt' :    {'width': 200},
    'UpdatedAt':        {'width': 200},
    'xp':               {'width': 50},
    'elo':              {'width': 50},
    'level':            {'width': 50},
    'deckScore':        {'width': 90},
    'deckRank':         {'width': 90},
    'pExpiry':          {'width': 200},
    'digital':          {'width': 50},
    'cardSetNo':        {'width': 50},
    'faction':          {'width': 80},
    'crossFaction':     {'width': 100},
    'forgebornId':      {'width': 100},
    'cardTitles':       {'width': 200},
    'Betrayers':        {'width': 200},
    'SolBinds':         {'width': 200},
    'nft':              {'width': 50},
    'price':            {'width': 50},
    'owner':            {'width': 200},
    'name':             {'width': 200}, 
    'cardType' :        {'width': 75},
    'cardSubType' :     {'width': 75},
    'FB4':              {'width': default_width},
    'FB2':              {'width': default_width},
    'FB3':              {'width': default_width},
    'Creatures':        {'width': 75},
    'Spells':           {'width': 75},
    'Exalt':            {'width': 75},
    'Sum':              {'width': 50},
    'A1':               {'width': 50},
    'H1':               {'width': 50},
    'A2':               {'width': 50},
    'H2':               {'width': 50},
    'A3':               {'width': 50},
    'H3':               {'width': 50},
    'graph':            {'width': 50},
    'node_data':        {'width': 50},
}

tag_selection_set = {
    
    "Tags": {
        "Sum":  True,
        "Beast": True,        
        "Dinosaur": True,        
        "Mage": True,        
        "Robot": True,
        "Scientist": True,
        "Spirit": True,        
        "Warrior": True,        
        "Zombie": True,        
        "Dragon": True,
        "Elemental": True,        
        "Plant": True,        
        "Replace Setup": True,
        "Minion": True,        
        "Spell": True,        
        "Healing Source": True,
        "Movement": True,
        "Disruption": True,
        "Movement Benefit": True,
        "Armor": True,
        "Armor Giver": True,
        "Armor Synergy": True,
        "Activate": True,
        "Ready": True,
        "Free": True,
        "Upgrade": True,
        "Upgrade Synergy": True,
        "Face Burn": True,
        "Removal": True,
        "Breakthrough": True,
        "Breakthrough Giver": True,
        "Aggressive": True,
        "Aggressive Giver": True,
        "Defender": True,
        "Defender Giver": True,
        "Stealth": True,
        "Stealth Giver": True,
        "Stat Buff": True,
        "Attack Buff": True,
        "Health Buff": True,
        "Stat Debuff": True,
        "Attack Debuff": True,
        "Health Debuff": True,
        "Destruction Synergy": True,
        "Destruction Self": True,
        "Destruction Others": True,
        "Self Damage Payoff": True,
        "Self Damage Activator": True,
        "Silence": True,
        "Exalt": True,
        "Exalt Synergy": True,
        "Slay": True,
        "Deploy": True,
    },    
    "Combos": {
        "Sum": True,
        "Free": True,
        'BEAST Combo':      True,
        'DINOSAUR Combo':   True,
        'DRAGON Combo':     True,
        'ELEMENTAL Combo':  True,    
        'MAGE Combo':       True,
        'PLANT Combo':      True,
        'ROBOT Combo':      True,
        'SCIENTIST Combo':  True,
        'SPIRIT Combo':     True,
        'BANISH SPIRIT Combo':     True,
        'WARRIOR Combo':    True,
        'ZOMBIE Combo':     True,
        'MINION Combo':     True,
        'EXALT Combo':      True,    
        'SPELL Combo':      True,
        'DEPLOY Combo' :    True,
        'ARMOR Combo':      True,
        'ACTIVATE Combo':   True,
        'DESTRUCTION Combo': True,
        'DESTROY Combo': True,
        'HEALING Combo':    True,
        'MOVEMENT Combo':   True,
        'REPLACE Combo':    True,            
        'READY Combo' :     True,    
        'REANIMATE Combo' : True,
        'SELFDAMAGE Combo': True,    
        'UPGRADE Combo':    True,    
        'INCREASED A Combo': True,
    },        
    
}


data_selection_sets = { 

  "Stats": {
    "A1": True,     "A2": True,     "A3": True,
    "H1": True,     "H2": True,     "H3": True
  },
   "Tags": {
    "Sum":  True,
    "Beast": True,
    "Beast Synergy": True,
    "Dinosaur": True,
    "Dinosaur Synergy": True,
    "Mage": True,
    "Mage Synergy": True,
    "Robot": True,
    "Robot Synergy": True,
    "Scientist": True,
    "Scientist Synergy": True,
    "Spirit": True,
    "Spirit Synergy": True,
    "Warrior": True,
    "Warrior Synergy": True,
    "Zombie": True,
    "Zombie Synergy": True,
    "Dragon": True,
    "Dragon Synergy": True,
    "Elemental": True,
    "Elemental Synergy": True,
    "Plant": True,
    "Plant Synergy": True,
    "Replace Setup": True,
    "Replace Profit": True,
    "Minion": True,
    "Minion Synergy": True,
    "Spell": True,
    "Spell Synergy": True,
    "Healing Source": True,
    "Healing Synergy": True,
    "Movement": True,
    "Disruption": True,
    "Movement Benefit": True,
    "Armor": True,
    "Armor Giver": True,
    "Armor Synergy": True,
    "Activate": True,
    "Ready": True,
    "Free": True,
    "Upgrade": True,
    "Upgrade Synergy": True,
    "Destruction Self": True,
    "Destruction Others": True,
    "Good Destroyed": True,
    "Destruction Snyergy": True,
    "Face Burn": True,
    "FB Creature": True,
    "FB Creature Synergy": True,
    "Removal": True,
    "Breakthrough": True,
    "Breakthrough Giver": True,
    "Aggressive": True,
    "Aggressive Giver": True,
    "Defender": True,
    "Defender Giver": True,
    "Stealth": True,
    "Stealth Giver": True,
    "Stat Buff": True,
    "Attack Buff": True,
    "Health Buff": True,
    "Stat Debuff": True,
    "Attack Debuff": True,
    "Health Debuff": True,
    "Self Damage Payoff": True,
    "Self Damage Activator": True,
    "Silence": True,
    "Exalt": True,
    "Exalt Synergy": True,
    "Slay": True,
    "Deploy": True,
    "Spicy": True,
    "Cool": True,
    "Fun": True,
    "Annoying": True
  },
  "Combos" :  {
    "Sum": True,
    "Free": True,
    'BEAST Combo':      True,
    'DINOSAUR Combo':   True,
    'DRAGON Combo':     True,
    'ELEMENTAL Combo':  True,    
    'MAGE Combo':       True,
    'PLANT Combo':      True,
    'ROBOT Combo':      True,
    'SCIENTIST Combo':  True,
    'SPIRIT Combo':     True,
    'BANISH SPIRIT Combo': True,
    'WARRIOR Combo':    True,
    'ZOMBIE Combo':     True,
    'MINION Combo':     True,
    'EXALT Combo':      True,    
    'SPELL Combo':      True,
    'DEPLOY Combo' :    True,
    'ARMOR Combo':      True,
    'ACTIVATE Combo':   True,
    'DESTRUCTION Combo': True,
    'DESTROY Combo': True,
    'HEALING Combo':    True,
    'MOVEMENT Combo':   True,
    'REPLACE Combo':    True,            
    'READY Combo' :     True,    
    'REANIMATE Combo' : True,
    'SELFDAMAGE Combo': True,    
    'UPGRADE Combo':    True,    
    'INCREASED A Combo': True,
  },
  'Deck Content': {
    'name': True,
    'faction': True,
    'rarity': True,
    'cardType': True,
    'cardSubType': True,
  },
  'CM Tags': {
    'Name': True,
    'faction': True,
    'FB2': True,
    'FB3': True,
    'FB4': True,
  },
  'Listing': {
    "Name": True, "name": True, "type": 'Deck', "id" : True,
    "price": True, "owner": True, "registeredDate": True, "pExpiry": True, 
    "deckScore": True, "deckRank": True,
    "cardSetNo": True,  "faction": True,
    "forgebornId": True, "cardTitles": True, "Betrayers": True, "SolBinds": True,
    "FB2": True,    "FB3": True,    "FB4": True,
    "Creatures": True,  "Spells": True, "Exalt": True,    
    "A1": True,     "A2": True,     "A3": True,
    "H1": True,     "H2": True,     "H3": True    
  }
}


GLOBAL_COLUMN_ORDER = [
    'index', 'type', 'Name', 'name', 'DeckName', 'Deck A', 'Deck B','id',
    'registeredDate', 'pExpiry', 'CreatedAt', 'UpdatedAt', 'digital', 'tags', 'nft', 'price', 'owner',
    'xp', 'elo', 'level', 'deckScore', 'deckRank', 'rarity',
    'cardSetNo', 'faction', 'crossFaction', 'cardTitles', 
    'cardType', 'cardSubType', 'forgebornId', 'FB2', 'FB3', 'FB4', 'Betrayers', 'SolBinds',
    'Spells', 'Exalt', 
    'A1', 'H1', 'A2', 'H2', 'A3', 'H3', 
    'Sum', 'Free',
    
    # Creatures
    'Abomination', 
    'Beast'         ,'Beast Synergy'        ,'BEAST Combo'                                                                  , 
    'Dinosaur'      ,'Dinosaur Synergy'     ,'DINOSAUR Combo'                                                               ,             
    'Dragon'        ,'Dragon Synergy'       ,'DRAGON Combo'                                                                 ,             
    'Elemental'     ,'Elemental Type'       ,'Elemental Synergy', 'ELEMENTAL Combo'                                         , 
    'Mage'          ,'Mage Synergy'         ,'MAGE Combo'                                                                   ,          
    'Ooze'                                                                                                                  ,     
    'Plant'         ,'Plant Synergy'        ,'BanishPlant'      ,'PLANT Combo'                                              ,     
    'Robot'         ,'BanishRobot'          ,'BanishRobot Synergy'                  ,'Robot Synergy'    ,'ROBOT Combo'      ,
    'Scientist'     ,'Scientist Synergy'    ,'SCIENTIST Combo'                                                              ,     
    'Spirit'        ,'Spirit Synergy'       ,'SPIRIT Combo'                                                                 ,       
    'BanishSpirit'  ,'BanishSpirit Synergy' ,'BANISH SPIRIT Combo'                                                          ,     
    'Vampire'                                                                                                               ,                                                                    
    'Warrior'       ,'Warrior Synergy'      ,'WARRIOR Combo'                                                                ,      
    'Zombie'        ,'Zombie Synergy'       ,'Zombie Type'      ,'ZOMBIE Combo'                                             ,                
    
    # Minion
    'Minion', 'Minion Synergy', 'MINION Combo',
    
    # Activate / Ready / Deploy 
    'Activate', 'ACTIVATION Combo', 
    'Ready', 'READY Combo',
    'Deploy', 'Deploy Synergy', 'DEPLOY Combo',
    
    # Damage 
    'Destruction Self'      ,'Destruction Synergy'      ,'DESTRUCTION Combo'        ,
    'Destruction Others'    ,'Good Destroyed'           ,'DESTROYED Combo'          ,
    'Self Damage Activator' ,'Self Damage Payoff'       ,'SELFDAMAGE Combo'         ,
    
    # Exalts / Spells
    'Exalts'                ,'Exalt Synergy'            ,'EXALT Combo'              , 'Exalt Counter',
    'Spell'                 ,'Spell Synergy'            ,'SPELL Combo'              , 
    
    # Utility
    'Armor', 'Armor Giver', 'Armor Synergy', 'ARMOR Combo',     
    'Healing Source', 'Healing Synergy', 'HEALING Combo', 
    'Movement', 'Movement Benefit', 'MOVEMENT Combo', 
    'Reanimate', 'Reanimate Activator', 'REANIMATE Combo',
    'Replace Setup', 'Replace Profit', 'REPLACE Combo', 
    'Upgrade', 'Upgrade Synergy', 'UPGRADE Combo', 
    
    # Free
    'Free Attack Buff', 'Free Healing Source', 'Free Mage', 'Free Spell', 'Free Replace', 'Free Self Damage', 'Free SelfDestruction', 'Free Upgrade',
    
    # Removal    
    'Face Burn', 'FB Creature', 'FB Creature Synergy', 'FACE DMG Combo',
    'Disruption', 'Removal', 'Silence', 
    
    # Keywords
    'Aggressive', 'Aggressive Giver',
    'Breakthrough', 'Breakthrough Giver', 
    'Defender', 'Defender Giver',
    'Stealth', 'Stealth Giver',
    
    # Stats
    'Increased A', 'Increased A Synergy', 'INC ATTACK Combo',
    
    
    'Stat Buff', 'Attack Buff', 'Health Buff',
    'Stat Debuff', 'Attack Debuff', 'Health Debuff',
    
    # Battle
    'Battle', 'Battle Synergy', 
    'Slay', 
    
    # Miscellaneous    
    'Last Winter', 'White Fang',
    'Spicy', 'Cool', 'Fun', 'Annoying'
]



# Initialize global_vars
global_vars = GlobalVariables.get_instance()