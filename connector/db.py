import datetime
import hashlib
import json
from abc import ABCMeta

from bson.objectid import ObjectId
from gridfs import GridFS
from pymongo import MongoClient

from connector import APP_ROOT

"""This db module contains database object for gathering data from a mongo db. It also contains related model classes
like Video and Mapping for handling db data more easy.
"""


class BaseDbo(metaclass=ABCMeta):
    """ Base class for all dbos. The base class initializes the connection to a mongo db server and provides the
    database selected to the subclasses.
    The base class could handle to different databsese:
    - internal: contains connector specific collections
    - external: contains collections for retrieving video metadata
    """

    def __init__(self, use_external_db=False):
        """ reads the connector configuration to establish a connection to the configured mongo db server
        and database

        :param use_external_db: use the external or internal databse
        """
        with open(APP_ROOT + '/config/connector.json') as file:
            self.config = json.loads(file.read())
        mongo_url = self.config['source' if use_external_db else 'internal']['mongodb']
        mongo_db = self.config['source' if use_external_db else 'internal']['database']
        self.database = MongoClient(mongo_url)[mongo_db]


class GridFsDbo(BaseDbo):

    def __init__(self):
        super().__init__(use_external_db=True)

    def image_by_id(self, image_id):
        fs = GridFS(self.database)
        try:
            return fs.get(image_id)
        except Exception:
            return fs.get(ObjectId(image_id))


class InternalConnectorDbo(BaseDbo):
    """Class to encapsulate access to the internal mongo db. This database contains users, mapping configuration and
    error messages.
    """

    def __init__(self):
        """Creates a new mongo client and retrieves the user and mapping collection."""
        super().__init__()
        self.user_collection = self.database[self.config['internal']['user_collection']]
        self.mapping_collection = self.database[self.config['internal']['mapping_collection']]

    def user_by_name(self, username):
        """Takes the user_collection and checks if a user with the given name exists. If true the func will return a
        dict with the corresponsing user data, otherwise none.

        :param username: name of the user
        :return: user dict or none
        """
        return self.user_collection.find_one({'username': username})

    def mapping_by_category_id(self, category_id):
        """Searches for  the matching category id in the mongo db. Returns a mapping model that contains the catgory id,
        a target platform and a target id. The target id is eg. a youtube channel id.

        :param category_id: category id to map
        :return: Mapping
        """
        raw_mapping = self.mapping_collection.find_one({'category_id': category_id})
        if raw_mapping is not None:
            return Mapping(raw_mapping['category_id'], raw_mapping['target_platform'], raw_mapping['target_id'])
        return None

    def mappings(self):
        """ Returns all mappings from the internal databse."""
        results = self.mapping_collection.find()
        mappings = [Mapping(mapping['category_id'], mapping['target_platform'], mapping['target_id']) for mapping in
                    results]
        return mappings

    def users(self):
        """ Returns all users from the internal databse."""
        return self.user_collection.find()

    def create_mapping(self, target_id, target_platform, category_id):
        """ Creates a new mapping."""
        self.mapping_collection.insert_one({
            'target_id': target_id,
            'target_platform': target_platform,
            'category_id': category_id
        })

    def delete_mapping_by_category_id(self, category_id):
        """ Deletes a mapping by category."""
        self.mapping_collection.delete_one({'category_id': category_id})

    def create_user(self, username, password):
        """ Creates a new user."""
        self.user_collection.insert_one({
            'username': username,
            'password_main': password
        })

    def delete_user_by_name(self, username):
        """ Deletes a user by username."""
        self.user_collection.delete_one({'username': username})


class ExternalConnectorDbo(BaseDbo):
    """This database object is responsible for enriching videos with metadata from the content database (mongo db).
    The video title, description and keywords are taken from the database and a Video instance will be created.
    """

    def __init__(self):
        """Creates the mongo db client required to retrieve video metadata and saves the collection as
        an instance variable.
        """
        super().__init__(use_external_db=True)
        mongo_collection = self.config['source']['collection']
        collection = self.database[mongo_collection]
        self.collection = collection

    def video_metadata_by_video_id(self, video_id):
        """Takes a video id and looks it up in the specified database. All required metadata will be read from
        the database:
        - title, description, keywords, downloadUrl.
        The download url is the link where the connector could download the binaries of the specified video.
        The binaries are required in order to upload the video to the target platform.
        :param video_id: video id required to retrieve metadata
        :return: video with metadata
        """

        asset = self.collection.find_one({'sourceId': video_id})
        if 'categoryIds' in asset:
            return Video(asset['name'], asset['text'], None, asset['downloadUrl'], asset['categoryIds'], asset['tags'].split(','), asset['imageid'])
        else:
            return Video(asset['name'], asset['text'], None, asset['downloadUrl'])


class Video(object):
    """This is just a data container. It keeps the title, description, keywords and the download url for a single
    video id. Those information are required to upload a video to a target platform.
    """

    def __init__(self, title, description, keywords, download_url, category_ids='', tags=list(), image_id=None):
        """Just sets the required parameter (metadata) of the video.

        :param title: title of the video
        :param description: description of the video
        :param keywords: keywords comma separated
        :param download_url: url to the binary source of the video
        :param category_ids: category ids as array
        """
        self.title = title
        self.description = description
        self.keywords = keywords
        self.download_url = download_url
        self.category_ids = category_ids.split(',')
        self.tags = tags
        self.image_id = image_id


