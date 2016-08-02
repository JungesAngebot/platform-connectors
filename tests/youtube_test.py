import os
import unittest
from unittest import mock

from connector.db import MongoDbFactory, VideoModel, RegistryModel, MappingModel
from connector.youtube import upload_video_to_youtube, update_video_on_youtube, create_metadata_hash, \
    unpublish_video_on_youtube


class CollectionMock(object):
    def find_one(self, query):
        return dict(
            name='videoName',
            text='videoText',
            tags=[],
            downloadUrl='downloadUrl',
            imageid='some_id'
        )


class MappingMock(object):
    def find_one(self, query):
        return dict(
            target_id='1234',
            target_platform='youtube',
            category_id='5678'
        )


class RegistryMock(object):
    def save(self, query):
        pass


def create_test_registry_model():
    registry = RegistryModel()
    registry.mapping_id = '5784e74283446200011bd4f8'
    registry.status = 'notified'
    registry.intermediate_state = 'uploading'
    return registry


def create_test_video_model():
    video = VideoModel()
    video.title = 'Test-Title'
    video.description = 'Test-Description'
    video.keywords = 'test,cool,nice,slow'
    video.download_url = 'url for upload'
    video.filename = 'testfile.mov'
    video.image_filename = os.path.realpath(__file__)

    return video


class MediaUploadMock:
    def __init__(self, *args, **kwargs):
        pass


class ExecCounter:
    count = 0


youtube_client_exec_count = ExecCounter()


class MockYoutubeClient:
    def __init__(self):
        self.exec_count = youtube_client_exec_count

    def json(self):
        return self.json_data

    def contentOwners(self):
        return self

    def list(self, *args, **kwargs):
        return self

    def execute(self):
        self.exec_count.count += 1
        return {'items': [{'id': '1234'}]}

    def videos(self):
        return self

    def insert(self, *args, **kwargs):
        return self

    def next_chunk(self):
        return 200, {'id': '567'}


class MockYoutubeClientWithError(MockYoutubeClient):
    def next_chunk(self):
        return 400, {'error': 'something bad hapens'}


class MockYoutubeUpdateClient(MockYoutubeClient):
    def update(self, *args, **kwargs):
        return self

    def execute(self):
        self.exec_count.count += 1
        return {'items': [{'snippet': {'title': 'Test-Title', 'description': 'Test-Description'},
                           'status': {'privacyStatus': 'public'}}]}


class MockYoutubeUpdateClientWithError(MockYoutubeClient):
    def update(self, *args, **kwargs):
        return self

    def execute(self):
        self.exec_count.count += 1
        raise Exception('Mock')


def mocked_youtube_inst(*args, **kwargs):
    return MockYoutubeClient(), MockYoutubeClient()


def mocked_youtube_inst_with_error_response(*args, **kwargs):
    return MockYoutubeClientWithError(), MockYoutubeClientWithError()


def mocked_youtube_update_inst(*args, **kwargs):
    return MockYoutubeUpdateClient(), MockYoutubeClient()


def mocked_youtube_update_inst_with_error_response(*args, **kwargs):
    return MockYoutubeUpdateClientWithError(), MockYoutubeClient()


class DbFactoryMock(MongoDbFactory):
    @staticmethod
    def assets_collection():
        return CollectionMock()

    @staticmethod
    def connector_mappings_collection():
        return MappingMock()

    @staticmethod
    def connector_registry_collection():
        return RegistryMock()


