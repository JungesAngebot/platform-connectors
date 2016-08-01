import hashlib
import os
import traceback
import uuid

from bson import ObjectId
from commonspy.logging import log_error, log_debug
from gridfs import GridFS
from pymongo import MongoClient

from config import CONNECTOR_MONGO_DB, ASSET_MONGO_DB, CONNECTOR_DB, CONNECTOR_REGISTRY, CONNECTOR_MAPPINGS, ASSET_DB, \
    ASSETS
from connector import external_client, internal_client


class MongoDbFactory(object):
    @staticmethod
    def _mongo_connection_url(system):
        if system == 'internal':
            return CONNECTOR_MONGO_DB if 'CONNECTOR_MONGO_DB' not in os.environ else os.environ['CONNECTOR_MONGO_DB']
        return ASSET_MONGO_DB if 'ASSET_MONGO_DB' not in os.environ else os.environ['ASSET_MONGO_DB']

    @staticmethod
    def _create_mongo_db_client_for_system(system):
        return internal_client if system == 'internal' else external_client

    @staticmethod
    def connector_registry_collection():
        log_debug('retrieving registry collection...')
        return MongoDbFactory._create_mongo_db_client_for_system('internal')[CONNECTOR_DB][CONNECTOR_REGISTRY]

    @staticmethod
    def connector_mappings_collection():
        log_debug('retrieving mappings collection...')
        return MongoDbFactory._create_mongo_db_client_for_system('internal')[CONNECTOR_DB][CONNECTOR_MAPPINGS]

    @staticmethod
    def assets_collection():
        log_debug('retrieving assets collection')
        return MongoDbFactory._create_mongo_db_client_for_system('external')[ASSET_DB][ASSETS]

    @staticmethod
    def einszwo_internal_database():
        log_debug('creating connection to einszwo_internal database in mongodb...')
        return MongoDbFactory._create_mongo_db_client_for_system('external')[ASSET_DB]


class RegistryModel(object):
    db_factory = MongoDbFactory

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
        self.video_hash_code = None

    def update_video_hash_code(self, hash_code):
        self.video_hash_code = hash_code
        self._persist()

    def set_state_and_persist(self, state):
        self.status = state
        self._persist()

    def set_intermediate_state_and_persist(self, state):
        self.intermediate_state = state
        self._persist()

    def _persist(self):
        collection = RegistryModel.db_factory.connector_registry_collection()
        try:
            collection.save(self._to_dict())
        except Exception as e:
            traceback.print_exc()
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
            mappingId=self.mapping_id,
            video_hash_code=self.video_hash_code
        )

    @classmethod
    def create_from_registry_id(cls, registry_id):
        log_debug('Creating registry model from registry id %s.' % registry_id)
        collection = RegistryModel.db_factory.connector_registry_collection()
        try:
            registry_obj = collection.find_one({'_id': registry_id})
            log_debug('Found matching registry entry...')
            obj = cls()
            obj.registry_id = registry_id
            obj.video_id = registry_obj['videoId']
            obj.category_id = registry_obj['categoryId']
            obj.status = registry_obj['status']
            obj.message = registry_obj['message']
            obj.target_platform = registry_obj['targetPlatform']
            obj.target_platform_video_id = registry_obj[
                'targetPlatformVideoId'] if 'targetPlatformVideoId' in registry_obj else ''
            obj.mapping_id = registry_obj['mappingId']
            obj.intermediate_state = registry_obj['intermediateState'] if 'intermediateState' in registry_obj else ''
            obj.video_hash_code = registry_obj['video_hash_code'] if 'video_hash_code' in registry_obj else ''
            log_debug('Loaded registry entry with id %s successfully.' % registry_id)
            return obj
        except Exception as e:
            traceback.print_exc()
            log_error(e.__traceback__)
            raise Exception('Cannot create registry model for registry id %s.' % registry_id) from e


class VideoModel(object):
    db_factory = MongoDbFactory

    def __init__(self):
        self.title = None
        self.description = None
        self.keywords = None
        self.filename = None
        self.download_url = None
        self.image_id = None
        self.hash_code = None
        self.image_filename = None

    @classmethod
    def create_from_video_id(cls, video_id):
        log_debug('Creating video model from id %s.' % video_id)
        collection = VideoModel.db_factory.assets_collection()
        try:
            video_dict = collection.find_one({'sourceId': video_id})
            log_debug('Found matching database entry.')
            video = cls()
            video.title = video_dict['name'] if 'name' in video_dict else ''
            video.description = video_dict['text'] if 'text' in video_dict else ''
            video.keywords = video_dict['tags'].split(',') if 'tags' in video_dict and video_dict['tags'] else []
            video.keywords = [keyword.strip() for keyword in video.keywords]
            video.download_url = video_dict['flavourSourceUrl']
            video.image_id = video_dict['imageid'] if 'imageid' in video_dict else None
            video_hash_code = hashlib.md5()
            video_hash_code.update(bytes(video.title.encode('UTF-8')))
            video_hash_code.update(bytes(video.description.encode('UTF-8')))
            video.hash_code = video_hash_code.hexdigest()
            video.filename = '%s-%s.mpeg' % (video_id, str(uuid.uuid4()))
            video.image_filename = '%s-%s.png' % (video_id, str(uuid.uuid4()))
            log_debug('Loaded video model with id %s successfully.' % video_id)
            return video
        except Exception as e:
            traceback.print_exc()
            log_error(e.__traceback__)
            raise Exception('Cannot retrieve video with id %s from asset collection.' % video_id) from e


def persist_video_image_on_disk(video_model: VideoModel):
    log_debug('Going to store thumbnail with id %s on disk...' % video_model.image_id)

    image_id = video_model.image_id
    database = MongoDbFactory.einszwo_internal_database()
    try:
        fs = GridFS(database)
        try:
            result = fs.get(image_id)
        except Exception:
            result = fs.get(ObjectId(image_id))
        with open(video_model.image_filename, 'wb') as file:
            file.write(result.read())
    except Exception as e:
        traceback.print_exc()
        video_id = video_model.image_id
        log_error(e.__traceback__)
        raise Exception('Cannot read image with id %s from video with id %s. GridFS connection not working' % (
            image_id, video_id)) from e


class MappingModel(object):
    db_factory = MongoDbFactory

    def __init__(self):
        self._id = None
        self.target_id = None
        self.target_platform = None
        self.category_id = None

    @classmethod
    def create_from_mapping_id(cls, mapping_id):
        collection = MappingModel.db_factory.connector_mappings_collection()
        try:
            mapping_dict = collection.find_one({'_id': ObjectId(mapping_id)})
            mapping = cls()
            mapping.target_id = mapping_dict['target_id']
            mapping.target_platform = mapping_dict['target_platform']
            mapping.category_id = mapping_dict['category_id']
            return mapping
        except Exception as e:
            log_error(e.__traceback__)
            traceback.print_exc()
            log_error('Cannot retrieve mapping with id %s from mapping collection.' % mapping_id)
            raise Exception('Cannot retrieve video with id %s from asset collection.' % mapping_id) from e
