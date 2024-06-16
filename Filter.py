import re

class Node:
    pass

class LogicalOperator(Node):
    def __init__(self, left, right, operator):
        self.left = left
        self.right = right
        self.operator = operator

class Condition(Node):
    def __init__(self, attribute, operator, value, dict_key=None, focus=None):
        self.attribute = attribute
        self.operator = operator
        self.value = value
        self.dict_key = dict_key
        self.focus = focus # Either 'keys' , 'values' or None

class Filter:
    def __init__(self, query, attribute_map):
        self.attribute_map = attribute_map
        tokens = self.tokenize(query)
        self.ast = self.parse(tokens)
        
    def tokenize(self, query):
        # Match strings between quotes, or any other existing pattern
        return re.findall(r'".+?"|&|\||!|\w+(?::\w+)?|[=<>~]+|\d+|\(|\)', query)

    def parse(self, tokens):
        return self._parse_logical(tokens)

    def _parse_logical(self, tokens):
        node = self._parse_or(tokens)
        while tokens and tokens[0] in ('|', '&'):
            operator = tokens.pop(0)
            right = self._parse_or(tokens)
            node = LogicalOperator(node, right, operator)
        return node

    def _parse_or(self, tokens):
        node = self._parse_and(tokens)
        while tokens and tokens[0] == '|':
            tokens.pop(0)
            right = self._parse_and(tokens)
            node = LogicalOperator(node, right, '|')
        return node

    def _parse_and(self, tokens):
        node = self._parse_not(tokens)
        while tokens and tokens[0] == '&':
            tokens.pop(0)
            right = self._parse_not(tokens)
            node = LogicalOperator(node, right, '&')
        return node

    def _parse_not(self, tokens):
        if tokens and tokens[0] == '!':
            tokens.pop(0)
            node = self._parse_not(tokens)
            return LogicalOperator(None, node, '!')
        else:
            return self._parse_group(tokens) if tokens and tokens[0] == '(' else self._parse_condition(tokens)

    def _parse_group(self, tokens):
        tokens.pop(0)  # Consume the opening parenthesis
        node = self._parse_logical(tokens)
        if tokens and tokens[0] == ')':
            tokens.pop(0)  # Consume the closing parenthesis
        else:
            raise ValueError("Missing closing parenthesis in group")
        return node
        
    def _parse_condition(self, tokens):
        token = tokens.pop(0)
        abbreviation, dict_key = None, None
        if ':' in token:
            abbreviation, dict_key = token.split(':')
            dict_key = dict_key.strip()  # remove leading/trailing whitespaces
        else:
            abbreviation = token

        operator = tokens.pop(0)
        value = tokens.pop(0)

        # Remove surrounding quotation marks if they exist
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]

        attribute, dtype, focus = self.attribute_map[abbreviation]
        if dtype is float:
            value = float(value)
        elif dtype is int:
            value = int(value)
        elif dtype is bool:
            value = value.lower() in ['true', '1', 'yes']

        return Condition(attribute, operator, value, dict_key, focus)

    def apply(self, objects):
        if isinstance(objects, dict):
            return {key: obj for key, obj in objects.items() if self.match(obj, self.ast)}
        else:
            return [obj for obj in objects if self.match(obj, self.ast)]

    def match(self, obj, node):
        if isinstance(node, Condition):
            return self.evaluate_condition(obj, node)
        elif isinstance(node, LogicalOperator):
            left_result = self.match(obj, node.left) if node.left is not None else True
            right_result = self.match(obj, node.right)
            if node.operator == '&':
                return left_result and right_result
            elif node.operator == '|':
                return left_result or right_result
            elif node.operator == '!':
                return not right_result

    def evaluate_condition(self, obj, condition):
        attribute = condition.attribute
        operator = condition.operator
        value = condition.value
        dict_key = condition.dict_key
        focus = condition.focus 
        
        current_attr = self.get_nested_attribute(obj, attribute)

        if current_attr is None:
            return False
        
        #Adjust based on the focus 
        if focus == 'keys' and isinstance(current_attr, dict):
            current_attr = [k[1] if isinstance(k, tuple) else k for k in current_attr.keys()]
        elif focus == 'values' and isinstance(current_attr, dict):
            current_attr = list(current_attr.values())

        if dict_key:
            if isinstance(current_attr, dict):
                current_attr = current_attr.get(dict_key, None)
            else:
                return False  # the attribute is not a dict, but a dict_key was specified

        if current_attr is None:
            return False

        # Ensure that the comparison is between compatible types:
        if isinstance(current_attr, (int, float)):
            try:
                value = float(value)
            except ValueError:
                return False

        # Perform the comparison specified by the operator
        if operator == '=':
            return current_attr == value
        elif operator == '>':
            return current_attr > value
        elif operator == '<':
            return current_attr < value
        elif operator == '~':
            if isinstance(current_attr, str):
                return value in current_attr  # Check for substring in a string
            elif isinstance(current_attr, (list, set, tuple)):
                return any(value in str(element) for element in current_attr)  # Check for substring in elements of a collection
            elif isinstance(current_attr, dict):
                return any(value in key for key in current_attr.keys())  # Check for substring in keys of a dictionary
            else:
                return False
        else:
            raise ValueError(f"Unknown operator: {operator}")

        return False


    def get_nested_attribute(self, obj, attribute_path):
        attributes = attribute_path.split('.')
        for attr in attributes:
            if obj is None:
                return None
            if isinstance(obj, dict):
                obj = obj.get(attr, None)
            else:
                obj = getattr(obj, attr, None)
        return obj


# Example usage:
# query = "F=Alloyin & (C~Drix | K:Robot > 3)"
# attribute_map = { 'F': ('faction', str), ... }
# filter = Filter(query, attribute_map)
# result = filter.apply(some_object_list)
