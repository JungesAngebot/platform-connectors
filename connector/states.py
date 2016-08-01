import os
import traceback
import urllib.request

from commonspy.logging import log_error, log_info, log_debug

from connector.db import VideoModel, persist_video_image_on_disk
from connector.platforms import PlatformInteraction


class Error(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model

    def run(self):
        try:
            log_info('Setting state for registry entry %s to error.' % self.registry_model.registry_id)
            self.registry_model.set_state_and_persist('error')
        except Exception as e:
            traceback.print_exc()
            log_error(e.__traceback__)
            log_error('Error while processing video with registry id %s.' % self.registry_model.registry_id)

    @classmethod
    def create_error_state(cls, registry_model):
        return cls(registry_model)


class Downloading(object):
    def __init__(self, registry_model):
        self.error_state = Error.create_error_state(registry_model)
        self.next_state = Uploading.create_uploading_state(registry_model)
        self.registry_model = registry_model
        self.download_binary_from_kaltura_to_disk = urllib.request.urlretrieve
        self.video_model_class = VideoModel
        self.image_download = persist_video_image_on_disk

    def _next_state(self, video):
        self.next_state.run(video)

    def _download_binaries(self, download_url, filename):
        try:
            log_info('Downloading video from %s with filename %s.' % (download_url, filename))
            if download_url is not None:
                self.download_binary_from_kaltura_to_disk(download_url, filename)
            else:
                raise Exception('No flavor source url provided for %s.' % filename)
            log_info('Download of video from %s with filename %s finished.' % (download_url, filename))
        except OSError as e:
            traceback.print_exc()
            log_error(e.__traceback__)
            log_error('Cannot download binary with url %s.' % download_url)
            raise Exception('Cannot download binary with url %s.' % download_url) from e

    def run(self):
        try:
            log_debug('Entering downloading state for registry id %s.' % self.registry_model.registry_id)
            self.registry_model.set_intermediate_state_and_persist('downloading')
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self._download_binaries(video_model.download_url, video_model.filename)
            self.image_download(video_model)
            self.registry_model.update_video_hash_code(video_model.hash_code)
            log_debug('Download of video with registry id %s successful.' % self.registry_model.registry_id)
            self._next_state(video_model)
        except Exception as e:
            traceback.print_exc()
            log_error(e.__traceback__)
            log_error('Cannot finish download of binary from kaltura. %s' % str(e))
            self.fire_error()

    def fire_error(self):
        self.error_state.run()

    @classmethod
    def create_downloading_state(cls, registry_model):
        return cls(registry_model)


class Uploading(object):
    def __init__(self, registry_model):
        self.error_state = Error.create_error_state(registry_model)
        self.interaction = PlatformInteraction()
        self.registry_model = registry_model
        self.next_state = Active.create_active_state(self.registry_model)

    def _fire_error(self):
        self.error_state.run()

    def run(self, video):
        try:
            log_debug('Entering uploading state for video with id %s to platform %s.' % (self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_intermediate_state_and_persist('uploading')
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'upload', video,
                                                          self.registry_model)
            log_debug('Finished upload of video with registry id %s to platform %s.' % (self.registry_model.registry_id, self.registry_model.target_platform))
            self.next_state.run()
        except Exception as e:
            log_error('Cannot perform target platform upload of video with id %s and registry id %s.' % (
                self.registry_model.registry_id, self.registry_model.video_id))
            log_error(e.__traceback__)
            traceback.print_exc()
            self._fire_error()

    @classmethod
    def create_uploading_state(cls, registry_model):
        return cls(registry_model)


class Active(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.error_state = Error.create_error_state(registry_model)

    def _cleanup(self):
        self.registry_model.set_intermediate_state_and_persist('')
        if os.path.isfile('%s.mpeg' % self.registry_model.video_id):
            os.remove('%s.mpeg' % self.registry_model.video_id)
        if os.path.isfile('%s.png' % self.registry_model.video_id):
            os.remove('%s.png' % self.registry_model.video_id)

    def _fire_error(self):
        self.error_state.run()

    def run(self):
        try:
            log_debug('Entering active state for video with registry id %s for platform %s.' % (self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_state_and_persist('active')
            self._cleanup()
            log_debug('Finished processing for video with registry id %s and platform %s' % (self.registry_model.registry_id, self.registry_model.target_platform))
        except Exception as e:
            traceback.print_exc()
            log_error(e.__traceback__)
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
        self.error_state = Error.create_error_state(registry_model)
        self.video_model_class = VideoModel

    def _fire_error(self):
        self.error_state.run()

    def run(self):
        try:
            log_debug('Entering update state for video with registy id %s and platform %s' % (self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_intermediate_state_and_persist('updating')
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'update', video_model,
                                                          self.registry_model)
            log_debug('Finished update state for video with registry id %s and platform %s' % (self.registry_model.registry_id, self.registry_model.target_platform))
            self.next_state.run()
        except Exception as e:
            traceback.print_exc()
            log_error(e.__traceback__)
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            log_error('Unable to update video with id %s and registry id %s.' % (video_id, registry_id))
            self._fire_error()

    @classmethod
    def create_updating_state(cls, registry_model):
        return cls(registry_model)


class Unpublish(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.error_state = Error.create_error_state(registry_model)
        self.next_state = Inactive.create_inactive_state(self.registry_model)
        self.interaction = PlatformInteraction()
        self.video_model_class = VideoModel

    def _fire_error(self):
        self.error_state.run()

    def run(self):
        try:
            log_debug('Entering unpublish state for video with registry id %s and platform %s' % (self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_intermediate_state_and_persist('unpublishing')
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'unpublish', video_model,
                                                          self.registry_model)
            log_debug('Finished unpublish state for video with registry id %s and platform %s' % (self.registry_model.registry_id, self.registry_model.target_platform))
            self.next_state.run()
        except Exception as e:
            traceback.print_exc()
            log_error(e.__traceback__)
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            log_error('Cannot unpublish video with id %s and registry id %s.' % (video_id, registry_id))
            self._fire_error()

    @classmethod
    def create_unpublish_state(cls, registry_model):
        return cls(registry_model)


class Inactive(object):
    def __init__(self, registry_model):
        self.error_state = Error.create_error_state(registry_model)
        self.registry_model = registry_model

    def _fire_error(self):
        self.error_state.run()

    def run(self):
        try:
            log_debug('Entering inactive state for video with registry id %s and platform %s' % (self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_state_and_persist('inactive')
            self._cleanup()
            log_debug('Finished inactive state for video with registry id %s and platform %s' % (self.registry_model.registry_id, self.registry_model.target_platform))
        except Exception as e:
            log_error(e.__traceback__)
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
        self.error_state = Error.create_error_state(registry_model)
        self.interaction = PlatformInteraction()
        self.registry_model = registry_model
        self.video_model_class = VideoModel

    def _fire_error(self):
        self.error_state.run()

    def run(self):
        try:
            log_debug('Entering deleting state for video with registry id %s and platform %s' % (self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_intermediate_state_and_persist('deleting')
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'delete', video_model,
                                                          self.registry_model)
            log_debug('Finished deleting state for video with registry id %s and platform %s' % (self.registry_model.registry_id, self.registry_model.target_platform))
            self.next_state.run()
        except Exception as e:
            log_error(e.__traceback__)
            traceback.print_exc()
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
        self.error_state = Error.create_error_state(registry_model)

    def _fire_error(self):
        self.error_state.run()

    def _cleanup(self):
        self.registry_model.set_intermediate_state_and_persist('')

    def run(self):
        try:
            log_debug('Entering deleted state for video with registry id %s and platform %s' % (self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_state_and_persist('deleted')
            self._cleanup()
            log_debug('Finished deleted state for video with registry id %s and platform %s' % (self.registry_model.registry_id, self.registry_model.target_platform))
        except Exception as e:
            log_error(e.__traceback__)
            traceback.print_exc()
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            log_error('Cannot set video with id %s and registry id %s to deleted.' % (video_id, registry_id))
            self._fire_error()

    @classmethod
    def create_deleted_state(cls, registry_model):
        return cls(registry_model)
