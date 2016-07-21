import os
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


class ActiveError(object):
    def run(self):
        pass


class UpdatingError(object):
    def run(self):
        pass


class UnpublishError(object):
    def run(self):
        pass


class DeletingError(object):
    def run(self):
        pass


class DeletedError(object):
    def run(self):
        pass


class InactiveError(object):
    def run(self):
        pass


class Error(object):
    def __init__(self):
        pass

    def run(self):
        pass


class Downloading(object):
    def __init__(self, registry_model):
        self.error_state = DownloadingError()
        self.next_state = Uploading.create_uploading_state(registry_model)
        self.registry_model = registry_model
        self.download_binary_from_kaltura_to_disk = urllib.request.urlretrieve
        self.video_model_class = VideoModel

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
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self._download_binaries(video_model.download_url, video_model.filename)
            self.registry_model.update_video_hash_code(video_model.hash_code)
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
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'upload', video, self.registry_model)
            self.next_state.run()
        except Exception:
            log_error('Cannot perform target platform upload of video with id %s and registry id %s.' % (self.registry_model.registry_id, self.registry_model.video_id))
            self._fire_error()

    @classmethod
    def create_uploading_state(cls, registry_model):
        return cls(registry_model)


class Active(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.error_state = ActiveError()

    def _cleanup(self):
        self.registry_model.set_intermediate_state_and_persist('')
        if os.path.isfile('%s.mpeg' % self.registry_model.video_id):
            os.remove('%s.mpeg' % self.registry_model.video_id)

    def _fire_error(self):
        self.error_state.run()

    def run(self):
        try:
            self.registry_model.set_state_and_persist('active')
            self._cleanup()
        except Exception as e:
            log_error('Cannot set state to active.')
            self._fire_error()

    @classmethod
    def create_active_state(cls, registry_model):
        return cls(registry_model)


class Updating(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.interaction = PlatformInteraction()
        self.next_state = Active.create_active_state(self.registry_model)
        self.error_state = UpdatingError()
        self.video_model_class = VideoModel

    def _fire_error(self):
        self.error_state.run()

    def run(self):
        try:
            self.registry_model.set_intermediate_state_and_persist('updating')
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'update', video_model, self.registry_model)
            self.next_state.run()
        except Exception as e:
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            log_error('Unable to update video with id %s and registry id %s.' % (video_id, registry_id))
            self._fire_error()

    @classmethod
    def create_updating_state(cls, registry_model):
        return cls(registry_model)


class Unpublish(object):
    def __init__(self, registry_model):
        self.error_state = UnpublishError()
        self.registry_model = registry_model
        self.next_state = Inactive.create_inactive_state(self.registry_model)
        self.interaction = PlatformInteraction()
        self.video_model_class = VideoModel

    def _fire_error(self):
        self.error_state.run()

    def run(self):
        try:
            self.registry_model.set_intermediate_state_and_persist('unpublishing')
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'unpublish', video_model, self.registry_model)
            self.next_state.run()
        except Exception:
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            log_error('Cannot unpublish video with id %s and registry id %s.' % (video_id, registry_id))
            self._fire_error()

    @classmethod
    def create_unpublish_state(cls, registry_model):
        return cls(registry_model)


class Inactive(object):
    def __init__(self, registry_model):
        self.error_state = InactiveError()
        self.registry_model = registry_model

    def _fire_error(self):
        self.error_state.run()

    def run(self):
        try:
            self.registry_model.set_state_and_persist('inactive')
            self._cleanup()
        except Exception:
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            log_error('Cannot set state of video with id %s and registry id %s to inactive.' % (video_id, registry_id))
            self._fire_error()

    def _cleanup(self):
        self.registry_model.set_intermediate_state_and_persist('')

    @classmethod
    def create_inactive_state(cls, registry_model):
        return cls(registry_model)


class Deleting(object):
    def __init__(self, registry_model):
        self.next_state = Deleted.create_deleted_state(registry_model)
        self.error_state = DeletingError()
        self.interaction = PlatformInteraction()
        self.registry_model = registry_model
        self.video_model_class = VideoModel

    def _fire_error(self):
        self.error_state.run()

    def run(self):
        try:
            self.registry_model.set_intermediate_state_and_persist('deleting')
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'delete', video_model, self.registry_model)
            self.next_state.run()
        except Exception:
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            log_error('Cannot delete video with id %s and registry id %s.' % (video_id, registry_id))
            self._fire_error()

    @classmethod
    def create_deleting_state(cls, registry_model):
        return cls(registry_model)


class Deleted(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.error_state = DeletedError()

    def _fire_error(self):
        self.error_state.run()

    def _cleanup(self):
        self.registry_model.set_intermediate_state_and_persist('')

    def run(self):
        try:
            self.registry_model.set_state_and_persist('deleted')
            self._cleanup()
        except Exception:
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            log_error('Cannot set video with id %s and registry id %s to deleted.' % (video_id, registry_id))
            self._fire_error()

    @classmethod
    def create_deleted_state(cls, registry_model):
        return cls(registry_model)
