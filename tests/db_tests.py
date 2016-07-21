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


class CollectionMockWithoutVideoTitle(object):
    def find_one(self, query):
        return dict(
            text='videoText',
            tags=[],
            downloadUrl='downloadUrl',
            image_id='image_id'
        )


class CollectionMockWithoutDescription(object):
    def find_one(self, query):
        return dict(
            name='videoTitle',
            tags=[],
            downloadUrl='downloadUrl',
            image_id='image_id'
        )


class CollectionMockWithoutTags(object):
    def find_one(self, query):
        return dict(
            name='videoTitle',
            text='videoDescription',
            downloadUrl='downloadUrl',
            image_id='image_id'
        )


class CollectionMockWithTags(object):
    def find_one(self, query):
        return dict(
            name='videoTitle',
            text='videoDescription',
            tags='tag1,tag2,tag3',
            downloadUrl='downloadUrl',
            image_id='image_id'
        )


class CollectionMockWithSpacesInTags(object):
    def find_one(self, query):
        return dict(
            name='videoTitle',
            text='videoDescription',
            tags='tag 1,tag 2,tag 3',
            downloadUrl='downloadUrl',
            image_id='image_id'
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

    def test_video_without_a_title(self):
        factory_mock = DbFactoryMock
        factory_mock.mock_to_use = CollectionMockWithoutVideoTitle
        VideoModel.db_factory = factory_mock

        model = VideoModel.create_from_video_id('id')

        self.assertEquals('', model.title)
        self.assertEquals('videoText', model.description)
        self.assertEquals([], model.keywords)
        self.assertEquals('id.mpeg', model.filename)
        self.assertEquals('image_id', model.image_id)
        self.assertEquals('15c4643f041b0098c90ca9e7cabd3bb0', model.hash_code)
        self.assertEquals('downloadUrl', model.download_url)

    def test_video_without_a_description(self):
        factory_mock = DbFactoryMock
        factory_mock.mock_to_use = CollectionMockWithoutDescription
        VideoModel.db_factory = factory_mock

        model = VideoModel.create_from_video_id('id')

        self.assertEquals('videoTitle', model.title)
        self.assertEquals('', model.description)
        self.assertEquals([], model.keywords)
        self.assertEquals('id.mpeg', model.filename)
        self.assertEquals('image_id', model.image_id)
        self.assertEquals('e46a220b84fe357e381b0799aac47226', model.hash_code)
        self.assertEquals('downloadUrl', model.download_url)

    def test_video_without_tags(self):
        factory_mock = DbFactoryMock
        factory_mock.mock_to_use = CollectionMockWithoutTags
        VideoModel.db_factory = factory_mock

        model = VideoModel.create_from_video_id('id')

        self.assertEquals('videoTitle', model.title)
        self.assertEquals('videoDescription', model.description)
        self.assertEquals([], model.keywords)
        self.assertEquals('id.mpeg', model.filename)
        self.assertEquals('image_id', model.image_id)
        self.assertEquals('7b0874a50d48c45ab258534142bd182c', model.hash_code)
        self.assertEquals('downloadUrl', model.download_url)

    def test_video_with_tags(self):
        factory_mock = DbFactoryMock
        factory_mock.mock_to_use = CollectionMockWithTags
        VideoModel.db_factory = factory_mock

        model = VideoModel.create_from_video_id('id')

        self.assertEquals(['tag1', 'tag2', 'tag3'], model.keywords)

    def test_video_filename(self):
        factory_mock = DbFactoryMock
        factory_mock.mock_to_use = CollectionMock
        VideoModel.db_factory = factory_mock

        model = VideoModel.create_from_video_id('id')

        self.assertEquals('id.mpeg', model.filename)

    def test_video_image_name(self):
        factory_mock = DbFactoryMock
        factory_mock.mock_to_use = CollectionMock
        VideoModel.db_factory = factory_mock

        model = VideoModel.create_from_video_id('id')

        self.assertEquals('id.png', model.image_filename)

    def test_video_with_tags_that_contains_whitespaces(self):
        pass

    def test_video_with_trailing_spaces_in_tags(self):
        pass
