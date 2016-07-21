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


class DbFactoryMock(MongoDbFactory):
    @staticmethod
    def assets_collection():
        return CollectionMock()


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
        VideoModel.db_factory = DbFactoryMock

        model = VideoModel.create_from_video_id('id')

        self.assertEquals('videoName', model.title)
        self.assertEquals('videoText', model.description)
        self.assertEquals([], model.keywords)
        self.assertEquals('id.mpeg', model.filename)
        self.assertEquals('some_id', model.image_id)
        self.assertEquals('fd447058ca5b7cf49fcec33f3476703e', model.hash_code)
        self.assertEquals('downloadUrl', model.download_url)

