import urllib.request

from commonspy.logging import log_error

from connector.db import VideoModel
from connector.platforms import PlatformInteraction


class DownloadingError(object):
    def run(self):
        pass


class UploadingError(object):
    def run(self):
        pass


class Downloading(object):
    def __init__(self, registry_model):
        self.error_state = DownloadingError()
        self.next_state = Uploading.create_uploading_state(registry_model)
        self.registry_model = registry_model
        self.download_binary_from_kaltura_to_disk = urllib.request.urlretrieve

    def _next_state(self, video):
        self.next_state.run(video)

    def _download_binaries(self, download_url, filename):
        try:
            self.download_binary_from_kaltura_to_disk(download_url, filename)
        except OSError as e:
            log_error('Cannot download binary with url %s.' % download_url)
            raise Exception('Cannot download binary with url %s.' % download_url) from e

    def run(self):
        try:
            self.registry_model.set_intermediate_state_and_persist('downloading')
            video_model = VideoModel.create_from_video_id(self.registry_model.video_id)
            self._download_binaries(video_model.download_url, video_model.filename)
            self._next_state(video_model)
        except Exception as e:
            log_error('Cannot finish download of binary from kaltura. %s' % str(e))
            self.fire_error()

    def fire_error(self):
        self.error_state.run()

    @classmethod
    def create_downloading_state(cls, registry_model):
        return cls(registry_model)


class Uploading(object):
    def __init__(self, registry_model):
        self.error_state = UploadingError()
        self.interaction = PlatformInteraction()
        self.registry_model = registry_model
        self.next_state = Active.create_active_state(self.registry_model)

    def _fire_error(self):
        self.error_state.run()

    def run(self, video):
        try:
            self.registry_model.set_intermediate_state_and_persist('uploading')
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'upload', video)
            self.next_state.run()
        except Exception as e:
            raise Exception(
                'Cannot perform target platform upload of video with id %s and registry id %s.' % (self.registry_model.registry_id, self.registry_model.video_id)) from e

    @classmethod
    def create_uploading_state(cls, registry_model):
        return cls(registry_model)


class Active(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model

    def run(self):
        try:
            self.registry_model.set_state_and_persist('active')
        except Exception as e:
            raise Exception('Cannot set state to active.') from e

    @classmethod
    def create_active_state(cls, registry_model):
        return cls(registry_model)


class Updating(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model

    def run(self):
        try:
            pass
        except Exception as e:
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            raise Exception('Unable to update video with id %s and registry id %s.' % (video_id, registry_id)) from e

    @classmethod
    def create_updating_state(cls, registry_model):
        return cls(registry_model)
