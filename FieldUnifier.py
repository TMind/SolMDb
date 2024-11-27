from GlobalVariables import GLOBAL_COLUMN_ORDER

# Define fields that apply to all items (both Deck and Fusion)
BASIC_FIELDS = [
    'Name', 'faction', 'digital', 'cardSetNo', 'forgebornId', 'FB2', 'FB3', 'FB4',
    'Betrayers', 'SolBinds', 'Spells', 'Exalt'
]

# Define type-specific fields
TYPE_SPECIFIC_FIELDS = {
    'Deck': ['level', 'xp', 'elo', 'deckScore', 'deckRank', 'registeredDate', 'pExpiry'],
    'Fusion': ['crossFaction', 'Deck A', 'Deck B', 'CreatedAt']
}

# Define fields related to dates for all types
DATE_FIELDS = ['registeredDate', 'pExpiry', 'CreatedAt', 'UpdatedAt']

# Define other specific field groupings that we can use as building blocks
STATS_FIELDS = ['type', 'id', 'level', 'xp', 'elo', 'deckScore', 'deckRank', 'Deck A', 'Deck B', 'crossFaction']

AVERAGE_FIELDS = ['A1', 'H1', 'A2', 'H2', 'A3', 'H3']

TAGS = [
    'Beast', 'Dinosaur', 'Mage', 'Robot', 'Scientist', 'Spirit', 'Warrior', 'Zombie',
    'Dragon', 'Elemental', 'Plant', 'Minion', 'Spell', 'Healing Source', 'Movement', 'Disruption',
    'Replace Setup', 'Armor', 'Activate', 'Ready', 'Free', 'Upgrade', 'FB Creature', 'Removal', 'Breakthrough',
    'Aggressive', 'Defender', 'Stealth', 'Stat Buff', 'Attack Buff', 'Health Buff', 'Stat Debuff', 'Increased A',
    'Attack Debuff', 'Health Debuff', 'Destruction Others', 'Destruction Self', 'Self Damage Activator', 'Silence', 'Exalt', 'Slay',
    'Reanimate', 'Deploy', 'Deploy Synergy', 'Spicy', 'Cool', 'Fun', 'Annoying',    
    'Beast Synergy', 'Dinosaur Synergy', 'Mage Synergy', 'Robot Synergy', 'Scientist Synergy',
    'BanishSpirit Synergy', 'Spirit Synergy', 'Warrior Synergy', 'Zombie Synergy', 'Dragon Synergy', 'Elemental Synergy',
    'Plant Synergy', 'Minion Synergy', 'Spell Synergy', 'Exalt Synergy', 'Healing Synergy', 'Movement Benefit', 'Replace Profit',
    'Armor Synergy', 'Upgrade Synergy', 'Destruction Synergy', 'Self Damage Payoff', 'Increased A Synergy', 'FB Creature Synergy' 
]
 
COMBOS = [
    'Sum','Free',
    'BEAST Combo', 'DINOSAUR Combo', 'MAGE Combo', 'ROBOT Combo', 'SCIENTIST Combo',
    'BANISH SPIRIT Combo', 'SPIRIT Combo', 'WARRIOR Combo', 'ZOMBIE Combo', 'DRAGON Combo', 'ELEMENTAL Combo',
    'PLANT Combo', 'MINION Combo', 'SPELL Combo', 'EXALT Combo', 
    'REPLACE Combo', 'DEPLOY Combo', 'READY Combo', 'REANIMATE Combo',
    'HEALING Combo', 'MOVEMENT Combo', 'DESTRUCTION Combo', 'DESTROYED Combo', 'SELFDAMAGE Combo', 
    'ARMOR Combo', 'UPGRADE Combo', 'FACE DMG Combo', 'INC ATTACK Combo'
] 
     
# Define the information levels
DETAILED_FIELDS = BASIC_FIELDS + DATE_FIELDS + STATS_FIELDS + ['cardTitles']

# Defining components with nested fields
COMPONENTS = {
    'Basic': BASIC_FIELDS,
    'Detail': DETAILED_FIELDS,
    'Stats': AVERAGE_FIELDS,
    'Tags': TAGS,
    'Combos': COMBOS,
    'All Fields': ['Basic Info', 'Detailed Info', 'Stats', 'Tags', 'Combos']
}


def resolve_component_fields(component_name):
    """Recursively resolve a component to its fields."""
    final_fields = set()
    component = COMPONENTS.get(component_name)

    if component is None:
        return final_fields

    if isinstance(component, list):
        for item in component:
            if item in COMPONENTS:
                # If item is another component, resolve its fields recursively
                final_fields.update(resolve_component_fields(item))
            else:
                # If item is a field, add it directly
                final_fields.add(item)

    return final_fields


def generate_final_fields(info_level, tag_level, item_type):
    """Generate a final list of fields based on the info level, tag level, and item type (Deck or Fusion)."""
    final_fields = set()        
    final_fields.update(resolve_component_fields(info_level))

    # Add fields from the tag level if specified
    if tag_level:
        final_fields.update(resolve_component_fields(tag_level))

    # Filter out fields that don't belong to the current item type
    if item_type == 'Deck':
        final_fields = {field for field in final_fields if field not in TYPE_SPECIFIC_FIELDS['Fusion']}
    elif item_type == 'Fusion':
        final_fields = {field for field in final_fields if field not in TYPE_SPECIFIC_FIELDS['Deck']}

    final_fields = sorted(final_fields, key=lambda field: GLOBAL_COLUMN_ORDER.index(field))

    return list(final_fields)


# Example usage
if __name__ == "__main__":
    # Set the selectors
    info_level = 'Basic Info'  # Could be 'Basic Info' or 'Detailed Info'
    tag_level = None  # Could be None, 'Tags and Combos', etc.
    item_type = 'Fusion'  # Could be 'Deck' or 'Fusion'

    # Generate the final list of fields
    final_fields = generate_final_fields(info_level, tag_level, item_type)
    print(final_fields)
