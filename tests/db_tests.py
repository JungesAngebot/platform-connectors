import unittest

from connector.db import MongoDbFactory, VideoModel


class CollectionMock(object):

    def find_one(self, query):
        return dict(
            name='videoName',
            text='videoText',
            tags=[],
            downloadUrl='downloadUrl',
            image_id='some_id'
        )


class CollectionMockWithoutImageId(object):
    def find_one(self, query):
        return dict(
            name='videoName',
            text='videoText',
            tags=[],
            downloadUrl='downloadUrl',
        )


class DbFactoryMock(MongoDbFactory):

    mock_to_use = CollectionMock

    @staticmethod
    def assets_collection():
        return DbFactoryMock.mock_to_use()


class VideoModelTest(unittest.TestCase):
    def test_video_contains_all_fields(self):
        VideoModel.db_factory = DbFactoryMock

        model = VideoModel.create_from_video_id('id')

        self.assertEquals('videoName', model.title)
        self.assertEquals('videoText', model.description)
        self.assertEquals([], model.keywords)
        self.assertEquals('id.mpeg', model.filename)
        self.assertEquals('some_id', model.image_id)
        self.assertEquals('fd447058ca5b7cf49fcec33f3476703e', model.hash_code)
        self.assertEquals('downloadUrl', model.download_url)

    def test_video_without_image_id(self):
        factory_mock = DbFactoryMock
        factory_mock.mock_to_use = CollectionMockWithoutImageId
        VideoModel.db_factory = factory_mock

        model = VideoModel.create_from_video_id('id')

        self.assertEquals('videoName', model.title)
        self.assertEquals('videoText', model.description)
        self.assertEquals([], model.keywords)
        self.assertEquals('id.mpeg', model.filename)
        self.assertEquals(None, model.image_id)
        self.assertEquals('c8b5d3de41ac85dc57bfede16b147d25', model.hash_code)
        self.assertEquals('downloadUrl', model.download_url)

