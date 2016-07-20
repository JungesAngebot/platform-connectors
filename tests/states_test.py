import hashlib
import unittest

from connector.db import RegistryModel, VideoModel
from connector.states import Downloading


class RegistryModelMock(RegistryModel):

    def __init__(self):
        super().__init__()
        self.final_state = None

    def set_state_and_persist(self, state):
        self.final_state = state

    def _persist(self):
        pass

    @classmethod
    def create_from_registry_id(cls, registry_id):
        obj = cls()
        obj.registry_id = registry_id
        obj.video_id = 'videoId'
        obj.category_id = 'categoryId'
        obj.status = 'notified'
        obj.message = 'message'
        obj.target_platform = 'facebook'
        obj.target_platform_video_id = 'targetPlatformVideoId'
        obj.mapping_id = 'mappingId'
        return obj


class VideoModelMock(VideoModel):

    @classmethod
    def create_from_video_id(cls, video_id):
        video = cls()
        video.title = 'video'
        video.description = 'text'
        video.keywords = []
        video.filename = '%s.mpeg' % video_id
        video.download_url = 'downloadUrl'
        video.image_id = 'image_id'
        video_hash_code = hashlib.md5()
        video_hash_code.update(bytes(video.title.encode('UTF-8')))
        video_hash_code.update(bytes(video.description.encode('UTF-8')))
        video_hash_code.update(bytes(str(video.keywords).encode('UTF-8')))
        video_hash_code.update(bytes(video.filename.encode('UTF-8')))
        video_hash_code.update(bytes(video.download_url.encode('UTF-8')))
        video_hash_code.update(bytes(video.image_id.encode('UTF-8')) if video.image_id is not None else "".encode('UTF-8'))
        video.hash_code = video_hash_code.hexdigest()
        return video


def download_function_mock(download_url, filename):
    pass


class TestUploadMechanism(unittest.TestCase):
    def test_upload_video_notified_state(self):
        registry_model_mock = RegistryModelMock()
        download_state = Downloading.create_downloading_state(registry_model_mock)
        download_state.video_model_class = VideoModelMock
        download_state.download_binary_from_kaltura_to_disk = download_function_mock
        download_state.run()


class TestUpdateMechanism(unittest.TestCase):
    pass


class TestUnpublishMechanism(unittest.TestCase):
    pass


class TestDeleteMechanism(unittest.TestCase):
    pass
