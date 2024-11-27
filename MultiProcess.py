import os
import logging
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context, Manager
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.operations import UpdateOne
from GlobalVariables import global_vars as gv
from CardLibrary import Fusion, FusionData
from MyGraph import MyGraph
import time

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def create_graph_for_fusions(fusion_object):
    try:
        logging.debug(f"Creating graph for object: {fusion_object}.")
        # Graph creation
        objectGraph = MyGraph()
        objectGraph.create_graph_children(fusion_object)
        fusion_object.data.node_data = objectGraph.node_data
        fusion_object.data.combo_data = objectGraph.combo_data

        # Convert the graph to a dictionary
        objectGraphDict = objectGraph.to_dict()
        fusion_object.data.graph = objectGraphDict

        logging.debug(f"Graph created for object: {fusion_object}.")
        return fusion_object
    except Exception as e:
        logging.error(f"Error creating graph for object: {e}")
        raise

def create_fusions(username, data_chunk, progress):
    try:
        logging.info(f"Creating fusions for data chunk with {len(data_chunk)} items.")

        # Initialize MongoDB connection only once per worker process
        if not hasattr(create_fusions, "_db_client"):
            create_fusions._db_client = MongoClient(os.getenv('MONGODB_URI'))
            create_fusions._db = create_fusions._db_client[username]
            logging.info(f"Opened MongoDB connection for worker process for database: {username}")

        # Fusion operations
        operations = []
        successful_fusions = 0
        batch_size = 100

        for decks in data_chunk:
            deck1, deck2 = decks
            if deck1['faction'] != deck2['faction']:
                try:
                    fusionName = f"{deck1['name']}_{deck2['name']}"
                    fusionId = ''
                    fusionDeckNames = [deck1['name'], deck2['name']]
                    fusionBornIds = [deck1['forgebornId'], deck2['forgebornId']]
                    fusionFaction = deck1['faction']
                    fusionCrossFaction = deck2['faction']
                    logging.debug(f"Creating Fusion object for {fusionName}.")

                    fusionObject = Fusion(FusionData(fusionName, fusionDeckNames, fusionFaction, fusionCrossFaction, deck1['forgebornId'], fusionBornIds, fusionId))

                    # Create a graph representation
                    fusionObject = create_graph_for_fusions(fusionObject)
                    fusionData = fusionObject.to_data()

                    # Store the operation to be performed in MongoDB
                    operations.append(UpdateOne({'_id': fusionName}, {'$set': fusionData}, upsert=True))
                    successful_fusions += 1

                except Exception as e:
                    logging.error(f"Error creating fusion for decks {deck1['name']} and {deck2['name']}: {e}")

                # Write in batches
                if len(operations) >= batch_size:
                    try:
                        create_fusions._db['Fusion'].bulk_write(operations)
                        progress.value += len(operations)  # Directly update the progress value
                        logging.info(f"Written {len(operations)} fusions to the database.")
                        operations = []
                    except PyMongoError as e:
                        logging.error(f"Error writing batch to database: {e}")

        # Write remaining operations
        if operations:
            try:
                create_fusions._db['Fusion'].bulk_write(operations)
                progress.value += len(operations)  # Directly update the progress value
                logging.info(f"Written {len(operations)} remaining fusions to the database.")
            except PyMongoError as e:
                logging.error(f"Error writing remaining batch to database: {e}")

        return successful_fusions
    except Exception as e:
        logging.error(f"Error creating fusion: {e}")
        raise

class MultiProcess:
    def __init__(self, username, data):
        self.num_items = len(data)
        self.num_processes = min(self.num_items, os.cpu_count())
        self.data = [data[i::self.num_processes] for i in range(self.num_processes)]  # Split into equal chunks for each worker
        self.username = os.getenv('SFF_USERNAME', username)

        if hasattr(gv.myDB, 'mdb'):
            gv.myDB.close_database()
            gv.myDB = None
            logging.info("Closed the existing MongoDB connection before starting multiprocessing.")

        gv.update_progress('MultiProcess Fusions', value=0, total=self.num_items, message='Fusioning Decks')
        logging.info(f"Initialized MultiProcess with {self.num_items} items, using {self.num_processes} processes.")

    def run(self):
        accumulated = 0
        try:
            with Manager() as manager:
                progress = manager.Value('i', 0)
                with ProcessPoolExecutor(max_workers=self.num_processes, mp_context=get_context('fork')) as executor:
                    logging.info("Submitting tasks to worker processes.")
                    futures = [executor.submit(create_fusions, self.username, data_chunk, progress) for data_chunk in self.data]

                    while True:
                        # Update progress periodically
                        current_progress = progress.value
                        if current_progress > accumulated:
                            accumulated = current_progress
                            gv.update_progress('MultiProcess Fusions', value=accumulated, set=True, message=f'Fusioning {accumulated} Decks')
                            logging.info(f"Updated progress: {accumulated} decks fused.")

                        # Break the loop if all futures are done
                        if all(f.done() for f in futures):
                            logging.info("All worker processes have completed.")
                            break

                        time.sleep(1)  # Sleep for a short time to avoid busy-waiting

                # Ensure that progress is fully updated once all workers are done
                final_progress = progress.value
                gv.update_progress('MultiProcess Fusions', value=final_progress, message=f'Fusioning complete: {final_progress} Decks')
                logging.info(f"Final progress updated: {final_progress} decks fused.")

        except Exception as e:
            logging.error(f"Error running multiprocessing: {e}")