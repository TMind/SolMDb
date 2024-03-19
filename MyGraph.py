from platform import node
import networkx as nx

class MyGraph:

    def __init__(self, DataBaseObject):
        self.G      = nx.DiGraph()
        self.object = DataBaseObject
        self.G.add_node(self.get_nodeId(self.object), color='purple')  # Use the name of the object as the node ID
        
    def add_node(self, child_object, **attributes):
        nodeId_child  = self.get_nodeId(child_object)
        self.G.add_node(nodeId_child, **attributes)

    def add_edge(self, parent, child_object, **attributes):
        nodeId_parent = self.get_nodeId(parent)
        nodeId_child  = self.get_nodeId(child_object)
        self.G.add_edge(nodeId_parent, nodeId_child ,**attributes)

    def get_nodeId(self, node):
        nodeId = ''
        if node.name :   nodeId = node.name         
        elif node.tag :  nodeId = node.tag
        elif node.title: nodeId = node.title
        return nodeId