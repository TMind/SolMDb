class Filter:
    def __init__(self, criteria_list):       
        self.criteria_list = criteria_list 
        self.criteria_dict = {
            'faction'  : 'faction',
            'deckname' : 'name',
            'forgeborn': 'forgeborn.name',
            'cardname' : 'cards'
        }

    def apply(self, objects):
        filtered_objects = []
        for obj in objects:
            if self.match(obj):
                filtered_objects.append(obj)
        return filtered_objects

    def match(self, obj):
        for attribute, values in self.criteria_list.items():
            if attribute in self.criteria_dict:
                attribute_to_check = self.criteria_dict[attribute]
                attr_item = getattr(obj, attribute_to_check)
                if isinstance(attr_item, dict):
                    if any(value in key for key in attr_item.keys() for value in values):
                        return True
                elif isinstance(attr_item, list):
                    if any(value in attr for value in values for attr in attr_item):
                        return True
                elif any(value in str(attr_item) for value in values):
                    return True
        return False





# Criteria list exapmle
# {    
#    faction   => 'Alloyn'
#    cardname  => 'Mantis'
#    forgeborn => 'Cercee'
#    deckname  => 'Whizzing'
# }