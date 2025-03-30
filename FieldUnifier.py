from GlobalVariables import GLOBAL_COLUMN_ORDER

# Define fields that apply to all items (both Deck and Fusion)
BASIC_FIELDS = [
    'Type', 'name', 'faction', 'digital', 'cardSetNo', 'Forgeborn', 'FB2', 'FB3', 'FB4',
    'Betrayers', 'SolBinds', 'Spells', 'Exalt'
]


# Define type-specific fields
TYPE_SPECIFIC_FIELDS = {
    'Deck': ['level', 'xp', 'elo', 'deckScore', 'deckRank', 'registeredDate', 'nft'],
    'Fusion': ['crossFaction', 'Deck A', 'Deck B', 'CreatedAt']    
}

# Define fields related to dates for all types
DATE_FIELDS = ['registeredDate', 'pExpiry', 'CreatedAt', 'UpdatedAt']

# Define other specific field groupings that we can use as building blocks
STATS_FIELDS = ['id', 'nft', 'level', 'xp', 'elo', 'deckScore', 'deckRank', 'Deck A', 'Deck B', 'crossFaction']

AVERAGE_FIELDS = ['A1', 'H1', 'A2', 'H2', 'A3', 'H3']

NFT_FIELDS = ['price', 'owner']

TAGS = [
    'Beast', 'Darkforge', 'Dinosaur', 'Mage', 'Metamind', 'Robot', 'Scientist', 'Spirit', 'Warrior', 'Yeti', 'Zombie',
    'Dragon', 'Elemental', 'Plant', 'Minion', 'Spell', 'Healing Source', 'Movement',
    'Replace Setup', 'Armor', 'Armor Giver', 'Augment', 'Activate', 'Ready', 'Free', 'Upgrade', 'FB Creature', 'Face Burn', 'FB Giver', 'Removal', 'Breakthrough',
    'Aggressive', 'Defender', 'Defender Giver', 'Stealth', 'Stealth Giver', 'Stat Buff', 'Attack Buff', 'Health Buff', 'Stat Debuff', 'Increased A',
    'Attack Debuff', 'Health Debuff', 'Destruction Others', 'Destruction Self', 'Self Burn', 'Self Damage Activator', 'Silence', 'Slay',  # 'Exalt' already in Stats
    'Reanimate', 'Deploy', 'Adjacency', 'Hand Disruption', 'Spicy', 'Cool', 'Fun', 'Annoying',    
    'Beast Synergy', 'Darkforge Synergy', 'Dinosaur Synergy', 'Mage Synergy', 'Metamind Synergy', 'Robot Synergy', 'Scientist Synergy',
    'BanishSpirit Synergy', 'Spirit Synergy', 'Warrior Synergy', 'Yeti Synergy', 'Zombie Synergy', 'Dragon Synergy', 'Elemental Synergy',
    'Plant Synergy', 'Minion Synergy', 'Spell Synergy', 'Exalt Synergy', 'Healing Synergy', 'Self Burn Synergy', 'Movement Benefit', 'Replace Profit',
    'Armor Synergy', 'Augment Synergy', 'Deploy Synergy', 'Upgrade Synergy', 'Destruction Synergy', 'Self Damage Payoff', 'Slay Synergy', 'Increased A Synergy', 'FB Creature Synergy', 'FB Synergy', 'FB Giver Synergy', 
]
 
COMBOS = [
    'Sum','Free',
    'BEAST Combo', 'DARKFORGE Combo', 'DINOSAUR Combo', 'MAGE Combo', 'METAMIND Combo', 'ROBOT Combo', 'SCIENTIST Combo',
    'BANISH SPIRIT Combo', 'SPIRIT Combo', 'WARRIOR Combo', 'YETI Combo', 'ZOMBIE Combo', 'DRAGON Combo', 'ELEMENTAL Combo',
    'PLANT Combo', 'MINION Combo', 'SPELL Combo', 'EXALT Combo', 
    'REPLACE Combo', 'DEPLOY Combo', 'READY Combo', 'REANIMATE Combo',
    'HEALING Combo', 'MOVEMENT Combo', 'DESTRUCTION Combo', 'DESTROYED Combo', 'SELFDAMAGE Combo', 'SELF BURN Combo',
    'ARMOR Combo', 'AUGMENT Combo', 'UPGRADE Combo', 'FACE DMG Combo', 'FB GIVER Combo', 'INC ATTACK Combo', 'DEC ATTACK Combo', 'SLAY Combo'
] 
     
