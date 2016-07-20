import os

from bson import ObjectId
from commonspy.logging import log_error
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


class RegistryModel(object):
    def __init__(self):
        self.registry_id = None
        self.video_id = None
        self.category_id = None
        self.status = None
        self.message = None
        self.target_platform = None
        self.target_platform_video_id = None
        self.mapping_id = None

    @classmethod
    def create_from_registry_id(cls, registry_id):
        collection = MongoDbFactory.connector_registry_collection()
        try:
            registry_obj = collection.find_one({'_id': ObjectId(registry_id)})
            obj = cls()
            obj.registry_id = registry_id
            obj.video_id = registry_obj['videoId']
            obj.category_id = registry_obj['categoryId']
            obj.status = registry_obj['status']
            obj.message = registry_obj['message']
            obj.target_platform = registry_obj['targetPlatform']
            obj.target_platform_video_id = registry_obj['targetPlatformVideoId']
            obj.mapping_id = registry_obj['mappingId']
            return obj
        except Exception as e:
            log_error('Cannot create registry model for registry id %s.' % registry_id)
