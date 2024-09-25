from IPython.display import display, HTML, Javascript

from gsheets import GoogleSheetsClient

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

    def create_and_inject_css(self, class_name, column_selector='', header_height=140):
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
            .{class_name} .slick-header-column {{
                height: {header_height}px !important;
                text-align: left !important;
                vertical-align: bottom !important;
            }}
            
            /* Position the sort indicator at the bottom of the rotated column */
            .{class_name} .slick-header-column .slick-sort-indicator {{
                position: absolute !important;
                bottom: 10px !important; /* Position at the bottom */
                left: 50% !important; /* Center horizontally */
                transform: translateX(-100%) !important; /* Proper centering */
                display: inline-block !important;
                visibility: visible !important;
                font-size: 20px !important; /* Adjust size as needed */
                z-index: 2; /* Ensure it's above other elements */
                color: blue !important; /* Adjust color */
            }}
            
            .{class_name} {column_selector} .slick-column-name {{
                display: inline-block !important;
                transform-origin: bottom left !important;
                white-space: nowrap !important;
                transform: rotate(90deg) !important;
                margin-top: 10px !important;
            }}
        </style>
        """
        display(HTML(style))
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

    def needs_custom_styles(self, qgrid_widget, column_selector=''):
        """
        Checks if there are any columns in the qgrid widget that need a custom style.

        Parameters:
        - qgrid_widget: The qgrid widget to check.
        - column_selector: A CSS selector to target specific columns (e.g., by ID or class).

        Returns:
        - True if any columns have the column_selector, False otherwise.
        """
        found_matching_columns = False
        df = qgrid_widget.get_changed_df()
        
        for column in df.columns:
            column_definition = qgrid_widget.column_definitions.get(column, {})
            if 'headerCssClass' in column_definition and column_definition['headerCssClass'] == column_selector:
                found_matching_columns = True
                break

        return found_matching_columns

    def apply_column_styles(self, qgrid_widget, sorted_columns=[], filtered_columns=[]):
        """
        Apply custom CSS styles to columns that are sorted or filtered.
        """
        column_definitions = qgrid_widget.column_definitions

        # Apply CSS class for sorted columns
        for sort_col in sorted_columns:
            column_definitions[sort_col]['cssClass'] = 'sorted-column'

        # Apply CSS class for filtered columns
        for filter_col in filtered_columns:
            column_definitions[filter_col]['cssClass'] = 'filtered-column'

        return column_definitions
    
    def get_column_definitions_with_gradient(self, column_definitions, sorting_info):
        """
        Update the column definitions with custom CSS for sorted columns.
        Applies a vertical gradient to the header based on the sorting direction,
        and applies a static background color to the column cells that matches the header's gradient.
        """
        
        # CSS classes for ascending and descending sorts
        ascending_header_class = 'sorted-column-header-ascending'
        descending_header_class = 'sorted-column-header-descending'
        
        # Static cell color classes for ascending and descending sorts
        ascending_cell_class = 'sorted-column-cells-ascending'
        descending_cell_class = 'sorted-column-cells-descending'

        # Loop over each sorted column to apply or update the gradient in the header and static color in the cells
        for col_name, sort_info in sorting_info.items():
            if col_name in column_definitions:
                # Determine the new CSS class based on the current ascending state
                if sort_info['ascending']:
                    new_header_class = ascending_header_class
                    #new_cell_class = ascending_cell_class
                    old_header_class = descending_header_class
                    #old_cell_class = descending_cell_class
                else:
                    new_header_class = descending_header_class
                    #new_cell_class = descending_cell_class
                    old_header_class = ascending_header_class
                    #old_cell_class = ascending_cell_class

                # Get the current headerCssClass
                existing_header_class = column_definitions[col_name].get('headerCssClass', '')

                # Add the new header class for gradient and ensure no duplicates
                updated_header_class = add_css_class(existing_header_class, new_header_class)

                # Remove the old gradient class from the header
                updated_header_class = remove_css_class(updated_header_class, old_header_class)

                # Get the current cssClass (for cells)
                existing_cell_class = column_definitions[col_name].get('cssClass', '')

                # Apply static color to the cells in the sorted column
               # updated_cell_class = add_css_class(existing_cell_class, new_cell_class)

                # Apply general sorted column style if needed (optional for borders)
                #updated_cell_class = add_css_class(updated_cell_class, 'sorted-column')

                # Remove old cell color class to avoid duplication
                #updated_cell_class = remove_css_class(updated_cell_class, old_cell_class)

                print(f"Updated CSS for column {col_name}: Header = {updated_header_class}")                
                # Update the column definition with the new classes
                column_definitions[col_name]['headerCssClass'] = updated_header_class
                #column_definitions[col_name]['cssClass'] = updated_cell_class

        return column_definitions

# Global functions

def add_css_class(existing_class, new_class):
    """Helper function to append a CSS class without duplication."""
    classes = existing_class.split() if existing_class else []
    if new_class not in classes:
        classes.append(new_class)
    return " ".join(classes)

def remove_css_class(existing_class, old_class):
    """Helper function to remove a CSS class."""
    classes = existing_class.split() if existing_class else []
    if old_class in classes:
        classes.remove(old_class)
    return " ".join(classes)


# Global variables 

default_width = 150
rotated_width = 20

rotate_suffix = '_rotate_'

from gsheets import GoogleSheetsClient
cm_tags = GoogleSheetsClient().get_column_names_from('Card Database', 'Beast')

cm_tags_definitions = {tag: {'width': default_width} for tag in cm_tags}

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

rotated_column_definitions = {**cm_tags_definitions, **rotated_column_definitions}
 
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