import unittest

from connector.db import RegistryModel


class RegistryModelMock(RegistryModel):

    def _persist(self):
        pass

    @classmethod
    def create_from_registry_id(cls, registry_id):
        obj = cls()
        obj.registry_id = registry_id
        obj.video_id = 'videoId'
        obj.category_id = 'categoryId'
        obj.status = 'status'
        obj.message = 'message'
        obj.target_platform = 'targetPlatform'
        obj.target_platform_video_id = 'targetPlatformVideoId'
        obj.mapping_id = 'mappingId'
        return obj


class TestUploadMechanism(unittest.TestCase):
    pass


class TestUpdateMechanism(unittest.TestCase):
    pass


class TestUnpublishMechanism(unittest.TestCase):
    pass


class TestDeleteMechanism(unittest.TestCase):
    pass
