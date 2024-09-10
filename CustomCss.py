from IPython.display import display, HTML, Javascript

# Function to inject CSS from a file
def inject_css(css_file_path):
    with open(css_file_path, 'r') as f:
        css = f.read()
    display(HTML(f"<style>{css}</style>"))

# Inject initial CSS file
inject_css('custom/custom.css')

class CSSManager:
    def __init__(self):
        self.css_classes = {}

    # TODO: Header height seems to be a problem since it messes up qgrids internal calculations on how many rows are actually displayed 
    def create_and_inject_css(self, class_name, column_selector='', header_height=120):
        """
        Creates and injects CSS for a specific class.

        Parameters:
        - class_name: A unique name for the CSS class.
        - column_selector: A CSS selector to target specific columns (e.g., by ID or class).
        - header_height: The height to apply to the headers (in pixels).

        Returns:
        - The name of the generated CSS class.
        """
        if column_selector and not column_selector.startswith('.'):
            column_selector = f'.{column_selector}'

        # Generate the CSS style as a string
        style = f"""
        <style>
            /* Set the header height for all columns */
            .{class_name} .slick-header-column {{
                height: {header_height}px !important;
                text-align: left !important;
                vertical-align: bottom !important;
            }}

            /* Apply the rotation to the specified columns (if column selector is provided) */
            .{class_name} {column_selector} .slick-column-name {{
                display: inline-block !important;
                transform-origin: bottom left !important;
                white-space: nowrap !important;
                transform: rotate(90deg) !important;
                margin-top: 10px !important;
            }}
        </style>
        """

        # Inject the custom CSS into the notebook
        display(HTML(style))
        
        # Store the CSS class name
        self.css_classes[class_name] = column_selector
        return class_name

    def apply_css_to_widget(self, widget, class_name):
        """
        Applies the CSS class to the qgrid widget.

        Parameters:
        - widget: The qgrid widget to apply the CSS class.
        - class_name: The CSS class name to apply.
        """
        if class_name in self.css_classes:
            widget.add_class(class_name)
        else:
            print(f"CSS class '{class_name}' does not exist.")

    def remove_class_from_widget(self, widget_id, class_name):
        js_code = f"""
        (function() {{
            var widget = document.getElementById('{widget_id}');
            if (widget) {{
                widget.classList.remove('{class_name}');
            }}
        }})();
        """
        display(Javascript(js_code))

    def needs_custom_styles(self, qgrid_widget, column_selector=''):
        """
        Checks if there are any columns in the qgrid widget that need a custom style.

        Parameters:
        - qgrid_widget: The qgrid widget to check.
        - column_selector: A CSS selector to target specific columns (e.g., by ID or class).

        Returns:
        - True if any columns has the column_selector, False otherwise.
        """
        found_matching_columns = False
        df = qgrid_widget.get_changed_df()
        
        for column in df.columns:
            column_definition = qgrid_widget.column_definitions.get(column, {})
            
            if 'headerCssClass' in column_definition and column_definition['headerCssClass'] == column_selector:
                found_matching_columns = True
                print(f"Found matching column selector {column_selector} for column {column}")
                break

        return found_matching_columns
    
# Global variables 

default_width = 150
rotated_width = 20

rotate_suffix = '_rotate_'

rotated_column_definitions = {
    # Creatures 
    'Creature':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Abomination':      {'width': rotated_width, 'headerCssClass': rotate_suffix},    
    'Beast':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Beast Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Beast Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dinosaur':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dinosaur Synergy': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dinosaur Combo':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dragon':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dragon Synergy':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Dragon Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Elemental':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Elemental Synergy':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Elemental Type':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Elemental Combo':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Mage':             {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Mage Synergy':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Mage Combo':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Plant':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Plant Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Plant Type':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Plant Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},    
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
    # Minion 
    'Minion':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Minion Synergy':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Minion Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Activate / Read / Deploy 
    'Activate':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Activate Combo':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Ready':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Ready Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Deploy':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Deploy Combo':     {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Damage 
    
    'Destruction Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Destruction Activator':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'SelfDestruction Activator':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Destruction Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Face Damage':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Face Damage Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Self Damage Payoff':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Self Damage Activator':{'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Self Damage Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Spell / Exalts
    'Exalts':           {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Exalt Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Exalt Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spell':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spell Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Spell Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    # Utility
    'Armor':            {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Armor Giver':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Armor Synergy':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Armor Combo':      {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
    'Disruption':       {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Healing Source':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Healing Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Healing Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Movement':         {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Movement Benefit': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Movement Combo':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Reanimate':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Reanimate Activator': {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Reanimate Combo':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Replace Setup':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Replace Profit':   {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Replace Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
   
    'Upgrade':          {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Upgrade Synergy':  {'width': rotated_width, 'headerCssClass': rotate_suffix},
    'Upgrade Combo':    {'width': rotated_width, 'headerCssClass': rotate_suffix},
    
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
    'Face Burn':        {'width': rotated_width, 'headerCssClass': rotate_suffix},
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
 
non_rotated_column_definitions = {
    'index':            {'width': 50},
    'Name':             {'width': 250},
    'DeckName':         {'width': 250},
    'type':             {'width': 60},
    'Deck A':           {'width': 250},
    'Deck B':           {'width': 250},
    'registeredDate':   {'width': 200},
    'CreatedAt' :    {'width': 200},
    'UpdatedAt':        {'width': 200},
    'xp':               {'width': 50},
    'elo':              {'width': 50},
    'level':            {'width': 50},
    'deckScore':        {'width': 90},
    'deckRank':         {'width': 90},
    'pExpiry':          {'width': 200},
    'cardSetNo':        {'width': 50},
    'faction':          {'width': 80},
    'crossFaction':     {'width': 100},
    'forgebornId':      {'width': 100},
    'cardTitles':       {'width': 200},
    'name':             {'width': 200}, 
    'cardType' :        {'width': 75},
    'cardSubType' :     {'width': 75},
    'FB4':              {'width': default_width},
    'FB2':              {'width': default_width},
    'FB3':              {'width': default_width},
    'Creatures':        {'width': default_width},
    'Spells':           {'width': default_width},
    'Exalt':            {'width': default_width},
    'A1':               {'width': 50},
    'H1':               {'width': 50},
    'A2':               {'width': 50},
    'H2':               {'width': 50},
    'A3':               {'width': 50},
    'H3':               {'width': 50},
    'graph':            {'width': 50},
    'node_data':        {'width': 50},
}