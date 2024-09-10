import ipywidgets as widgets
from gridfs import GridFS
import os

from CustomCss import rotated_column_definitions, non_rotated_column_definitions

class GlobalVariables:
  
    _instance = None

    @classmethod  
    def get_instance(cls):  
        if cls._instance is None:  
            cls._instance = cls()  
        return cls._instance

    def __new__(cls,):
        if cls._instance is None:
            cls._instance = super(GlobalVariables, cls).__new__(cls)
            cls._instance._initialize_env()
        return cls._instance

    def _initialize_env(self):
        self._username = os.getenv('SFF_USERNAME', 'sff')
        self._host = os.getenv('HOST', 'localhost')
        self._port = os.getenv('MONGODB_PORT', 27017)
        self.uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        #self.uri = os.getenv('MONGODB_URI', "mongodb://tmind:c6tltLqSnbIyy4SAVsBwCiZWET9LA6USjk87IV3SO64jkKIuKXMBoe5Oeku4F2qHjXDldrgaNxypACDbE0WurA==@tmind.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb&maxIdleTimeMS=120000&appName=@tmind@")
        self.debug = os.getenv('DEBUG_MODE', 'False').lower() in ('true', '1', 't')
        
        self.myDB = None
        self.fs = None 
        self.commonDB = None
        self.progress_containers = {}
        self.out_debug = None
        self.rotated_column_definitions = rotated_column_definitions
        self.all_column_definitions = {**non_rotated_column_definitions, **rotated_column_definitions}
        self.data_selection_sets = data_selection_sets
        
        self._set_environment_variables()
        
        #apply_CustomCss_to_ClassHeader('.qgrid-custom-css', rotate_suffix , header_height=150)    
        #apply_CustomCss_to_ColumnHeader('.qgrid-custom-css', rotate_suffix , header_height=150)

    def _initialize_objects(self):
        
        self.commonDB = self._initialize_commonDB()
        self.out_debug = widgets.Output()
        self.progressbar_container = widgets.VBox([])  # Initially empty
        # If there are already progress containers, add them to the progressbar_container
        for identifier, container_dict in self.progress_containers.items():
            self.progressbar_container.children += (container_dict['container'],)  # Add to VBox
       
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

    def update_progress(self, identifier, value=None, total=None, message=None):
        container = self.get_or_create_progress_container(identifier)
        progress_bar = container['progress_bar']
        label = container['label']

        if message:
            label.value = message
        if total is not None:
            progress_bar.max = total
        if value is not None:
            progress_bar.value += value
            if value == 0:
                progress_bar.bar_style = 'info'
                progress_bar.style.bar_color = 'lightblue'
        else:
            progress_bar.value += 1  # Auto-increment if no value provided

        if progress_bar.value >= progress_bar.max:
            progress_bar.bar_style = 'success'
            progress_bar.style.bar_color = 'lightgreen'
            label.value = f"{message} -> Finished!"

data_selection_sets = {
  "Deck Stats": {
    "Name": True, "type": 'Deck',
    "registeredDate": True, "UpdatedAt": True, "pExpiry": True,
    "level": True,  "xp": True, "elo": True, "deckScore": True, "deckRank": True,
    "cardSetNo": True,  "faction": True,
    "forgebornId": True, "cardTitles": True,
    "Creatures": True,  "Spells": True,
    "FB2": True,    "FB3": True,    "FB4": True,
    "A1": True,     "A2": True,     "A3": True,
    "H1": True,     "H2": True,     "H3": True
  },
  "Fusion Stats": {
    "Name": True, "type": 'Fusion',
    "CreatedAt": True, "UpdatedAt": True, 
    "faction": True, "crossFaction": True,
    "forgebornId": True, "cardTitles": True,
    "FB2": True,    "FB3": True,    "FB4": True,
    "Creatures": True,  "Spells": True, "Exalts": True,    
    #"A1": True,     "A2": True,     "A3": True,
    #"H1": True,     "H2": True,     "H3": True
  },
  "Card Types": {
    "Name": True,
    "type": 'Deck',
    "faction": True,
    "Creatures": True,
    "Spells": True,
    "Exalts": True,
    "Beast": True,
    "Dinosaur": True,
    "Dragon": True,
    "Elemental Type": True,
    "Mage": True,
    "Plant Type": True,
    "Robot Type": True,
    "Scientist": True,
    "Spirit Type": True,
    "Warrior": True,
    "Zombie Type": True,
    "Minion": True,    
  },
  "Deck Tags": {
    "Name": True,
    "type": 'Deck',
    "faction": True,
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
    "Destruction Activator": True,
    "Self Damage Payoff": True,
    "Self Damage Activator": True,
    "Silence": True,
    "Exalt": True,
    "Exalt Synergy": True,
    "Slay": True,
    "Deploy": True,
    "White Fang": True,
    "Last Winter": True,
    "Spicy": True,
    "Cool": True,
    "Fun": True,
    "Annoying": True
  },
  "Deck Synergies": {
    "Name": True,
    "type": 'Deck',
    "faction": True,
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
    "Movement Benefit": True,
    "Armor": True,
    "Armor Giver": True,
    "Armor Synergy": True,
    "Activate": True,
    "Ready": True,
    "Upgrade": True,
    "Upgrade Synergy": True,
    "Destruction Activator": True,
    "Destruction Synergy": True,
    "Self Damage Activator": True,
    "Self Damage Payoff": True,
    "Exalt": True,
    "Exalt Synergy": True
  },
  "Fusion Tags": {
    "Name": True,
    "type": 'Fusion',
    "Deck A": True,
    "Deck B": True,
    "faction": True,
    "crossFaction": True,
    "forgebornId": True,
    "FB2": True,
    "FB3": True,
    "FB4": True,
    "cardTitles": True,
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
    "Destruction Activator": True,
    "Self Damage Payoff": True,
    "Self Damage Activator": True,
    "Silence": True,
    "Exalt": True,
    "Exalt Synergy": True,
    "Slay": True,
    "Deploy": True,
    "White Fang": True,
    "Last Winter": True,
    "Spicy": True,
    "Cool": True,
    "Fun": True,
    "Annoying": True
  },
  "Fusion Combos" :  {
    "Name": True,
    "type": 'Fusion',
    "Deck A": True,
    "Deck B": True,
    "faction": True,
    "crossFaction": True,
    "forgebornId": True,
    "FB2": True,
    "FB3": True,
    "FB4": True,
    "cardTitles": True,  
    'Beast Combo':      True,
    'Dinosaur Combo':   True,
    'Dragon Combo':     True,
    'Elemental Combo':  True,    
    'Mage Combo':       True,
    'Plant Combo':      True,
    'Robot Combo':      True,
    'Scientist Combo':  True,
    'Spirit Combo':     True,
    'Warrior Combo':    True,
    'Zombie Combo':     True,
    'Minion Combo':     True,
    'Exalt Combo':      True,    
    'Spell Combo':      True,
    'Deploy Combo' :    True,
    'Armor Combo':      True,
    'Activate Combo':   True,
    'Destruction Combo': True,
    'Healing Combo':    True,
    'Movement Combo':   True,
    'Replace Combo':    True,            
    'Ready Combo' :     True,    
    'Reanimate Combo' : True,
    'Self Damage Combo': True,    
    'Upgrade Combo':    True,    
  },
  'Deck Content': {
    'name': True,
    'faction': True,
    'cardType': True,
    'cardSubType': True,
  }
}

# Initialize global_vars
global_vars = GlobalVariables.get_instance()
global_vars._initialize_objects() 