import hashlib
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


class RegistryModel(object):
    def __init__(self):
        self.registry_id = None
        self.video_id = None
        self.category_id = None
        self.status = None
        self.intermediate_state = None
        self.message = None
        self.target_platform = None
        self.target_platform_video_id = None
        self.mapping_id = None

    def set_state_and_persist(self, state):
        self.status = state
        self._persist()

    def set_intermediate_state_and_persist(self, state):
        self.intermediate_state = state
        self._persist()

    def _persist(self):
        collection = MongoDbFactory.connector_registry_collection()
        try:
            collection.save(self._to_dict())
        except Exception as e:
            raise Exception('Cannot update state of registry item with id %s.' % self.registry_id) from e

    def _to_dict(self):
        return dict(
            _id=self.registry_id,
            videoId=self.video_id,
            categoryId=self.category_id,
            status=self.status,
            intermediateState=self.intermediate_state,
            message=self.message,
            targetPlatform=self.target_platform,
            targetPlatformVideoId=self.target_platform_video_id,
            mappingId=self.mapping_id
        )

    @classmethod
    def create_from_registry_id(cls, registry_id):
        collection = MongoDbFactory.connector_registry_collection()
        try:
            registry_obj = collection.find_one({'_id': registry_id})
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
            raise Exception('Cannot create registry model for registry id %s.' % registry_id) from e


class VideoModel(object):
    def __init__(self):
        self.title = None
        self.description = None
        self.keywords = None
        self.filename = None
        self.download_url = None
        self.image_id = None
        self.hash_code = None

    @classmethod
    def create_from_video_id(cls, video_id):
        collection = MongoDbFactory.assets_collection()
        try:
            video_dict = collection.find_one({'sourceId': video_id})
            video = cls()
            video.title = video_dict['name']
            video.description = video_dict['text']
            video.keywords = video_dict['tags'].split(',') if video_dict['tags'] else []
            video.filename = '%s.mpeg' % video_id
            video.download_url = video_dict['downloadUrl']
            video.image_id = video_dict['image_id'] if 'image_id' in video_dict else None
            video_hash_code = hashlib.md5()
            video_hash_code.update(bytes(video.title))
            video_hash_code.update(bytes(video.description))
            video_hash_code.update(bytes(str(video.keywords)))
            video_hash_code.update(bytes(video.filename))
            video_hash_code.update(bytes(video.download_url))
            video_hash_code.update(bytes(video.image_id))
            video.hash_code = video_hash_code.digest()
            return video
        except Exception as e:
            raise Exception('Cannot retrieve video with id %s from asset collection.' % video_id) from e
