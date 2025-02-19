import os
import logging
from concurrent.futures import ProcessPoolExecutor, wait
from multiprocessing import get_context, Manager
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.operations import UpdateOne
from GlobalVariables import global_vars as gv
from CardLibrary import Fusion, FusionData
from ObjectProcessor import ObjectProcessor
import time, math

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def create_fusions(username, data_chunk, progress):
    logging.info(f"Worker {os.getpid()} started processing {len(data_chunk)} decks.")  # Add worker PID
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
        batch_size = 200

        for decks in data_chunk:
            deck1, deck2 = decks
            if deck1['faction'] != deck2['faction']:
                try:
                    fusionName = f"{deck1['name']}_{deck2['name']}"
                    fusionId = ''
                    fusionDeckNames = [ {'name' :  deck1['name'] },  {'name' : deck2['name']} ] 
                    fusionBornIds = [deck1['forgebornId'], deck2['forgebornId']]
                    fusionFaction = deck1['faction']
                    fusionCrossFaction = deck2['faction']
                    logging.debug(f"Creating Fusion object for {fusionName}.")

                    fusionObject = Fusion(FusionData(fusionName, fusionDeckNames, fusionFaction, fusionCrossFaction, deck1['forgebornId'], fusionBornIds, fusionId))

                    ObjectProcessor.process_object_for_db(fusionObject)                                            
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
                        progress.increment(len(operations))  # Directly update the progress value
                        logging.info(f"Written {len(operations)} fusions to the database.")
                        operations = []
                    except PyMongoError as e:
                        logging.error(f"Error writing batch to database: {e}")

        # Write remaining operations
        if operations:
            try:
                create_fusions._db['Fusion'].bulk_write(operations)
                progress.increment(len(operations))  # Directly update the progress value
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

        gv.progress_manager.update_progress('MultiProcess Fusions', value=0, total=self.num_items, message='Fusioning Decks')
        logging.info(f"Initialized MultiProcess with {self.num_items} items, using {self.num_processes} processes.")



    def run(self, use_multiprocessing=True):
        accumulated = 0
        timeout_seconds = 300  # 5-minute timeout
        start_time = time.time()

        # ✅ Close existing MongoDB connection before forking
        if hasattr(gv.myDB, 'mdb'):
            gv.myDB.close_database()  
            gv.myDB = None
            logging.info("Closed MongoDB connection before starting multiprocessing.")

        try:
            if use_multiprocessing: 
                with Manager() as manager:
                    progress = ProgressWrapper(manager.Value('i', 0))

                    with ProcessPoolExecutor(max_workers=self.num_processes, mp_context=get_context('spawn')) as executor:
                        logging.info("Submitting tasks to worker processes.")
                        futures = [executor.submit(create_fusions, self.username, data_chunk, progress) for data_chunk in self.data]

                        # # ✅ **Wait until all futures are completed before continuing**
                        # logging.info("Waiting for all worker processes to finish...")
                        # wait(futures, timeout=timeout_seconds)  # ✅ **Blocks until all processes are done**
                        # logging.info("All worker processes have completed.")

                        # # ✅ Ensure progress updates after all processes finish
                        # final_progress = progress.get()
                        # gv.progress_manager.update_progress('MultiProcess Fusions', value=final_progress, message=f'Fusioning complete: {final_progress} Decks')
                        # logging.info(f"Final progress updated: {final_progress} decks fused.")

                        accumulated = 0
                        logging.info("Waiting for all worker processes to finish...")
                                                
                        while not all(f.done() for f in futures):  # Check if all processes are done
                            current_progress = progress.get()
                            if current_progress > accumulated:
                                accumulated = current_progress
                                gv.progress_manager.update_progress(
                                    'MultiProcess Fusions',
                                    value=accumulated,
                                    set=True,
                                    message=f'Fusioning {accumulated} Decks'
                                )
                                logging.info(f"Updated progress: {accumulated} decks fused.")

                            time.sleep(1)  # ✅ Avoid busy-waiting

                        # ✅ **Ensure all futures are actually done before continuing**
                        wait(futures, timeout=timeout_seconds)  # This ensures no process is left running
                        logging.info("All worker processes have completed.")

                        # ✅ Ensure progress updates once all processes finish
                        final_progress = progress.get()
                        gv.progress_manager.update_progress('MultiProcess Fusions', value=final_progress, message=f'Fusioning complete: {final_progress} Decks')
                        logging.info(f"Final progress updated: {final_progress} decks fused.")

            else:
                # ✅ **SINGLE-PROCESS MODE (FOR DEBUGGING)**
                logging.info("Running in single-process mode for debugging.")
                progress = ProgressWrapper(0)

                for data_chunk in self.data:
                    amount = create_fusions(self.username, data_chunk, progress)
                    progress.increment(amount)
                    num = progress.get()

                    gv.progress_manager.update_progress('MultiProcess Fusions', value=num, set=True, message=f'Fusioning {num} Decks')
                    logging.info(f"Updated progress: {num} decks fused.")

                gv.progress_manager.update_progress('MultiProcess Fusions', value=num, message=f'Fusioning complete: {num} Decks')
                logging.info(f"Final progress updated: {num} decks fused.")

        except Exception as e:
            logging.error(f"Error running multiprocessing: {e}")
            
            
    def determine_required_cpus(self, num_items, max_cpus=None, min_items_per_cpu=1000):
        """
        Determines the optimal number of CPUs to use based on the workload.

        Args:
            num_items (int): Total number of items to process.
            max_cpus (int, optional): The upper limit for CPU usage. Defaults to `os.cpu_count()`.
            min_items_per_cpu (int): Minimum number of items per CPU to ensure efficiency.

        Returns:
            int: The number of CPUs that should be used.
        """
        if num_items == 0:
            return 1  # Default to 1 CPU if no items need processing

        available_cpus = max_cpus or os.cpu_count()
        
        # Avoid using more CPUs than available
        max_possible_cpus = min(available_cpus, num_items)  

        # Ensure each CPU gets a reasonable workload
        optimal_cpus = min(max_possible_cpus, math.ceil(num_items / min_items_per_cpu))  

        return max(1, optimal_cpus)  # Ensure at least 1 CPU is always used
            
class ProgressWrapper:
    """ A wrapper to handle both Manager.Value and regular integers safely. """
    def __init__(self, progress):
        self.progress = progress

    def get(self) -> int:
        """Returns the current progress value as an integer."""
        return int(self.progress.value) if hasattr(self.progress, 'value') else int(self.progress)

    def increment(self, amount=1):
        """Safely increments the progress value."""
        if hasattr(self.progress, 'value'):  # It's a Manager.Value
            self.progress.value += amount  # ✅ Remove get_lock()
        else:  # It's a regular integer
            self.progress += amount