from platform import node
import networkx as nx
import importlib

def get_class_from_path(full_class_path):
    if '.' not in full_class_path:
        print(f"No Module found: {full_class_path}")
        return None, None

    module_name, class_name = full_class_path.rsplit('.', 1)  # Split on last dot

    try:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        return cls, class_name
    except (ModuleNotFoundError, AttributeError) as e:
        print(f"Error loading {full_class_path}: {e}")
        return None, None

class MyGraph:
    def __init__(self):
        self.G      = nx.DiGraph()
        #self.G.add_node(self.get_nodeId(self.object), color='purple')  # Use the name of the object as the node ID
        
    def add_node(self, child_object, **attributes):
        nodeId_child  = self.get_nodeId(child_object)
        self.G.add_node(nodeId_child, **attributes)

    def add_edge(self, parent, child_object, **attributes):
        nodeId_parent = self.get_nodeId(parent)
        nodeId_child  = self.get_nodeId(child_object)
        self.G.add_edge(nodeId_parent, nodeId_child ,**attributes)

    def get_nodeId(self, node):
        nodeId = ''
        if isinstance(node, str): nodeId = node
        elif node.name :   nodeId = node.name         
        elif node.tag :  nodeId = node.tag
        elif node.title: nodeId = node.title
        return nodeId
    
    def set_node_attributes(self, node, **attributes):
        nodeId = self.get_nodeId(node)
        self.G.nodes[nodeId].update(attributes)

    def create_graph_statistics(self):
        # Create statistics for the graph 

        pass

    def create_graph_children(self, db_object, parent_object=None, root=None):
        """
        Creates the children nodes and edges for a given database object.

        Parameters:
        - db_object: The database object for which to create the children nodes and edges.
        - parent_object: The parent object of the database object. Default is None.
        - root: The root object of the graph. Default is None.

        Returns:
        None
        """
        root, parent_object = self.initialize_root_and_parent(db_object, parent_object, root)
        self.print_parent_and_db_object(parent_object, db_object)

        if db_object.children_data:
            for child_name, full_class_path in db_object.children_data.items():
                self.process_child(root, db_object, parent_object, child_name, full_class_path)

        return

    def initialize_root_and_parent(self, db_object, parent_object, root):
        """
        Initializes the root and parent objects if they are not provided.

        Parameters:
        - db_object: The database object.
        - parent_object: The parent object. Default is None.
        - root: The root object. Default is None.

        Returns:
        - root: The initialized root object.
        - parent_object: The initialized parent object.
        """
        if not root or not parent_object: 
            root = self
            parent_object = db_object
            self.add_node(self.get_nodeId(db_object), color='purple')
        return root, parent_object

    def print_parent_and_db_object(self, parent_object, db_object):
        """
        Prints the parent object and database object information.

        Parameters:
        - parent_object: The parent object.
        - db_object: The database object.

        Returns:
        None
        """
        parentType = parent_object.__class__.__name__
        selfType = db_object.__class__.__name__
        #print(f"Parent Object = {self.get_nodeId(parent_object)}[{parentType}] , Db Object = {self.get_nodeId(db_object)}[{selfType}] \n")

    def process_child(self, root, db_object, parent_object, child_name, full_class_path):
        """
        Processes a child object and adds it to the graph.

        Parameters:
        - root: The root object of the graph.
        - db_object: The database object.
        - parent_object: The parent object.
        - child_name: The name of the child object.
        - full_class_path: The full class path of the child object.

        Returns:
        None
        """
        color = '#97c2fc'        

        cls , childType = get_class_from_path(full_class_path)
        if not cls or not childType: return

        #print(f"Child Name = {child_name}[{childType}] \n")

        if childType == 'Synergy': 
            self.process_synergy_child(root, db_object, cls, child_name)
            return

        child_object = cls.lookup(child_name)
        if child_object:
            color = self.get_color_based_on_child_type(childType, child_object)
            self.add_child_to_graph(root, db_object, parent_object, child_object, color)
            self.create_graph_children(child_object, parent_object=db_object, root=root)

    def process_synergy_child(self, root, db_object, cls, child_name):
        """
        Processes a synergy child object and adds it to the graph.

        Parameters:
        - root: The root object of the graph.
        - db_object: The database object.
        - cls: The class of the child object.
        - child_name: The name of the child object.

        Returns:
        None
        """
        child_object = cls.load(child_name)
        node_attributes = {'shape' : 'diamond', 'color' : 'greenyellow', 'label' : self.get_nodeId(child_object)}
        root.add_node(child_object, **node_attributes)
        root.add_edge(db_object, child_object)  
        self.add_parent_to_child(root, db_object, child_object)

    def get_color_based_on_child_type(self, childType, child_object):
        """
        Returns the color based on the child type.

        Parameters:
        - childType: The type of the child object.
        - child_object: The child object.

        Returns:
        - color: The color based on the child type.
        """
        if childType == 'Interface':             
            if 'O' in child_object.types:
                return "gainsboro"
            if 'I' in child_object.types: 
                return "gold"
        elif childType == 'Card':     return 'skyblue'
        elif childType == 'Fusion': return 'purple'
        elif childType == 'Deck':   return 'violet'                                            
        else : return '#97c2fc'

    def add_child_to_graph(self, root, db_object, parent_object, child_object, color):
        """
        Adds a child object to the graph.

        Parameters:
        - root: The root object of the graph.
        - db_object: The database object.
        - parent_object: The parent object.
        - child_object: The child object.
        - color: The color of the child object.

        Returns:
        None
        """
        source_object, target_object, source_type, target_type = self.get_source_and_target_objects(db_object, parent_object, child_object)
        if not target_type == 'Entity' or source_type == 'Forgeborn':
            root.add_node(target_object, color=color, title=target_type)
        else:
            #print(f"Skipping {self.get_nodeId(target_object)} \n")
            return
        dashes = True if source_type in ['Fusion', 'Deck', 'Forgeborn'] else False                
        edge_arguments = {'smooth' : {'type' : 'diagonalCross'}} if dashes else {'smooth' : False}
        if not source_type in ['Deck', 'Forgeborn']:
            root.add_edge(source_object, target_object, **edge_arguments)
            #self.print_edge_info(target_type, source_object, target_object)
        #if source_object not in ['Fusion', 'Deck', 'Forgeborn']:
        self.add_parent_to_child(root, source_object, target_object)

    def get_source_and_target_objects(self, db_object, parent_object, child_object):
        """
        Returns the source and target objects for adding an edge to the graph.

        Parameters:
        - db_object: The database object.
        - parent_object: The parent object.
        - child_object: The child object.

        Returns:
        - source_object: The source object.
        - target_object: The target object.
        - source_type: The type of the source object.
        - target_type: The type of the target object.
        """
        source_object = db_object
        target_object = child_object
        parent_object = parent_object
        source_type = source_object.__class__.__name__
        target_type = target_object.__class__.__name__
        parent_type = parent_object.__class__.__name__
        
        #If an edge is to be made between Card and Entity , instead make an edge between Card and Entities children
        if source_type == 'Entity' and parent_type == 'Card':
            #print(f"Changing source object from {self.get_nodeId(source_object)} to {self.get_nodeId(parent_object)}")
            source_object = parent_object
            source_type = source_object.__class__.__name__
        return source_object, target_object, source_type, target_type

    def print_edge_info(self, target_type, source_object, target_object):
        """
        Prints the edge information.

        Parameters:
        - target_type: The type of the target object.
        - source_object: The source object.
        - target_object: The target object.

        Returns:
        None
        """

        #Get edge attributes for source_object -> target_object
        edge_attributes = self.G.get_edge_data(self.get_nodeId(source_object), self.get_nodeId(target_object))
        #print all edge attributes
        #print(f"Edge Attributes = {edge_attributes} \n")     
    

    def add_parent_to_child(self, root, source_object, target_object):
        """
        Adds the parent object to the child object.

        Parameters:
        - root: The root object of the graph.
        - source_object: The source object.
        - target_object: The target object.

        Returns:
        None
        """
        ChildNode = root.G.nodes[root.get_nodeId(target_object)]                
        ChildNode.setdefault('parents', [])
        ChildNode['parents'].append(self.get_nodeId(source_object))