class YoutubeUploadTest(unittest.TestCase):
    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_inst)
    def test_success_with_thumb(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock
        youtube_client_exec_count.count = 0
        registry = create_test_registry_model()
        video = create_test_video_model()

        upload_video_to_youtube(video, registry)
        self.assertEquals('567', registry.target_platform_video_id)
        self.assertEquals('active', registry.status)
        self.assertEqual(youtube_client_exec_count.count, 1)

    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_inst)
    def test_success_without_thumb(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock

        registry = create_test_registry_model()
        video = create_test_video_model()
        video.image_filename = None

        upload_video_to_youtube(video, registry)
        self.assertEquals('567', registry.target_platform_video_id)
        self.assertEquals('active', registry.status)

    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_inst_with_error_response)
    def test_req_error(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock

        registry = create_test_registry_model()
        video = create_test_video_model()
        video.image_filename = None

        with self.assertRaises(Exception):
            upload_video_to_youtube(video, registry)

    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_inst)
    def test_error_if_platform_id_is_set(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock

        registry = create_test_registry_model()
        registry.target_platform_video_id = '321'
        video = create_test_video_model()

        with self.assertRaises(Exception):
            upload_video_to_youtube(video, registry)

    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_inst)
    def test_error_if_intermediate_state_not_valid(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock

        registry = create_test_registry_model()
        registry.intermediate_state = 'downloading'
        video = create_test_video_model()

        with self.assertRaises(Exception):
            upload_video_to_youtube(video, registry)


class YoutubeUpdateTest(unittest.TestCase):
    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_update_inst)
    def test_success(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock
        youtube_client_exec_count.count = 0

        registry = create_test_registry_model()
        registry.intermediate_state = 'updating'
        registry.target_platform_video_id = '1'
        registry.video_hash_code = create_metadata_hash({'title': 'Test-Title', 'description': 'Test-Description'})
        video = create_test_video_model()

        update_video_on_youtube(video, registry)
        self.assertEqual(youtube_client_exec_count.count, 3)

    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_update_inst)
    def test_error_if_target_platform_video_id_not_set(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock
        youtube_client_exec_count.count = 0

        registry = create_test_registry_model()
        registry.intermediate_state = 'updating'
        registry.target_platform_video_id = None
        registry.video_hash_code = create_metadata_hash({'title': 'Test-Title', 'description': 'Test-Description'})
        video = create_test_video_model()

        with self.assertRaises(Exception):
            update_video_on_youtube(video, registry)

        self.assertEqual(youtube_client_exec_count.count, 0)

    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_update_inst)
    def test_error_if_intermediate_state_wrong(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock
        youtube_client_exec_count.count = 0

        registry = create_test_registry_model()
        registry.intermediate_state = 'downloading'
        registry.target_platform_video_id = '1'
        registry.video_hash_code = create_metadata_hash({'title': 'Test-Title', 'description': 'Test-Description'})
        video = create_test_video_model()

        with self.assertRaises(Exception):
            update_video_on_youtube(video, registry)

        self.assertEqual(youtube_client_exec_count.count, 0)

    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_update_inst_with_error_response)
    def test_error_if_request_error(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock
        youtube_client_exec_count.count = 0

        registry = create_test_registry_model()
        registry.intermediate_state = 'updating'
        registry.target_platform_video_id = '1'
        registry.video_hash_code = create_metadata_hash({'title': 'Test-Title', 'description': 'Test-Description'})
        video = create_test_video_model()

        with self.assertRaises(Exception):
            update_video_on_youtube(video, registry)

        self.assertEqual(youtube_client_exec_count.count, 1)

    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_update_inst)
    def test_do_nothing_if_video_hash_equal_to_registry_hash(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock
        youtube_client_exec_count.count = 0

        registry = create_test_registry_model()
        registry.intermediate_state = 'updating'
        registry.target_platform_video_id = '1'
        registry.video_hash_code = create_metadata_hash({'title': 'Test-Title', 'description': 'Test-Description'})
        video = create_test_video_model()
        video.hash_code = registry.video_hash_code

        update_video_on_youtube(video, registry)
        self.assertEqual(youtube_client_exec_count.count, 0)

    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_update_inst)
    def test_do_nothing_if_remote_hash_not_equal_to_registry_hash(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock
        youtube_client_exec_count.count = 0

        registry = create_test_registry_model()
        registry.intermediate_state = 'updating'
        registry.target_platform_video_id = '1'
        registry.video_hash_code = create_metadata_hash({'title': 'Test-Title2', 'description': 'Test-Description'})
        video = create_test_video_model()

        update_video_on_youtube(video, registry)
        self.assertEqual(youtube_client_exec_count.count, 1)


class YoutubeUnpublishTest(unittest.TestCase):
    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_update_inst)
    def test_success(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock
        youtube_client_exec_count.count = 0

        registry = create_test_registry_model()
        registry.intermediate_state = 'unpublishing'
        registry.target_platform_video_id = '1'
        registry.video_hash_code = create_metadata_hash({'title': 'Test-Title', 'description': 'Test-Description'})
        video = create_test_video_model()

        unpublish_video_on_youtube(video, registry)
        self.assertEqual(youtube_client_exec_count.count, 3)

    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_update_inst)
    def test_error_if_wrong_intermediate_state(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock
        youtube_client_exec_count.count = 0

        registry = create_test_registry_model()
        registry.intermediate_state = 'downloading'
        registry.target_platform_video_id = '1'
        registry.video_hash_code = create_metadata_hash({'title': 'Test-Title', 'description': 'Test-Description'})
        video = create_test_video_model()

        self.assertRaises(Exception, unpublish_video_on_youtube, video, registry);
        self.assertEqual(youtube_client_exec_count.count, 0)

    @mock.patch('builtins.open')
    @mock.patch('connector.youtube.youtube_inst', side_effect=mocked_youtube_update_inst)
    def test_error_if_not_target_platform_video_id_set(self, mock_youtube, mock_open):
        MappingModel.db_factory = DbFactoryMock
        RegistryModel.db_factory = DbFactoryMock
        youtube_client_exec_count.count = 0

        registry = create_test_registry_model()
        registry.intermediate_state = 'unpublishing'
        registry.target_platform_video_id = None
        registry.video_hash_code = create_metadata_hash({'title': 'Test-Title', 'description': 'Test-Description'})
        video = create_test_video_model()

        with self.assertRaises(Exception):
            unpublish_video_on_youtube(video, registry)
