import networkx as nx
import importlib

def get_class_from_path(full_class_path):
    if '.' not in full_class_path:
        print(f"No Module found: {full_class_path}")
        return None, None

    module_name, class_name = full_class_path.rsplit('.', 1)

    try:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        return cls, class_name
    except (ModuleNotFoundError, AttributeError) as e:
        print(f"Error loading {full_class_path}: {e}")
        return None, None

class MyGraph:
    
    graph_cache = {}  # Class-level cache to store graphs
    
    def __init__(self):
        self.G = nx.DiGraph()
        self.node_data =  { 'tags': {}}

    def add_node(self, child_object, **attributes):
        node_id = self.get_node_id(child_object)
        self.G.add_node(node_id, **attributes)

    def add_edge(self, parent, child_object, **attributes):
        parent_id = self.get_node_id(parent)
        child_id = self.get_node_id(child_object)
        self.G.add_edge(parent_id, child_id, **attributes)

    def get_node_id(self, node):
        for attr in ['name', 'tag', 'title']:
            node_id = getattr(node, attr, None)
            if node_id:
                return node_id
        return node if isinstance(node, str) else ''

    def set_node_attributes(self, node, **attributes):
        node_id = self.get_node_id(node)
        self.G.nodes[node_id].update(attributes)

    def create_graph_children(self, db_object, parent_object=None, root=None):
        # # Use a unique identifier for caching, for example, the name or ID
        # object_id = self.get_node_id(db_object)
        # if object_id in MyGraph.graph_cache:
        #     # Load the graph from cache
        #     self.G, self.node_data = MyGraph.graph_cache[object_id]
        #     return
        
        root, parent_object = self._initialize_root_and_parent(db_object, parent_object, root)
        if db_object.children_data:
            for child_name, full_class_path in db_object.children_data.items():
                self._process_child(root, db_object, parent_object, child_name, full_class_path)

        # After graph is constructed, cache it
        # MyGraph.graph_cache[object_id] = (self.G.copy(), dict(self.node_data))

    def _initialize_root_and_parent(self, db_object, parent_object, root):
        if not root or not parent_object:
            root = self
            parent_object = db_object
            self.add_node(db_object, color='purple')
        return root, parent_object

    def _print_parent_and_db_object(self, parent_object, db_object):
        parent_type = parent_object.__class__.__name__
        self_type = db_object.__class__.__name__
        #print(f"Parent Object = {self.get_node_id(parent_object)}[{parent_type}], Db Object = {self.get_node_id(db_object)}[{self_type}]")

    def _process_child(self, root, db_object, parent_object, child_name, full_class_path):
        cls, child_type = get_class_from_path(full_class_path)
        if not cls or not child_type:
            return

        #print(f"Child Name = {child_name}[{child_type}]")

        if child_type == 'Interface':
            self._process_interface_child(root, db_object, parent_object, child_name, full_class_path)
        elif child_type == 'Synergy':
            self._process_synergy_child(root, db_object, cls, child_name)
        elif child_type == 'Forgeborn':
            self._process_forgeborn_child(root, db_object, parent_object, child_name, full_class_path)                     
        else:
            child_object = cls.lookup(child_name)
            #print(f"Child Object = {child_object}")
            if child_object:
                color = self._get_color_based_on_child_type(child_type, child_object)
                self._add_child_to_graph(root, db_object, parent_object, child_object, color)
                self.create_graph_children(child_object, parent_object=db_object, root=root)

    def _process_forgeborn_child(self, root, db_object, parent_object, child_name, full_class_path):
        forgebornId = child_name[5:-3]
        cls, child_type = get_class_from_path(full_class_path)
        if not cls or not child_type:
            return

        forgeborn_object = cls.load(forgebornId)
        forgeborn_object.get_permutation(forgebornId)
        color = self._get_color_based_on_child_type(child_type, forgeborn_object)
        self._add_child_to_graph(root, db_object, parent_object, forgeborn_object, color)
        self.create_graph_children(forgeborn_object, db_object, root)

    def _process_interface_child(self, root, db_object, parent_object, child_name, full_class_path):
        cls, child_type = get_class_from_path(full_class_path)
        if not cls or not child_type:
            return

        #print(f"Child Name = {child_name}[{child_type}]")

        # Increase the number of child_name in the node_data dictionary
        self.node_data['tags'].setdefault(child_name, 0)
        self.node_data['tags'][child_name] += 1
        
        #child_object = cls.load(child_name)
        child_object = cls.lookup(child_name)
        if child_object:
            #print(f"Interface Child Object = {child_object}")
            color = self._get_color_based_on_child_type(child_type, child_object)
            self._add_child_to_graph(root, db_object, parent_object, child_object, color)
            self.create_graph_children(child_object, parent_object=db_object, root=root)

    def _process_synergy_child(self, root, db_object, cls, child_name):
        child_object = cls.load(child_name)
        #print(f"Synergy Child Object = {child_object}")
        node_attributes = {'shape': 'diamond', 'color': 'greenyellow', 'label': self.get_node_id(child_object)}
        root.add_node(child_object, **node_attributes)
        root.add_edge(db_object, child_object)
        self._add_parent_to_child(root, db_object, child_object)

    def _get_color_based_on_child_type(self, child_type, child_object):
        """
        Returns the color based on the child type.

        Parameters:
        - child_type: The type of the child object.
        - child_object: The child object.

        Returns:
        - color: The color based on the child type.
        """
        if child_type == 'Interface':
            if child_object.types and 'O' in child_object.types:
                return "gainsboro"
            if child_object.types and 'I' in child_object.types:
                return "gold"
        color_mapping = {
            'Card': 'skyblue',
            'Fusion': 'purple',
            'Deck': 'violet'
        }
        return color_mapping.get(child_type, '#97c2fc')


    def _add_child_to_graph(self, root, db_object, parent_object, child_object, color):
        source_object, target_object, source_type, target_type = self._get_source_and_target_objects(db_object, parent_object, child_object)

        if target_type != 'Entity' or source_type == 'Forgeborn':
            root.add_node(target_object, color=color, title=target_type)
        else:
            return

        dashes = source_type in ['Fusion', 'Deck', 'Forgeborn']
        edge_arguments = {'smooth': {'type': 'diagonalCross'}} if dashes else {'smooth': False}
        if source_type not in ['Deck', 'Forgeborn']:
            root.add_edge(source_object, target_object, **edge_arguments)

        self._add_parent_to_child(root, source_object, target_object)

    def _get_source_and_target_objects(self, db_object, parent_object, child_object):
        source_object = db_object
        target_object = child_object
        parent_type = parent_object.__class__.__name__

        if source_object.__class__.__name__ == 'Entity' and parent_type == 'Card':
            source_object = parent_object

        return source_object, target_object, source_object.__class__.__name__, target_object.__class__.__name__

    def _add_parent_to_child(self, root, source_object, target_object):
        child_node = root.G.nodes[self.get_node_id(target_object)]
        child_node.setdefault('parents', []).append(self.get_node_id(source_object))

    def get_length_interface_ids(self):
        return {interface_id: self.node_data['tags'][interface_id]
                for interface_id in self.node_data['tags']}