class Mapping(object):
    """Represents a mapping between a category id and a target id. The target id is the channel / graph to upload
    a video to.
    """

    def __init__(self, category_id, target_platform, target_id):
        """Creates / sets the required mapping attributes.

        :param category_id: category id (search key)
        :param target_platform: youtube / facebook etc
        :param target_id: eg. youtube channel id
        """
        self.category_id = category_id
        self.target_platform = target_platform
        self.target_id = target_id


class MessageDbo(BaseDbo):
    """ A message contains information about the triggered upload. It's used to
    log if an upload was successful or not.
    """

    def __init__(self):
        """ Initializes the corresponding mongo collection for crud messages."""
        super().__init__()
        mongo_collection = self.config['internal']['message_collection']
        collection = self.database[mongo_collection]
        self.collection = collection

    def add_upload_error(self, video_id, video_title, error_message):
        """ Adds an error message to the collection if the upload of a video failed."""
        self.collection.insert_one({
            'video_id': video_id,
            'video_title': video_title,
            'error_message': error_message,
            'timestamp': datetime.datetime.now(),
            'type': 'error'
        })

    def add_upload_success(self, video_id, video_title):
        """ Adds a success message if the upload of a video succeeded."""
        self.collection.insert_one({
            'video_id': video_id,
            'video_title': video_title,
            'timestamp': datetime.datetime.now(),
            'type': 'success'
        })

    def messages(self):
        """ Returns all messages from the internal database. (collection)"""
        messages = self.collection.find()
        msg_list = list()
        for message in messages:
            msg_list.append(Message(message['_id'], message['video_id'], message['video_title'], message['timestamp'],
                                    message['type']))
        return msg_list

    def message(self, msg_id):
        """ Returns a single message by id."""
        msg = self.collection.find_one({'_id': ObjectId(msg_id)})
        return Message(msg['_id'], msg['video_id'], msg['video_title'], msg['timestamp'], msg['type'],
                       msg['error_message'] if 'error_message' in msg else None)


class Message(object):
    """ The message class is just a data container for holding message information. (Error and success)"""

    def __init__(self, obj_id, video_id, video_title, timestamp, msg_type, error_msg=None):
        """ Initializes the object with the given message data.

        :param obj_id: id of the message
        :param video_id: id of the video to upload (this is the external id
        :param video_title: title of the video
        :param timestamp: upload timestamp
        :param msg_type: could be eather success or error
        :param error_msg: if the message is an error this will contain the error message
        """
        self.obj_id = obj_id
        self.video_id = video_id
        self.video_title = video_title
        self.timestamp = timestamp
        self.msg_type = msg_type
        self.error_msg = error_msg


class RegistryDbo(BaseDbo):
    """ Manages registry entries. A registry entry is used to check if a video has already been uploaded."""

    def __init__(self):
        """ Creates a new connection to the registry collection."""
        super().__init__()
        mongo_collection = self.config['internal']['registry_collection']
        collection = self.database[mongo_collection]
        self.collection = collection

    def preregister_upload_in_progres(self, video_id):
        if not self.is_registered(video_id):
            self.collection.insert_one({
                '_id': video_id,
                'status': 'uploading',
                'hashcode': ''
            })

    def register(self, video_id, yt_video_id, video_metadata):
        """ Registers a video upload. The id of a registry entry is the external video id."""
        md5 = self.create_hashcode_from_video_metadata(video_id, video_metadata)
        self.collection.update_one(
            {'_id': video_id},
            {
                '$set': {
                    'yt_video_id': yt_video_id,
                    'status': 'uploaded',
                    'hashcode': md5.digest()
                }
            }
        )

    @staticmethod
    def create_hashcode_from_video_metadata(video_id, video_metadata):
        """ Determines the hashcode for videometadata.
        The hashcode consits of the video keywords, title, description, category
        and the video id (from kaltura). The hash is used to check if
        an already uploaded video hash changes on the target platform.
        In this case the connector should not upload the video.
        """
        keywords = video_metadata['keywords']
        title = video_metadata['title']
        description = video_metadata['description']
        category = video_metadata['category']
        md5 = hashlib.md5()
        md5.update(b"%s%s%s%s%s" % (bytes(video_id.encode()), bytes(str(keywords).encode()), bytes(title.encode()), bytes(description.encode()), bytes(str(category).encode())))
        return md5

    def youtube_id_by_video_id(self, video_id):
        """ Returns the matching youtube video if for the given external video id."""
        video = self.collection.find_one({'_id': video_id})
        if video is not None:
            return video['yt_video_id']
        return None

    def is_registered(self, video_id):
        """ Checks if the given external video id is already registerd."""
        result = self.collection.find_one({'_id': video_id})
        if result is not None and result['status'] != 'uploading':
            return True
        return False

    def is_uploading(self, video_id):
        result = self.collection.find_one({'_id': video_id})
        return result is not None and result['status'] == 'uploading'

    def registry(self):
        """ Returns all registry entries."""
        return self.collection.find()


def change_status_of_process():
    pass

