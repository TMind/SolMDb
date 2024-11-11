import os
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pymongo import MongoClient
from pymongo.operations import UpdateOne  
from GlobalVariables import global_vars as gv
from CardLibrary import Fusion, FusionData  
from MyGraph import MyGraph  
  
# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
  
class MultiProcess:  
    def __init__(self, username, data, chunk_size=500):          
        self.num_items = len(data)  
        self.num_processes = min(self.num_items, os.cpu_count())  
        self.data = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]  
        self.username = os.getenv('SFF_USERNAME', username)
        if hasattr(gv.myDB, 'mdb'):
            gv.myDB.mdb.close()
            logging.info("Closed the existing MongoDB connection before starting multiprocessing.")
        gv.update_progress('MultiProcess Fusions', value = 0, total = self.num_items, message = 'Fusioning Decks')  
        logging.info(f"Initialized MultiProcess with {self.num_items} items, using {self.num_processes} processes.")
  
    def run(self):  
        accumulated = 0        
        try:
            with ProcessPoolExecutor(max_workers=self.num_processes, mp_context=get_context('fork')) as executor:  
                logging.info("Submitting tasks to worker processes.")
                futures = [executor.submit(create_fusion, self.username, data_chunk) for data_chunk in self.data]
                for future in as_completed(futures):
                    try:
                        chunk_size = future.result()  # Ensure all workers complete
                        accumulated += chunk_size
                        gv.update_progress('MultiProcess Fusions', value=accumulated, message=f'Fusioning {accumulated} Decks')
                        logging.info(f"Worker process completed a task. Accumulated: {accumulated}")
                    except Exception as e:
                        logging.error(f"Error processing future: {e}")
        except Exception as e:
            logging.error(f"Error running multiprocessing: {e}")

def create_graph_for_object(object):
    try:
        logging.debug(f"Creating graph for object: {object}.")
        # Graph creation
        objectGraph = MyGraph()
        objectGraph.create_graph_children(object)
        object.data.node_data = objectGraph.node_data
        object.data.combo_data = objectGraph.combo_data
        
        # Convert the graph to a dictionary
        objectGraphDict = objectGraph.to_dict()
        object.data.graph = objectGraphDict
        
        logging.debug(f"Graph created for object: {object}.")
        return object
    except Exception as e:
        logging.error(f"Error creating graph for object: {e}")
        raise  

def create_fusion(username, data_chunk):  
    try:
        logging.info(f"Creating fusions for data chunk with {len(data_chunk)} items.")
        
        # Lazy initialization of MongoDB connection within each worker process
        if not hasattr(create_fusion, "_db_client"):
            create_fusion._db_client = MongoClient(os.getenv('MONGODB_URI'))
            create_fusion._db = create_fusion._db_client[username]  # Assuming `username` is the database name
            logging.info(f"Opened MongoDB connection for worker process for database: {username}")

        operations = []  
        for decks in data_chunk:  
            deck1, deck2 = decks  
            if deck1['faction'] != deck2['faction']:  
                fusionName = f"{deck1['name']}_{deck2['name']}"  
                fusionId = ''  
                fusionDeckNames = [deck1['name'], deck2['name']]  
                fusionBornIds = [deck1['forgebornId'], deck2['forgebornId']]  
                fusionFaction = deck1['faction']
                fusionCrossFaction = deck2['faction']
                logging.debug(f"Creating Fusion object for {fusionName}.")
                fusionObject = Fusion(FusionData(fusionName, fusionDeckNames, fusionFaction, fusionCrossFaction, deck1['forgebornId'], fusionBornIds, fusionId))  
                
                fusionObject = create_graph_for_object(fusionObject)
                fusionData = fusionObject.to_data()   
                
                operations.append(UpdateOne({'_id': fusionName}, {'$set': fusionData}, upsert=True))  
                logging.debug(f"Fusion object created for {fusionName}.")
      
        # Write operations directly to the database
        if operations:
            create_fusion._db['Fusion'].bulk_write(operations)
            logging.info(f"Written {len(operations)} fusions to the database.")
        return len(data_chunk)
    except Exception as e:
        logging.error(f"Error creating fusion: {e}")
        raise