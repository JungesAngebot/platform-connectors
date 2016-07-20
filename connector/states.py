import urllib.request

from commonspy.logging import log_error

from connector.db import RegistryModel, VideoModel


class DownloadingError:
    def run(self):
        pass


class Downloading:
    def __init__(self, registry_id):
        self.error_state = DownloadingError
        self.next_state = Uploading
        self.registry_id = registry_id
        self.download_binary_from_kaltura_to_disk = urllib.request.urlretrieve

    def _next_state(self, video):
        self.next_state().run(None)

    def _download_binaries(self, download_url, filename):
        try:
            self.download_binary_from_kaltura_to_disk(download_url, filename)
        except OSError:
            pass

    def run(self):
        try:
            registry_model = RegistryModel.create_from_registry_id(self.registry_id)
            video_model = VideoModel.create_from_video_id(registry_model['videoId'])
            self._download_binaries(video_model.download_url, video_model.filename)
        except Exception as e:
            log_error('Cannot finish download of binary from kaltura. %s' % str(e))
            self.fire_error()

    def fire_error(self):
        self.error_state().run()

    @classmethod
    def create_downloading_state(cls, registry_id):
        return cls(registry_id)


class Uploading:
    def run(self, video):
        pass
