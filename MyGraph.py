from hmac import new
import re
import attr
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
    
    object_cache = {} # Cache for objects to avoid loading them multiple times    
    
    def __init__(self):
        self.G = nx.DiGraph()
        self.node_data =  { 'tags': {}}
        self.combo_data = {}

    def add_node(self, child_object, **attributes):
        node_id = self.get_node_id(child_object)
        # Set a default node_type if not provided
        if 'node_type' not in attributes:
            attributes['node_type'] = 'generic'
        self.G.add_node(node_id, **attributes)

    def add_edge(self, parent, child_object, **attributes):
        parent_id = self.get_node_id(parent)
        child_id = self.get_node_id(child_object)

        # Extract edge weights and types
        weight_to_add = attributes.get('weight', 1)
        edge_types = attributes.get('types', ['undirected'])
        
        # Check if the child node exists
        edge_exists = self.G.has_edge(parent_id, child_id)
                
        # Check if the edge already exists
        if edge_exists:
            # Get current edge weights
            input_weight = self.G[parent_id][child_id].get('input_weight', 0)
            output_weight = self.G[parent_id][child_id].get('output_weight', 0)
            weight = self.G[parent_id][child_id].get('weight', 1)

            # Update edge weights based on types
            if 'I' in edge_types:
                input_weight += weight_to_add
                weight       += weight_to_add
            if 'O' in edge_types:
                output_weight += weight_to_add
                weight        += weight_to_add
            
            # Update the edge attributes
            attributes['weight'] = weight
            attributes['input_weight'] = input_weight
            attributes['output_weight'] = output_weight            
            self.G[parent_id][child_id].update(attributes)
                                
        else:
            # Add a new edge with weights
            self.G.add_edge(parent_id, child_id, **attributes)

        # Get current child node weights
        weight = self.G.nodes[child_id].get('weight', 0)
        input_weight = self.G.nodes[child_id].get('input_weight', 0)
        output_weight = self.G.nodes[child_id].get('output_weight', 0)

        # Initialize or update child node weights
        weight += weight_to_add
        input_weight  += weight_to_add if 'I' in edge_types else 0
        output_weight += weight_to_add if 'O' in edge_types else 0
        
        self.set_weight(child_id, weight, input_weight, output_weight)
        #print(f"{parent_id} -{weight_to_add}-> {child_id} [{self.G.nodes[child_id]['weight']}]")
            
    def set_weight(self, node_id, weight, input_weight=0, output_weight=0):
        self.G.nodes[node_id]['weight'] = weight
        if input_weight is not None:
            self.G.nodes[node_id]['input_weight'] = input_weight
        if output_weight is not None:
            self.G.nodes[node_id]['output_weight'] = output_weight
        self.update_label(node_id)

    def update_label(self, node_id):
        weight_self = self.G.nodes[node_id].get('weight', 1)
        input_weight = self.G.nodes[node_id].get('input_weight', 0)
        output_weight = self.G.nodes[node_id].get('output_weight', 0)
        self.G.nodes[node_id]['label'] = f"{node_id}[{weight_self}]"
        if input_weight or output_weight:
            self.G.nodes[node_id]['label'] += f"[{input_weight}:{output_weight}]"
            self.combo_data[node_id] = (input_weight , output_weight)
        
    def get_node_id(self, node):
        for attr in ['name', 'tag', 'title']:
            node_id = getattr(node, attr, None)
            if node_id:
                return node_id
        return node if isinstance(node, str) else ''

    def set_node_attributes(self, node, **attributes):
        node_id = self.get_node_id(node)
        self.G.nodes[node_id].update(attributes)
    
    def set_edge_attributes(self, source, target, **attributes):
        if self.G.has_edge(source, target):
            self.G[source][target].update(attributes)
            
    def get_node_attributes(self, node, attribute):
        node_id = self.get_node_id(node)
        return self.G.nodes[node_id].get(attribute, None)
        
    def create_graph_children(self, db_object, parent_object=None, root=None):      
        root, parent_object = self._initialize_root_and_parent(db_object, parent_object, root)
        if db_object.children_data:
            for child_name, full_class_path in db_object.children_data.items():
                self._process_child(root, db_object, parent_object, child_name, full_class_path)        

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
            self._process_synergy_child(root, db_object, full_class_path, child_name)
        elif child_type == 'Forgeborn':
            self._process_forgeborn_child(root, db_object, parent_object, child_name, full_class_path)                     
        else:
            ftype = 'name'  if child_type == 'Entity' else '_id'            
            child_object = self.get_cached_child_object(full_class_path, child_name, field=ftype)                
            
            #print(f"Child Object = {child_object}")
            if child_object:
                node_attributes = {
                    'color': self._get_color_based_on_child_type(child_type, child_object),
                    'node_type': child_type,  # Include the node type
                }
                self._add_child_to_graph(root, db_object, parent_object, child_object, node_attributes)
                self.create_graph_children(child_object, parent_object=db_object, root=root)
            else:
                #print(f"process_child: Child Object not found: {child_name}")
                pass

    def _process_forgeborn_child(self, root, db_object, parent_object, child_name, full_class_path):
        forgebornId = child_name
        forgebornName = child_name[5:-3]
        cls, child_type = get_class_from_path(full_class_path)
        if not cls or not child_type:
            return

        forgeborn_object = self.get_cached_child_object(full_class_path, forgebornName, field='name')
        if not forgeborn_object:
            #print(f"process_forgeborn: Child Object not found: {child_name}")
            return
        forgeborn_with_abilities_object = forgeborn_object.get_permutation(forgebornId)
        node_attributes = {
                'color': self._get_color_based_on_child_type(child_type, forgeborn_with_abilities_object),
                'node_type': child_type,
            }
        self._add_child_to_graph(root, db_object, parent_object, forgeborn_with_abilities_object, node_attributes)
        self.create_graph_children(forgeborn_with_abilities_object, db_object, root)

    def _process_interface_child(self, root, db_object, parent_object, child_name, full_class_path):
        cls, child_type = get_class_from_path(full_class_path)
        if not cls or not child_type:
            return

        child_object = self.get_cached_child_object(full_class_path, child_name)        
        
        if child_object:
            #print(f"Interface Child Object = {child_object}")            
            # Increase the number of child_name in the node_data dictionary
            weight = self._get_edge_weight(parent_object, child_object)    
            self.node_data['tags'].setdefault(child_name, 0)
            self.node_data['tags'][child_name] += weight
            
            node_attributes = {
                'color': self._get_color_based_on_child_type(child_type, child_object),
                'node_type': 'Interface',  # Mark this node as an interface
            }
            self._add_child_to_graph(root, db_object, parent_object, child_object, node_attributes)
            self.create_graph_children(child_object, parent_object=db_object, root=root)
        else:
            #print(f"Child Object not found: {child_name}")
            pass
        
    def _process_synergy_child(self, root, db_object, class_path, child_name):
        # Load the Synergy child object
        child_object = self.get_cached_child_object(class_path, child_name, field='name')

        if child_object is None:
            #print(f"process_synergy: Child Object not found: {child_name}")
            return

        # Define Synergy-specific attributes
        node_attributes = {
            'shape': 'diamond',
            'color': 'greenyellow',
            'label': self.get_node_id(child_object),
            'node_type': 'Synergy'
        }

        # Use the centralized method to add the child node and its edge
        self._add_child_to_graph(root, db_object, parent_object=db_object, child_object=child_object, node_attributes=node_attributes)
        
    def get_cached_child_object(self, class_path_or_cls, child_name, field='_id'):
        cls, _ = get_class_from_path(class_path_or_cls)
        cache_key = (class_path_or_cls, child_name)  
            
        # Check cache for existing object
        if cache_key in self.object_cache:
            return self.object_cache[cache_key]
        
        # Fetch and cache the child object using the determined class
        child_object = cls.get_instance(child_name, field=field)
        self.object_cache[cache_key] = child_object
        return child_object

    

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
            if child_object.types and 'I' in child_object.types:
                return "gold"
            if child_object.types and 'O' in child_object.types:
                return "gainsboro"
        color_mapping = {
            'Card': 'skyblue',
            'Fusion': 'purple',
            'Deck': 'violet',
            'Forgeborn': 'darkorange',
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
        elif target_type == 'Entity':
            # Save interfaces in node of parent object
            parent_node = root.G.nodes[self.get_node_id(source_object)]
            parent_node.setdefault('interfaces', {}).update(target_object.data.interfaces)
        else:    
            return

        # Initialize the edge type as None
        edge_types = ['undirected']

        # Check for 'Interface' to 'Synergy' relationship and fetch the type from the Interface object
        if source_type == 'Interface' and target_type == 'Synergy':
            edge_types = source_object.types

        # Get the weight of the edge based on the parent object's interfaces
        weight = self._get_edge_weight(parent_object, child_object)
        
        # Prepare edge attributes with determined edge type
        edge_arguments = {
            'weight': weight,
            'types': edge_types,
            'smooth': {'type': 'diagonalCross'} if source_type in ['Fusion', 'Deck', 'Forgeborn'] else {'smooth': False}
        }

        if source_type not in ['Fusion', 'Deck']:            
            root.add_edge(source_object, target_object, **edge_arguments)

    def _get_source_and_target_objects(self, db_object, parent_object, child_object):
        source_object = db_object
        target_object = child_object
        parent_type = parent_object.__class__.__name__

        if source_object.__class__.__name__ == 'Entity' and parent_type == 'Card':
            source_object = parent_object

        return source_object, target_object, source_object.__class__.__name__, target_object.__class__.__name__

    def _get_edge_weight(self, parent_object, child_object):
        """
        Returns the weight of the edge between the parent and child objects.
        
        Parameters:
        - parent_object: The parent object.
        - child_object: The child object.
        
        Returns:
        - weight: The weight of the edge between the parent and child objects.
        """
        
        node_id = self.get_node_id(parent_object)
        node = self.G.nodes[node_id]  
        #if 'weight' in node:      
        weight = node.get('weight', 1.0)
        #if isinstance(weight, float):
        #    print(f"Weight: {weight} for {node_id}")
        interfaces = node.get('interfaces', {})
        #interfaces = self.get_node_attributes(parent_object, 'interfaces')
        weight = interfaces.get(self.get_node_id(child_object), 1)
        return weight

    def get_length_interface_ids(self):
        return {interface_id: self.node_data['tags'][interface_id]
                for interface_id in self.node_data['tags']}

    def get_combos(self):
        """
        Collects the number of input and output synergies for every synergy node in the graph,
        distinguishing them by the edge types 'I' for input and 'O' for output.
        
        :return: A dictionary with nodes as keys and a tuple (input_synergies, output_synergies) as values.
        """
        if not self.combo_data: 
            
            print("No combo_data found. Calculating...")
            # Iterate through each node in the graph
            for node in self.G.nodes:
                node_data = self.G.nodes[node]
        
                # Check if the node is a synergy node by its `node_type`
                if node_data.get('node_type') == 'Synergy':
                    input_synergies = node_data.get('input_weight', 0)
                    output_synergies = node_data.get('output_weight', 0)
        
                    # Store the counts in the dictionary
                    if input_synergies == 0 or output_synergies == 0:
                        input_synergies = -input_synergies
                        output_synergies = -output_synergies
                    self.combo_data[node] = (input_synergies, output_synergies)
        
        return self.combo_data
        
    def to_dict(self):
        """
        Converts the entire graph, including node and edge attributes, into a dictionary.
        
        :return: A dictionary containing all data needed to restore the graph.
        """
        graph_dict = {
            'nodes': {node: self.G.nodes[node] for node in self.G.nodes},
            'edges': nx.to_dict_of_dicts(self.G),
            'node_data': self.node_data,  
            'combo_data' : self.combo_data
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
        self.combo_data = graph_dict.get('combo_data', {})
    
