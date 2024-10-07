import networkx as nx
import importlib

from numpy import source

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
        self.G = nx.MultiDiGraph()
        self.node_data =  { 'tags': {}}

    def add_node(self, child_object, **attributes):
        node_id = self.get_node_id(child_object)
        # Set a default node_type if not provided
        if 'node_type' not in attributes:
            attributes['node_type'] = 'generic'
        self.G.add_node(node_id, **attributes)

    def add_edge(self, parent, child_object, **attributes):
        parent_id = self.get_node_id(parent)
        child_id = self.get_node_id(child_object)
        
        # Add the edge between parent and child
        self.G.add_edge(parent_id, child_id, **attributes)

        # Update incoming edge information for the child node
        # If storing the number of incoming edges:
        if 'parents' not in self.G.nodes[child_id]:
            self.G.nodes[child_id]['parents'] = []
        
        self.G.nodes[child_id]['parents'].append(parent_id)

        # Optionally, if storing the sum of weights from all incoming edges:
        # current_weight = self.G.nodes[child_id].get('weight', 0)
        # edge_weight = attributes.get('weight', 1)  # Assuming a default weight of 1 if not provided
        # self.G.nodes[child_id]['weight'] = current_weight + edge_weight
        
        # Store or update label directly with the number of parents or total weight
        num_parents = len(self.G.nodes[child_id]['parents'])
        self.G.nodes[child_id]['label'] = f"{child_id}[{num_parents}]"

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
            ftype = 'name'  if child_type == 'Entity' else '_id'
            child_object = cls.lookup(child_name, type=ftype)
            #print(f"Child Object = {child_object}")
            if child_object:
                node_attributes = {
                    'color': self._get_color_based_on_child_type(child_type, child_object),
                    'node_type': child_type,  # Include the node type
                }
                self._add_child_to_graph(root, db_object, parent_object, child_object, node_attributes)
                self.create_graph_children(child_object, parent_object=db_object, root=root)

    def _process_forgeborn_child(self, root, db_object, parent_object, child_name, full_class_path):
        forgebornId = child_name[5:-3]
        cls, child_type = get_class_from_path(full_class_path)
        if not cls or not child_type:
            return

        forgeborn_object = cls.load(forgebornId)
        forgeborn_object.get_permutation(forgebornId)
        node_attributes = {
                'color': self._get_color_based_on_child_type(child_type, forgeborn_object),
                'node_type': child_type,
            }
        self._add_child_to_graph(root, db_object, parent_object, forgeborn_object, node_attributes)
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
            node_attributes = {
                'color': self._get_color_based_on_child_type(child_type, child_object),
                'node_type': 'Interface',  # Mark this node as an interface
            }
            self._add_child_to_graph(root, db_object, parent_object, child_object, node_attributes)
            self.create_graph_children(child_object, parent_object=db_object, root=root)
        
    def _process_synergy_child(self, root, db_object, cls, child_name):
        # Load the Synergy child object
        child_object = cls.load(child_name)

        # Count incoming edges for the synergy child node
        child_id = self.get_node_id(child_object)
        input_count, output_count = self.count_incoming_edge_types(child_id)

        # Define Synergy-specific attributes
        node_attributes = {
            'shape': 'diamond',
            'color': 'greenyellow',
            'label': self.get_node_id(child_object),
            'node_type': 'Synergy',
            'input_count': input_count,
            'output_count': output_count
        }

        # Use the centralized method to add the child node and its edge
        self._add_child_to_graph(root, db_object, parent_object=db_object, child_object=child_object, node_attributes=node_attributes)
        
        # Update the label with the input and output counts
        self.G.nodes[child_id]['label'] += f"[{input_count}<-{output_count}]"


    def count_incoming_edge_types(self, node_id):
        """
        Counts the number of incoming edges for a node, categorized by type 'I' (Input) and 'O' (Output).

        Parameters:
        - node_id (str): The ID of the node for which to count incoming edge types.

        Returns:
        - tuple: A tuple (input_count, output_count) representing the count of input and output edges.
        """
        input_count = 0
        output_count = 0

        # Iterate over all incoming edges to the node
        for _, _, edge_data in self.G.in_edges(node_id, data=True):
            # Check if the edge type includes 'I' for Input and 'O' for Output
            edge_types = edge_data.get('types', [])
            
            # Count based on 'I' and 'O' type
            if 'I' in edge_types:
                input_count += 1
            if 'O' in edge_types:
                output_count += 1

        return input_count, output_count
            
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


    def _add_child_to_graph(self, root, db_object, parent_object, child_object, node_attributes):
        """
        Adds a child node to the graph with provided attributes.
        
        Parameters:
        - root: The root of the graph.
        - db_object: The database object representing the parent node.
        - parent_object: The parent object of the child.
        - child_object: The child object to be added.
        - node_attributes: The attributes for the child node (e.g., color, node_type).
        """
        source_object, target_object, source_type, target_type = self._get_source_and_target_objects(db_object, parent_object, child_object)

        if target_type != 'Entity' or source_type == 'Forgeborn':
            # Add the node with provided attributes (color, node_type, etc.)
            root.add_node(target_object, **node_attributes)
        else:
            return

        # Initialize the edge type as None
        edge_types = ['undirected']

        # Check for 'Interface' to 'Synergy' relationship and fetch the type from the Interface object
        if source_type == 'Interface' and target_type == 'Synergy':
            edge_types = source_object.types
            #self._fetch_edge_type_from_interface(source_object)


        # Prepare edge attributes with determined edge type
        edge_arguments = {
            'types': edge_types,
            'smooth': {'type': 'diagonalCross'} if source_type in ['Fusion', 'Deck', 'Forgeborn'] else {'smooth': False}
        }

        if source_type not in ['Deck', 'Forgeborn']:
            root.add_edge(source_object, target_object, **edge_arguments)

