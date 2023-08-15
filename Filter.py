class Filter:
    def __init__(self, criteria_list):       
        self.criteria_list = criteria_list 
        self.criteria_dict = {
            'F'     : ('faction', str),
            'D'     : ('name', str),
            'FB'    : ('forgeborn.name', str),
            'C'     : ('cards', list),
            'A'     : ('forgeborn.abilities', list)
        }

    def apply(self, objects):
        if isinstance(objects, dict):
            filtered_objects = {}
            for key, obj in objects.items():
                if self.match(obj):
                    filtered_objects[key] = obj
            return filtered_objects
        else:
            filtered_objects = []
            for obj in objects:
                if self.match(obj):
                    filtered_objects.append(obj)
            return filtered_objects

    def match(self, obj):
        for attribute, values in self.criteria_list.items():
            if attribute in self.criteria_dict:
                attribute_path, data_type = self.criteria_dict[attribute]                                
                attributes = attribute_path.split('.')
                current_attr = obj
                for attr in attributes:
                    current_attr = getattr(current_attr, attr)

                # Dictionary
                if data_type is dict:
                    if any(value in key for key in current_attr.values() for value in values):
                        return True
                #List
                elif data_type is list:
                    if any(value in attr for value in values for attr in current_attr):
                        return True
                #String
                elif any(value in str(current_attr) for value in values):
                    return True
        return False