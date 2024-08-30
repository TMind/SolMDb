import ipywidgets as widgets
from IPython.display import display
from gridfs import GridFS

class GlobalVariables:
    def __init__(self):
        self._username = 'sff'
        self.uri = "mongodb://localhost:27017"
        self.myDB = None
        self.fs = None 
        self.commonDB = self._initialize_commonDB()
        self.progress_containers = {}
        self.out_debug = widgets.Output()
        self.debug = False
        self.rotated_column_definitions = rotated_column_definitions
        self.all_column_definitions = { **non_rotated_column_definitions, **rotated_column_definitions }
        self.data_selection_sets = data_selection_sets
        #print("Global Variables Initialized")
        #print(f"Username: {self._username}")

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        self._username = value
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
            display(hbox)
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

default_width = 150
rotated_width = 10

rotated_column_definitions = {
     'Creatures':        {'width': rotated_width},
    'Spells':           {'width': rotated_width},
    'Exalts':           {'width': rotated_width},   
    'Beast':            {'width': rotated_width},
    'Beast Synergy':    {'width': rotated_width},
    'Beast Combo':      {'width': rotated_width},
    'Dinosaur':         {'width': rotated_width},
    'Dinosaur Synergy': {'width': rotated_width},
    'Dinosaur Combo':   {'width': rotated_width},
    'Mage':             {'width': rotated_width},
    'Mage Synergy':     {'width': rotated_width},
    'Mage Combo':       {'width': rotated_width},
    'Robot':            {'width': rotated_width},
    'Robot Synergy':    {'width': rotated_width},
    'Robot Type':       {'width': rotated_width},
    'Robot Combo':      {'width': rotated_width},
    'Scientist':        {'width': rotated_width},
    'Scientist Synergy': {'width': rotated_width},
    'Scientist Combo':  {'width': rotated_width},
    'Spirit':           {'width': rotated_width},
    'Spirit Synergy':   {'width': rotated_width},
    'Spirit Type' :     {'width': rotated_width},
    'Spirit Combo':     {'width': rotated_width},
    'Warrior':          {'width': rotated_width},
    'Warrior Synergy':  {'width': rotated_width},
    'Warrior Combo':    {'width': rotated_width},
    'Zombie':           {'width': rotated_width},
    'Zombie Synergy':   {'width': rotated_width},
    'Zombie Type':      {'width': rotated_width},
    'Zombie Combo':     {'width': rotated_width},
    'Replace Setup':    {'width': rotated_width},
    'Replace Profit':   {'width': rotated_width},
    'Replace Combo':    {'width': rotated_width},
    'Minion':           {'width': rotated_width},
    'Minion Synergy':   {'width': rotated_width},
    'Minion Combo':     {'width': rotated_width},
    'Spell':            {'width': rotated_width},
    'Spell Synergy':    {'width': rotated_width},
    'Spell Combo':      {'width': rotated_width},
    'Healing Source':   {'width': rotated_width},
    'Healing Synergy':  {'width': rotated_width},
    'Healing Combo':    {'width': rotated_width},
    'Movement':         {'width': rotated_width},
    'Disruption':       {'width': rotated_width},
    'Movement Benefit': {'width': rotated_width},
    'Movement Combo':   {'width': rotated_width},
    'Armor':            {'width': rotated_width},
    'Armor Giver':      {'width': rotated_width},
    'Armor Synergy':    {'width': rotated_width},
    'Armor Combo':      {'width': rotated_width},
    'Activate':         {'width': rotated_width},
    'Ready':            {'width': rotated_width},
    'Activate Combo':   {'width': rotated_width},
    'Free':             {'width': rotated_width},
    'Free Upgrade':     {'width': rotated_width},
    'Upgrade':          {'width': rotated_width},
    'Upgrade Synergy':  {'width': rotated_width},
    'Upgrade Combo':    {'width': rotated_width},
    'Face Burn':        {'width': rotated_width},
    'Removal':          {'width': rotated_width},
    'Breakthrough':     {'width': rotated_width},
    'Breakthrough Giver':{'width': rotated_width},
    'Aggressive':       {'width': rotated_width},
    'Aggressive Giver': {'width': rotated_width},
    'Defender':         {'width': rotated_width},
    'Defender Giver':   {'width': rotated_width},
    'Stealth':          {'width': rotated_width},
    'Stealth Giver':    {'width': rotated_width},
    'Stat Buff':        {'width': rotated_width},
    'Attack Buff':      {'width': rotated_width},
    'Health Buff':      {'width': rotated_width},
    'Stat Debuff':      {'width': rotated_width},
    'Attack Debuff':    {'width': rotated_width},
    'Health Debuff':    {'width': rotated_width},
    'Destruction Synergy':{'width': rotated_width},
    'Destruction Activator':{'width': rotated_width},
    'Destruction Combo': {'width': rotated_width},
    'Self Damage Payoff':{'width': rotated_width},
    'Self Damage Activator':{'width': rotated_width},
    'Self Damage Combo': {'width': rotated_width},
    'Silence':          {'width': rotated_width},
    'White Fang':       {'width': rotated_width},
    'Dragon':           {'width': rotated_width},
    'Dragon Synergy':   {'width': rotated_width},
    'Dargon Combo':     {'width': rotated_width},
    'Elemental':        {'width': rotated_width},
    'Elemental Synergy':{'width': rotated_width},
    'Elemental Type':   {'width': rotated_width},
    'Elemental Combo':  {'width': rotated_width},
    'Plant':            {'width': rotated_width},
    'Plant Synergy':    {'width': rotated_width},
    'Plant Combo':      {'width': rotated_width},
    'Exalts':           {'width': rotated_width},
    'Exalt Synergy':    {'width': rotated_width},
    'Exalt Combo':      {'width': rotated_width},
    'Slay':             {'width': rotated_width},
    'Deploy':           {'width': rotated_width},
    'Ready Combo' :     {'width': rotated_width},
    'Deploy Combo' :    {'width': rotated_width},
    'Reanimate' :       {'width': rotated_width},
    'Reanimate Activator' : {'width': rotated_width},
    'Reanimate Combo' : {'width': rotated_width},
    'Last Winter':      {'width': rotated_width},
    'Spicy':            {'width': rotated_width},
    'Cool':             {'width': rotated_width},
    'Fun':              {'width': rotated_width},
    'Annoying':         {'width': rotated_width}
}