# Define the information levels
DETAILED_FIELDS = BASIC_FIELDS + DATE_FIELDS + STATS_FIELDS + ['CardTitles']
LISTING_FIELDS = BASIC_FIELDS + ['UpdatedAt'] + NFT_FIELDS

# Defining components with nested fields
COMPONENTS = {
    'Basic': BASIC_FIELDS,
    'Detail': DETAILED_FIELDS,    
    'Listing' : LISTING_FIELDS,
    'Stats': AVERAGE_FIELDS,
    'Tags': TAGS,
    'Combos': COMBOS,
    'Graph': TAGS + COMBOS,
    'All Fields': ['Basic', 'Detailed', 'Stats', 'Tags', 'Combos']
}


DB_TO_DF_FIELDS = {    
    'name': 'Name',
    'digital': 'Digital',
    'cardSetNo': 'Set',
    'deckRank': 'Rank',
    'deckScore': 'Score'
}

CONVERSION_TABLE_2DF = {
    #"myDecks[0].faction": "faction",
    "myDecks[0].name": "Deck A",
    "myDecks[1].name": "Deck B",
}

# Reverse mapping for DataFrame to Database fields
DF_TO_DB_FIELDS = {v: k for k, v in DB_TO_DF_FIELDS.items()}



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
                #print(f"Adding field    : {item}")
                final_fields.add(item)

    return final_fields


def generate_final_fields(info_level, tag_level, item_type, rename_fields_to=None):
    """
    Generate a final list of fields based on the info level, tag level, and item type (Deck or Fusion),
    while ensuring that fields from CONVERSION_TABLE are incorporated before filtering.

    Args:
        info_level (str): Information level determining which fields to include.
        tag_level (str): Tag level determining additional fields.
        item_type (str): Either 'Deck' or 'Fusion'.
        rename_fields_to (str, optional): Converts field names to 'db' (database) or 'df' (dataframe).

    Returns:
        list: A list of fields with appropriate renaming applied.
    """
    final_fields = set()
    
    # Step 1: Add fields based on info_level and tag_level
    final_fields.update(resolve_component_fields(info_level))

    if tag_level:
        final_fields.update(resolve_component_fields(tag_level))

    # Step 2: Incorporate fields from CONVERSION_TABLE before filtering
    final_fields.update(CONVERSION_TABLE_2DF.values())

    # Step 3: Filter out fields that don’t belong to the item type
    if item_type == 'Deck':
        final_fields = {field for field in final_fields if field not in TYPE_SPECIFIC_FIELDS['Fusion']}
    elif item_type == 'Fusion':
        final_fields = {field for field in final_fields if field not in TYPE_SPECIFIC_FIELDS['Deck']}

    # Step 4: Sort fields according to GLOBAL_COLUMN_ORDER
    final_fields = sorted(final_fields, key=lambda field: GLOBAL_COLUMN_ORDER.index(field))

    # Step 5: Apply renaming if requested
    if rename_fields_to:
        if rename_fields_to.lower() == 'db':
            final_fields = {DF_TO_DB_FIELDS.get(field, field) for field in final_fields}
        elif rename_fields_to.lower() == 'df':
            renamed_fields = {DB_TO_DF_FIELDS.get(field, field) for field in final_fields}

            # Ensure mapped conversion fields are also applied
            final_fields = {CONVERSION_TABLE_2DF.get(field, field) for field in renamed_fields}

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