#        self._add_parent_to_child(root, source_object, target_object)

    def _get_source_and_target_objects(self, db_object, parent_object, child_object):
        source_object = db_object
        target_object = child_object
        parent_type = parent_object.__class__.__name__

        if source_object.__class__.__name__ == 'Entity' and parent_type == 'Card':
            source_object = parent_object

        return source_object, target_object, source_object.__class__.__name__, target_object.__class__.__name__

    # def _add_parent_to_child(self, root, source_object, target_object):
    #     child_node = root.G.nodes[self.get_node_id(target_object)]
    #     child_node.setdefault('parents', []).append(self.get_node_id(source_object))

    def get_length_interface_ids(self):
        return {interface_id: self.node_data['tags'][interface_id]
                for interface_id in self.node_data['tags']}

    def get_combos(self):
        """
        Collects the number of input and output synergies for every synergy node in the graph,
        distinguishing them by the edge types 'I' for input and 'O' for output.
        
        :return: A dictionary with nodes as keys and a tuple (input_synergies, output_synergies) as values.
        """
        synergy_counts = {}

        # Iterate through each node in the graph
        for node in self.G.nodes:
            node_data = self.G.nodes[node]

            # Check if the node is a synergy node by its `node_type`
            if node_data.get('node_type') == 'Synergy':
                input_synergies = node_data.get('input_count', 0)
                output_synergies = node_data.get('output_count', 0)

                # Store the counts in the dictionary
                if input_synergies == 0 or output_synergies == 0:
                    input_synergies = -input_synergies
                    output_synergies = -output_synergies
                synergy_counts[node] = (input_synergies, output_synergies)

        return synergy_counts

    def to_dict(self):
        """
        Converts the entire graph, including node and edge attributes, into a dictionary.
        
        :return: A dictionary containing all data needed to restore the graph.
        """
        graph_dict = {
            'nodes': {node: self.G.nodes[node] for node in self.G.nodes},
            'edges': nx.to_dict_of_dicts(self.G),
            'node_data': self.node_data  # Include additional node data, if needed
        }
        
        # Convert edges, changing integer keys to strings
        for source, targets in self.G.adjacency():
            graph_dict['edges'][source] = {}
            for target, key_dict in targets.items():
                graph_dict['edges'][source][target] = {str(k): v for k, v in key_dict.items()}
            
        return graph_dict

    def from_dict(self, graph_dict):
        """
        Restores the graph from a dictionary format containing nodes and edges with attributes.
        
        :param graph_dict: A dictionary containing the data to restore the graph.
        """
        # Restore the edges with nx.from_dict_of_dicts
        self.G = nx.from_dict_of_dicts(graph_dict['edges'], create_using=nx.DiGraph)
        
        # Restore node attributes
        for node, attributes in graph_dict['nodes'].items():
            if node in self.G:
                self.G.nodes[node].update(attributes)
            else:
                self.G.add_node(node, **attributes)  # Add the node with attributes if it wasn't included in edges

        # Restore additional node data
        self.node_data = graph_dict.get('node_data', {'tags': {}})
    