non_rotated_column_definitions = {
    'index':            {'width': 50},
    'Name':             {'width': 250},
    'type':             {'width': 60},
    'Deck A':           {'width': 250},
    'Deck B':           {'width': 250},
    'registeredDate':   {'width': 200},
    'UpdatedAt':        {'width': 200},
    'xp':               {'width': 50},
    'elo':              {'width': 50},
    'level':            {'width': 50},
    'pExpiry':          {'width': 200},
    'cardSetNo':        {'width': 50},
    'faction':          {'width': 100},
    'crossFaction':     {'width': 100},
    'forgebornId':      {'width': 100},
    'cardTitles':       {'width': 200},
    'FB4':              {'width': default_width},
    'FB2':              {'width': default_width},
    'FB3':              {'width': default_width},
    'A1':               {'width': 50},
    'H1':               {'width': 50},
    'A2':               {'width': 50},
    'H2':               {'width': 50},
    'A3':               {'width': 50},
    'H3':               {'width': 50},
}
  
data_selection_sets = {
  "Deck Stats": {
    "Name": True, "type": 'Deck',
    "registeredDate": True, "UpdatedAt": True, "pExpiry": True,
    "level": True,  "xp": True, "elo": True,
    "cardSetNo": True,  "faction": True,
    "forgebornId": True, "cardTitles": True,
    "Creatures": True,  "Spells": True,
    "FB2": True,    "FB3": True,    "FB4": True,
    "A1": True,     "A2": True,     "A3": True,
    "H1": True,     "H2": True,     "H3": True
  },
  "Fusion Stats": {
    "Name": True, "type": 'Fusion',
    "CreationDate": True, "UpdatedAt": True, 
    "faction": True, "crossfaction": True,
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
    "Dinosaur Type": True,
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
    "Exalts": True,
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
    "Exalts": True,
    "Exalt Synergy": True
  },
  "Fusion Tags": {
    "Name": True,
    "type": 'Fusion',
    "Deck A": True,
    "Deck B": True,
    "faction": True,
    "crossfaction": True,
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
    "Exalts": True,
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
    "crossfaction": True,
    "forgebornId": True,
    "FB2": True,
    "FB3": True,
    "FB4": True,
    "cardTitles": True,  
    'Beast Combo':      True,
    'Dinosaur Combo':   True,
    'Mage Combo':       True,
    'Robot Combo':      True,
    'Scientist Combo':  True,
    'Spirit Combo':     True,
    'Warrior Combo':    True,
    'Zombie Combo':     True,
    'Replace Combo':    True,
    'Minion Combo':     True,
    'Spell Combo':      True,
    'Healing Combo':    True,
    'Movement Combo':   True,
    'Armor Combo':      True,
    'Activate Combo':   True,
    'Upgrade Combo':    True,
    'Destruction Combo': True,
    'Self Damage Combo': True,
    'Dargon Combo':     True,
    'Elemental Combo':  True,
    'Plant Combo':      True,
    'Exalt Combo':      True,
    'Ready Combo' :     True,
    'Deploy Combo' :    True,
    'Reanimate Combo' : True,
  },
  'Deck Content': {
    'name': True,
    'CardTitle': True,
    'faction': True,
    'cardType': True,
    'cardSubType': True,
  }
}

# Initialize global_vars
global_vars = GlobalVariables()