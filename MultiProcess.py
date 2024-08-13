from email import message
from itertools import accumulate
from GlobalVariables import global_vars as gv
from multiprocessing import Pool, cpu_count  
from pymongo.operations import UpdateOne  
from CardLibrary import Fusion, FusionData  
from MongoDB.DatabaseManager import DatabaseManager  
from MyGraph import MyGraph  
import networkx as nx  
  
class MultiProcess:  
    def __init__(self, username, data, chunk_size=100):          
        self.num_items = len(data)  
        self.num_processes = min(self.num_items, cpu_count())  
        self.data = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]  
        self.username = username
        gv.username = username
  
    def init_worker(self):  
        global dbmgr  
        gv.username = self.username
        dbmgr = DatabaseManager(self.username, force_new=True)          
        #print(f"Initialized worker with username: {self.username} , gv.username: {gv.username}")
  
    def run(self):  
        accumulated = 0
        gv.update_progress('MultiProcess Fusions', value = 0, total = self.num_items, message = 'Fusioning Decks')  
        with Pool(processes=self.num_processes, initializer=self.init_worker) as pool:  
            for chunk_size in pool.imap_unordered(create_fusion, self.data):  
                accumulated += chunk_size
                gv.update_progress('MultiProcess Fusions', value = chunk_size, message = f'Fusioning Decks {accumulated}/{self.num_items}')  

def create_graph_for_object(object):
    # Graph creation
    objectGraph = MyGraph()
    objectGraph.create_graph_children(object)
    object.data.node_data = objectGraph.node_data
    
    # Convert the graph to a dictionary
    objectGraphDict = nx.to_dict_of_dicts(objectGraph.G)
    object.data.graph = objectGraphDict
    #print(f"object.data.graph: {object.data.graph}")
    #print(f"object.data.node_data: {object.data.node_data}")
    
    return object  
  
def create_fusion(dataChunk):  
    global dbmgr
    operations = []  
    for decks in dataChunk:  
        deck1, deck2 = decks  
        if deck1['faction'] != deck2['faction']:  
            fusionName = f"{deck1['name']}_{deck2['name']}"  
            fusionId = fusionName  
            fusionDeckNames = [deck1['name'], deck2['name']]  
            fusionBornIds = [deck1['forgebornId'], deck2['forgebornId']]  
            fusionFaction = deck1['faction']
            fusionCrossFaction = deck2['faction']
            fusionObject = Fusion(FusionData(fusionName, fusionDeckNames, fusionFaction, fusionCrossFaction, deck1['forgebornId'], fusionBornIds, fusionId))  
            #fusionData = fusionObject.to_data()  
             
            fusionObject = create_graph_for_object(fusionObject)
            fusionData = fusionObject.to_data()   
            #fusionGraph = MyGraph()  
            #fusionGraph.create_graph_children(fusionObject)  
            #fusionGraphDict = nx.to_dict_of_dicts(fusionGraph.G) 
            #fusionData['graph'] = fusionGraphDict  
            #fusionData['node_data'] = fusionGraph.node_data  
  
            operations.append(UpdateOne({'_id': fusionId}, {'$set': fusionData}, upsert=True))  
  
    if operations:
        dbmgr.bulk_write('Fusion', operations)  
    return len(dataChunk)  
  
