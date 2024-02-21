class DataClassOrganizer:
    def __init__(self, name=None, data=None):
        self.name = name
        self.data = data  # Arbitrary data specific to this instance
        self.children = {}  # Dictionary to hold child DCOs

    def add_child(self, child_name, child_data=None):
        # Adds a new child DCO instance or updates existing one
        if child_name not in self.children:
            self.children[child_name] = DataClassOrganizer(name=child_name, data=child_data)
        else:
            # Optionally update data if child already exists
            self.children[child_name].data = child_data

    def __str__(self, indent=0):
        # Recursive print function to display the structure
        rep = '  ' * indent + f"Name: {self.name}, Data: {self.data}\n"
        for child in self.children.values():
            rep += child.__str__(indent + 1)
        return rep

# Example usage to demonstrate adding and printing nested DCOs
root = DataClassOrganizer(name="Root")

# Adding a deck
root.add_child("The Mending Rexes Guardian", {"Description": "A powerful deck"})

# Adding cards to the deck
root.children["The Mending Rexes Guardian"].add_child("s1aa1adaptive-assassin", {"Power": 5})
root.children["The Mending Rexes Guardian"].add_child("s1aa1energy-prison", {"Power": 3})

print(root)
