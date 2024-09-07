import ipywidgets as widgets
from IPython.display import display
from gridfs import GridFS
import os

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
    
    #apply_custom_css_for_specific_qgrid(self.rotated_column_definitions.keys(), header_height=150)
    #apply_custom_css_for_headerCss(header_height=150)
    apply_CustomCss_to_ClassHeader('.qgrid-custom-css', rotate_suffix , header_height=150)    

  def _initialize_objects(self):
    
    self.commonDB = self._initialize_commonDB()
    self.out_debug = widgets.Output()

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
          
          
from IPython.display import display, HTML

def apply_custom_css_for_specific_qgrid(column_names, column_width=10, header_height=80):
    style = f"""
    <style>
        .slick-header-column {{
            height: {header_height}px !important;
            text-align: left !important;
            vertical-align: bottom !important;
        }}

        .slick-header-column .slick-column-name {{
            display: inline-block !important;
            transform-origin: bottom left !important;
            white-space: nowrap !important;
            writing-mode: vertical-lr !important;
            text-orientation: mixed !important;
            margin-top: 20px !important;  /* Adding margin to the top */
        }}
    </style>

    <script>
        const columnNames = {column_names};

        document.querySelectorAll('.slick-header-column').forEach(function(col) {{
            const columnName = col.querySelector('.slick-column-name').innerText.trim();
            if (columnNames.includes(columnName)) {{
                col.style.width = '{column_width}px';
                col.querySelector('.slick-column-name').style.transform = 'rotate(90deg)';
            }} else {{
                col.style.width = ''; // Reset the width for non-target columns
                col.querySelector('.slick-column-name').style.transform = ''; // Reset the transform
            }}
        }});
    </script>
    """

    display(HTML(style))

def apply_custom_css_for_headerCss(column_width=10, header_height=80):
    style = f"""
    <style>
        .slick-header-column {{
            height: {header_height}px !important;
            text-align: left !important;
            vertical-align: bottom !important;
        }}

        ._rotate_ .slick-column-name {{
            display: inline-block !important;
            transform-origin: bottom left !important;
            white-space: nowrap !important;
            transform: rotate(90deg) !important;
            margin-top: 10px !important;  /* Adding margin to the top */
        }}
    </style>
    """

    display(HTML(style))

def apply_CustomCss_to_ClassHeader(class_name='', keyword = '', header_height=80):
    if keyword and not keyword.startswith('.'): keyword = f'.{keyword}'
    style = f"""
    <style>
        {class_name} .slick-header-column {{
            height: {header_height}px !important;
            text-align: left !important;
            vertical-align: bottom !important;
        }}

        {class_name} {keyword} .slick-column-name {{
            display: inline-block !important;
            transform-origin: bottom left !important;
            white-space: nowrap !important;
            transform: rotate(90deg) !important;
            margin-top: 10px !important;
        }}
    </style>
    """

    display(HTML(style))



default_width = 150
rotated_width = 10

rotate_suffix = '_rotate_'

rotated_column_definitions = {
    'Creatures':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spells':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Exalts':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Beast':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Beast Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Beast Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dinosaur':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dinosaur Synergy': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dinosaur Combo':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Mage':             {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Mage Synergy':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Mage Combo':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Robot':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Robot Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Robot Type':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Robot Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Scientist':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Scientist Synergy':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Scientist Combo':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spirit':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spirit Synergy':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spirit Type' :     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spirit Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Warrior':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Warrior Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Warrior Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Zombie':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Zombie Synergy':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Zombie Type':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Zombie Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Replace Setup':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Replace Profit':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Replace Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Minion':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Minion Synergy':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Minion Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spell':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spell Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spell Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Healing Source':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Healing Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Healing Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Movement':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Disruption':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Movement Benefit': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Movement Combo':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Armor':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Armor Giver':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Armor Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Armor Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Activate':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Ready':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Activate Combo':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Free':             {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Free Upgrade':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Upgrade':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Upgrade Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Upgrade Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Face Burn':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Removal':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Breakthrough':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Breakthrough Giver':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Aggressive':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Aggressive Giver': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Defender':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Defender Giver':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Stealth':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Stealth Giver':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Stat Buff':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Attack Buff':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Health Buff':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Stat Debuff':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Attack Debuff':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Health Debuff':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Destruction Synergy':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Destruction Activator':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Destruction Combo': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Self Damage Payoff':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Self Damage Activator':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Self Damage Combo': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Silence':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'White Fang':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dragon':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dragon Synergy':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dragon Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Elemental':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Elemental Synergy':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Elemental Type':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Elemental Combo':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Plant':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Plant Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Plant Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Exalts':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Exalt Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Exalt Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Slay':             {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Deploy':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Ready Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Deploy Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Reanimate':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Reanimate Activator': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Reanimate Combo':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Last Winter':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spicy':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Cool':             {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Fun':              {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Annoying':         {'width': rotated_width, 'headerCssClass': rotate_suffix}
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
    'deckScore':        {'width': 90},
    'deckRank':         {'width': 90},
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
    "level": True,  "xp": True, "elo": True, "deckScore": True, "deckRank": True,
    "cardSetNo": True,  "faction": True,
    "forgebornId": True, "cardheaderCssClasss": True,
    "Creatures": True,  "Spells": True,
    "FB2": True,    "FB3": True,    "FB4": True,
    "A1": True,     "A2": True,     "A3": True,
    "H1": True,     "H2": True,     "H3": True
  },
  "Fusion Stats": {
    "Name": True, "type": 'Fusion',
    "CreationDate": True, "UpdatedAt": True, 
    "faction": True, "crossfaction": True,
    "forgebornId": True, "cardheaderCssClasss": True,
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
    "cardheaderCssClasss": True,
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
    "cardheaderCssClasss": True,  
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
    'cardTitles': True,
    'faction': True,
    'cardType': True,
    'cardSubType': True,
  }
}

# Initialize global_vars
global_vars = GlobalVariables.get_instance()
global_vars._initialize_objects() 