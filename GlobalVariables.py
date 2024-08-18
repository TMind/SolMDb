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
        self.all_column_definitions = all_column_definitions
        print("Global Variables Initialized")
        print(f"Username: {self._username}")

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
all_column_definitions = {
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
    'Creatures':        {'width': 80},
    'Spells':           {'width': 80},
    'Exalts':           {'width': 80},   
    'Beast':            {'width': 80},
    'Beast Synergy':    {'width': default_width},
    'Beast Combo':      {'width': default_width},
    'Dinosaur':         {'width': 80},
    'Dinosaur Synergy': {'width': default_width},
    'Dinosaur Combo':   {'width': default_width},
    'Mage':             {'width': 80},
    'Mage Synergy':     {'width': default_width},
    'Mage Combo':       {'width': default_width},
    'Robot':            {'width': 80},
    'Robot Synergy':    {'width': default_width},
    'Robot Type':       {'width': default_width},
    'Robot Combo':      {'width': default_width},
    'Scientist':        {'width': 80},
    'Scientist Synergy': {'width': default_width},
    'Scientist Combo':  {'width': default_width},
    'Spirit':           {'width': 80},
    'Spirit Synergy':   {'width': default_width},
    'Spirit Type' :     {'width': default_width},
    'Spirit Combo':     {'width': default_width},
    'Warrior':          {'width': 80},
    'Warrior Synergy':  {'width': default_width},
    'Warrior Combo':    {'width': default_width},
    'Zombie':           {'width': 80},
    'Zombie Synergy':   {'width': default_width},
    'Zombie Type':      {'width': default_width},
    'Zombie Combo':     {'width': default_width},
    'Replace Setup':    {'width': default_width},
    'Replace Profit':   {'width': default_width},
    'Replace Combo':    {'width': default_width},
    'Minion':           {'width': 80},
    'Minion Synergy':   {'width': default_width},
    'Minion Combo':     {'width': default_width},
    'Spell':            {'width': 80},
    'Spell Synergy':    {'width': default_width},
    'Spell Combo':      {'width': default_width},
    'Healing Source':   {'width': default_width},
    'Healing Synergy':  {'width': default_width},
    'Healing Combo':    {'width': default_width},
    'Movement':         {'width': 80},
    'Disruption':       {'width': 80},
    'Movement Benefit': {'width': default_width},
    'Movement Combo':   {'width': default_width},
    'Armor':            {'width': 80},
    'Armor Giver':      {'width': default_width},
    'Armor Synergy':    {'width': default_width},
    'Armor Combo':      {'width': default_width},
    'Activate':         {'width': 80},
    'Ready':            {'width': 80},
    'Activate Combo':   {'width': default_width},
    'Free':             {'width': 80},
    'Upgrade':          {'width': 80},
    'Upgrade Synergy':  {'width': default_width},
    'Upgrade Combo':    {'width': default_width},
    'Face Burn':        {'width': 80},
    'Removal':          {'width': 80},
    'Breakthrough':     {'width': default_width},
    'Breakthrough Giver':{'width': default_width},
    'Aggressive':       {'width': 80},
    'Aggressive Giver': {'width': default_width},
    'Defender':         {'width': 80},
    'Defender Giver':   {'width': default_width},
    'Stealth':          {'width': 80},
    'Stealth Giver':    {'width': default_width},
    'Stat Buff':        {'width': default_width},
    'Attack Buff':      {'width': default_width},
    'Health Buff':      {'width': default_width},
    'Stat Debuff':      {'width': default_width},
    'Attack Debuff':    {'width': default_width},
    'Health Debuff':    {'width': default_width},
    'Destruction Synergy':{'width': default_width},
    'Destruction Activator':{'width': default_width},
    'Destruction Combo': {'width': default_width},
    'Self Damage Payoff':{'width': default_width},
    'Self Damage Activator':{'width': default_width},
    'Self Damage Combo': {'width': default_width},
    'Silence':          {'width': 80},
    'White Fang':       {'width': 80},
    'Dragon':           {'width': 80},
    'Dragon Synergy':   {'width': default_width},
    'Dargon Combo':     {'width': default_width},
    'Elemental':        {'width': 80},
    'Elemental Synergy':{'width': default_width},
    'Elemental Type':   {'width': default_width},
    'Elemental Combo':  {'width': default_width},
    'Plant':            {'width': 80},
    'Plant Synergy':    {'width': default_width},
    'Plant Combo':      {'width': default_width},
    'Exalts':           {'width': 80},
    'Exalt Synergy':    {'width': default_width},
    'Exalt Combo':      {'width': default_width},
    'Slay':             {'width': 80},
    'Deploy':           {'width': 80},
    'Ready Combo' :     {'width': 80},
    'Deploy Combo' :    {'width': 80},
    'Reanimate' :       {'width': 80},
    'Reanimate Activator' : {'width': 80},
    'Reanimate Combo' : {'width': 80},
    'Last Winter':      {'width': default_width},
    'Spicy':            {'width': 80},
    'Cool':             {'width': 80},
    'Fun':              {'width': 80},
    'Annoying':         {'width': 80}
}


# Initialize global_vars
global_vars = GlobalVariables()