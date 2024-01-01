from pymongo import MongoClient
from pymongo.collection import Collection

class MongoDB:
    def __init__(self, db_name: str, host='localhost', port=27017):
        self.client = MongoClient(host, port)
        self.set_db(db_name)

    def set_db(self, db_name):
        self.db = self.client[db_name]

    def get_collection(self, collection_name: str) -> Collection:
        return self.db[collection_name]
    
    def ensure_unique_index(self, collection_name: str, field: str):
        collection = self.get_collection(collection_name)
        collection.create_index([(field, 1)], unique=True)

    def insert(self, collection_name: str, data: dict):
        collection = self.get_collection(collection_name)
        return collection.insert_one(data).inserted_id
    
    def upsert(self, collection_name: str, identifier: dict, data: dict):
        collection = self.get_collection(collection_name)
        return collection.update_one(identifier, {'$set': data}, upsert=True)

    def find_one(self, collection_name: str, query: dict):
        collection = self.get_collection(collection_name)
        return collection.find_one(query)

    def find(self, collection_name: str, query: dict = None):
        collection = self.get_collection(collection_name)
        if query is None:
            query = {}
        return collection.find(query)

    def update_one(self, collection_name: str, query: dict, update_data: dict):
        collection = self.get_collection(collection_name)
        return collection.update_one(query, {'$set': update_data})

    def delete_one(self, collection_name: str, query: dict):
        collection = self.get_collection(collection_name)
        return collection.delete_one(query)

    def delete_many(self, collection_name: str, query: dict):
        collection = self.get_collection(collection_name)
        return collection.delete_many(query)

    def count_documents(self, collection_name: str, query: dict = None):
        collection = self.get_collection(collection_name)
        if query is None:
            query = {}
        return collection.count_documents(query)

    def close(self):
        self.client.close()
