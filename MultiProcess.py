from GlobalVariables import update_progress, username  
from multiprocessing import Pool, cpu_count  
from pymongo.operations import UpdateOne  
from CardLibrary import Fusion, FusionData  
from MongoDB.DatabaseManager import DatabaseManager  
from MyGraph import MyGraph  
import networkx as nx  
  
class MultiProcess:  
    def __init__(self, data, chunk_size=100):  
        self.func = create_fusion  
        self.num_items = len(data)  
        self.num_processes = min(self.num_items, cpu_count())  
        self.data = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]  
  
    def init_worker(self):  
        global dbmgr  
        dbmgr = DatabaseManager(username, force_new=True)  
  
    def run(self):  
        with Pool(processes=self.num_processes, initializer=self.init_worker) as pool:  
            update_progress('MultiProcess Fusions', 0, self.num_items, 'Fusioning Decks')  
            for chunk_size in pool.imap_unordered(lambda chunk: self.func(chunk, dbmgr), self.data):  
                update_progress('MultiProcess Fusions', chunk_size)  
  
def create_fusion(dataChunk, dbmgr):  
    operations = []  
    for decks in dataChunk:  
        deck1, deck2 = decks  
        if deck1['faction'] != deck2['faction']:  
            fusionName = f"{deck1['name']}_{deck2['name']}"  
            fusionId = fusionName  
            fusionDeckNames = [deck1['name'], deck2['name']]  
            fusionBornIds = [deck1['forgebornId'], deck2['forgebornId']]  
  
            fusionObject = Fusion(FusionData(fusionName, fusionDeckNames, deck1['forgebornId'], fusionBornIds, fusionId))  
            fusionData = fusionObject.to_data()  
  
            fusionGraph = MyGraph()  
            fusionGraph.create_graph_children(fusionObject)  
            fusionGraphDict = nx.to_dict_of_dicts(fusionGraph.G)  
            fusionData['graph'] = fusionGraphDict  
            fusionData['node_data'] = fusionGraph.node_data  
  
            operations.append(UpdateOne({'_id': fusionId}, {'$set': fusionData}, upsert=True))  
  
    if operations:  
        dbmgr.bulk_write('Fusion', operations)  
    return len(dataChunk)  
  
