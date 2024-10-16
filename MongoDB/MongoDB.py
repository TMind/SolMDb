from pymongo.mongo_client import MongoClient
from pymongo.collection import Collection
from pymongo import UpdateOne, InsertOne, DeleteOne

class MongoDB:
    def __init__(self, db_name: str, host='localhost', port=27017, uri=None):
        if uri:
            self.client = MongoClient(uri)
        else:
            self.client = MongoClient(host, port)
        self.set_db(db_name)

    def set_db(self, db_name):
        self.db = self.client[db_name]

    def get_db_name(self):
        return self.db.name

    def get_collection(self, collection_name: str) -> Collection:
        return self.db[collection_name]
    
    def list_collection_names(self):
        return self.db.list_collection_names()

    def ensure_unique_index(self, collection_name: str, field: str):
        collection = self.get_collection(collection_name)
        collection.create_index([(field, 1)], unique=True)

    def distinct(self, collection_name: str, field: str):
        collection = self.get_collection(collection_name)
        return collection.distinct(field)

    def insert(self, collection_name: str, data: dict):
        collection = self.get_collection(collection_name)
        return collection.insert_one(data).inserted_id
    
    def insert_many(self, collection_name: str, data: list):
        collection = self.get_collection(collection_name)
        #new_data = []
        #existing_ids = [doc['_id'] for doc in collection.find({}, {'_id': 1})]
        #for doc in data:
        #    if '_id' in doc and doc['_id'] not in existing_ids:
        #        new_data.append(doc)
        #if new_data:
        return collection.insert_many(data).inserted_ids

    def upsert(self, collection_name: str, identifier: dict, data: dict):
        collection = self.get_collection(collection_name)
        return collection.update_one(identifier, {'$set': data}, upsert=True)

    def find_one(self, collection_name: str, query: dict):
        collection = self.get_collection(collection_name)
        return collection.find_one(query)

    def find(self, collection_name: str, query: dict = {}, projection: dict = None, batch_size : int = 1000):
        collection = self.get_collection(collection_name)        
        return collection.find(query, projection, batch_size=batch_size)


    def bulk_write(self, collection_name: str, operations: list):
        collection = self.get_collection(collection_name)
        return collection.bulk_write(operations)

    def update_one(self, collection_name: str, query: dict, update_data: dict):
        collection = self.get_collection(collection_name)
        return collection.update_one(query, {'$set': update_data})

    def upsert_many(self, collection_name: str, data: list):
        def check_keys(doc, path="root"):
            if isinstance(doc, dict):
                for key, value in doc.items():
                    if not isinstance(key, str):
                        print(f"Invalid key '{key}' found in path '{path}' in document with '_id': {doc.get('_id')}")
                        return False
                    if not check_keys(value, path + f".{key}"):
                        return False
            elif isinstance(doc, list):
                for index, item in enumerate(doc):
                    if not check_keys(item, path + f"[{index}]"):
                        return False
            return True
        
        # Prepare bulk operations for upsert
        operations = []
        for doc in data:
            # Validate document keys
            if not check_keys(doc):
                print("Skipping document due to invalid keys:", doc)
                continue  # Skip invalid documents

            if '_id' in doc:
                filter_query = {'_id': doc['_id']}
            else:
                # Define another unique identifier or criteria for upsert
                filter_query = {'_id': doc['name'] }
            
            update_doc = {'$set': doc}  # The document to upsert
            
            # Add an upsert operation
            operations.append(UpdateOne(filter_query, update_doc, upsert=True))
        
        if operations:
            # Execute the bulk upsert operation
            result = self.bulk_write(collection_name, operations)
            return {
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
                "upserted_ids": result.upserted_ids
            }
        else:
            return None

    def delete_one(self, collection_name: str, query: dict):
        collection = self.get_collection(collection_name)
        return collection.delete_one(query)

    def delete_many(self, collection_name: str, query: dict):
        collection = self.get_collection(collection_name)
        return collection.delete_many(query)
    
    def drop_collection(self, collection_name: str):
        collection = self.get_collection(collection_name)
        return collection.drop
    
    def drop_database(self):
        return self.client.drop_database(self.db.name)

    def count_documents(self, collection_name: str, query: dict = {}):
        collection = self.get_collection(collection_name)        
        return collection.count_documents(query)

    def close(self):
        self.client.close()
