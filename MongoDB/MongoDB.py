from pymongo.mongo_client import MongoClient
from pymongo.collection import Collection

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

    def find(self, collection_name: str, query: dict = {}, projection: dict = None):
        collection = self.get_collection(collection_name)        
        return collection.find(query, projection)

    from pymongo.operations import UpdateOne, InsertOne, DeleteOne

    def bulk_write(self, collection_name: str, operations: list):
        collection = self.get_collection(collection_name)
        return collection.bulk_write(operations)

    def update_one(self, collection_name: str, query: dict, update_data: dict):
        collection = self.get_collection(collection_name)
        return collection.update_one(query, {'$set': update_data})

    def delete_one(self, collection_name: str, query: dict):
        collection = self.get_collection(collection_name)
        return collection.delete_one(query)

    def delete_many(self, collection_name: str, query: dict):
        collection = self.get_collection(collection_name)
        return collection.delete_many(query)

    def count_documents(self, collection_name: str, query: dict = {}):
        collection = self.get_collection(collection_name)        
        return collection.count_documents(query)

    def close(self):
        self.client.close()
