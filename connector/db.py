import os

from pymongo import MongoClient

from config import CONNECTOR_MONGO_DB, ASSET_MONGO_DB, CONNECTOR_DB, CONNECTOR_REGISTRY, CONNECTOR_MAPPINGS, ASSET_DB, ASSETS


class MongoDbFactory(object):
    @staticmethod
    def _mongo_connection_url(system):
        if system == 'internal':
            return CONNECTOR_MONGO_DB if 'CONNECTOR_MONGO_DB' not in os.environ else os.environ['CONNECTOR_MONGO_DB']
        return ASSET_MONGO_DB if 'ASSET_MONGO_DB' not in os.environ else os.environ['ASSET_MONGO_DB']

    @staticmethod
    def _create_mongo_db_client_for_system(system):
        url = MongoDbFactory._mongo_connection_url(system)
        return MongoClient(url)

    @staticmethod
    def connector_registry_collection():
        return MongoDbFactory._create_mongo_db_client_for_system('internal')[CONNECTOR_DB][CONNECTOR_REGISTRY]

    @staticmethod
    def connector_mappings_collection():
        return MongoDbFactory._create_mongo_db_client_for_system('internal')[CONNECTOR_DB][CONNECTOR_MAPPINGS]

    @staticmethod
    def assets_collection():
        return MongoDbFactory._create_mongo_db_client_for_system('external')[ASSET_DB][ASSETS]
