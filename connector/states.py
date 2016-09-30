import os
import traceback
import urllib.request

from commonspy.logging import log_error, log_info, log_debug, build_message_from_exception_chain

from connector.db import VideoModel, persist_video_image_on_disk
from connector.platforms import PlatformInteraction
from connector.youtube import SuccessWithWarningException


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
        self.captions_download = download_captions

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
            log_error(traceback.format_exc())
            log_error('Cannot download binary with url %s.' % download_url)
            raise Exception('Cannot download binary with url %s.' % download_url) from e

    def run(self):
        try:
            log_debug('Entering downloading state for registry id %s.' % self.registry_model.registry_id)
            self.registry_model.set_intermediate_state_and_persist('downloading')
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self._download_binaries(video_model.download_url, video_model.filename)
            self.image_download(video_model)
            self.captions_download(video_model)
            self.registry_model.update_video_hash_code(video_model.hash_code)
            log_debug('Download of video with registry id %s successful.' % self.registry_model.registry_id)
            self._next_state(video_model)
        except Exception as e:
            traceback.print_exc()
            log_error(traceback.format_exc())
            message = 'Cannot finish download of binary from kaltura. %s' % build_message_from_exception_chain(e)
            log_error(message)
            self.registry_model.message = message
            self._fire_error()

    def _fire_error(self):
        self.error_state.run()

    @classmethod
    def create_downloading_state(cls, registry_model):
        return cls(registry_model)


def download_captions(video_model: VideoModel):
    try:
        log_info('Downloading captions for video %s' % video_model.video_id)
        if video_model.captions_url is not None:
            urllib.request.urlretrieve(video_model.captions_url, video_model.captions_filename)
        else:
            log_info('No captions found for video %s' % video_model.video_id)
            video_model.captions_filename = None
        log_info('Finished download for captions of video %s to file %s' % (video_model.video_id, video_model.captions_filename))
    except OSError as e:
        video_model.captions_filename = None
        traceback.print_exc()
        log_error(traceback.format_exc())
        log_error('Cannot download captions for video %s with url %s' % (video_model.video_id, video_model.captions_url))


class Uploading(object):
    def __init__(self, registry_model):
        self.error_state = Error.create_error_state(registry_model)
        self.interaction = PlatformInteraction()
        self.registry_model = registry_model
        self.next_state = Active.create_active_state(self.registry_model, True)
        self.next_state_with_custom_message = Active.create_active_state(self.registry_model, False)

    def _fire_error(self):
        self.error_state.run()

    def run(self, video):
        try:
            log_debug('Entering uploading state for video with id %s to platform %s.' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_intermediate_state_and_persist('uploading')
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'upload', video,
                                                          self.registry_model)
            log_debug('Finished upload of video with registry id %s to platform %s.' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
            self.next_state.run(video)
        except SuccessWithWarningException as e:
            log_debug('Finished upload of video with registry id %s to platform %s.' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
            self.next_state_with_custom_message.run(video)
        except Exception as e:
            message = 'Cannot perform target platform upload of video with id %s and registry id %s. %s' % (
                self.registry_model.registry_id, self.registry_model.video_id, build_message_from_exception_chain(e))
            log_error(message)
            log_error(traceback.format_exc())
            traceback.print_exc()
            self.registry_model.message = message
            self._fire_error()

    @classmethod
    def create_uploading_state(cls, registry_model):
        return cls(registry_model)


class Active(object):
    def __init__(self, registry_model, overwrite_success_message):
        self.registry_model = registry_model
        self.error_state = Error.create_error_state(registry_model)
        self.overwrite_success_message = overwrite_success_message

    def _cleanup(self, video):
        self.registry_model.set_intermediate_state_and_persist('')
        if os.path.isfile(video.filename):
            os.remove(video.filename)
            log_debug("Cleaning up video file: %s" % video.filename)
        if os.path.isfile(video.image_filename):
            os.remove(video.image_filename)
            log_debug("Cleaning up thumbnail file: %s" % video.image_filename)
        if video.captions_filename and os.path.isfile(video.captions_filename):
            os.remove(video.captions_filename)
            log_debug("Cleaning up captions file: %s" % video.captions_filename)

    def _fire_error(self):
        self.error_state.run()

    def run(self, video):
        try:
            log_debug('Entering active state for video with registry id %s for platform %s.' % (
                self.registry_model.registry_id, self.registry_model.target_platform))

            if self.overwrite_success_message:
                self.registry_model.set_state_and_message_and_persist('active',
                                                                  'Content successfully published on target platform.')
            else:
                self.registry_model.set_state_and_persist('active')

            self._cleanup(video)
            log_debug('Finished processing for video with registry id %s and platform %s' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
        except Exception as e:
            traceback.print_exc()
            log_error(traceback.format_exc())
            message = 'Cannot set state to active. %s ' % build_message_from_exception_chain(e)
            log_error(message)
            self.registry_model.message = message
            self._fire_error()

    @classmethod
    def create_active_state(cls, registry_model, overwrite_success_message=True):
        return cls(registry_model, overwrite_success_message)


class Updating(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.interaction = PlatformInteraction()
        self.next_state = Active.create_active_state(self.registry_model)
        self.error_state = Error.create_error_state(registry_model)
        self.video_model_class = VideoModel
        self.captions_download = download_captions

    def _fire_error(self):
        self.error_state.run()

    def run(self):
        try:
            log_debug('Entering update state for video with registy id %s and platform %s' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_intermediate_state_and_persist('updating')
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self.captions_download(video_model)
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'update', video_model,
                                                          self.registry_model)
            log_debug('Finished update state for video with registry id %s and platform %s' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
            self.next_state.run(video_model)
        except Exception as e:
            traceback.print_exc()
            log_error(traceback.format_exc())
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            message = 'Unable to update video with id %s and registry id %s. %s' % (
            video_id, registry_id, build_message_from_exception_chain(e))
            log_error(message)
            self.registry_model.message = message
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
            log_debug('Entering unpublish state for video with registry id %s and platform %s' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_intermediate_state_and_persist('unpublishing')
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'unpublish', video_model,
                                                          self.registry_model)
            log_debug('Finished unpublish state for video with registry id %s and platform %s' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
            self.next_state.run()
        except Exception as e:
            traceback.print_exc()
            log_error(traceback.format_exc())
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            message = 'Cannot unpublish video with id %s and registry id %s. %s' % (
            video_id, registry_id, build_message_from_exception_chain(e))
            log_error(message)
            self.registry_model.message = message
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
            log_debug('Entering inactive state for video with registry id %s and platform %s' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_state_and_message_and_persist('inactive',
                                                                  'Content successfully set to private on target platform.')
            self._cleanup()
            log_debug('Finished inactive state for video with registry id %s and platform %s' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
        except Exception as e:
            log_error(traceback.format_exc())
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            message = 'Cannot set state of video with id %s and registry id %s to inactive. %s' % (
                video_id, registry_id, build_message_from_exception_chain(e))
            log_error(message)
            self.registry_model.message = message
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
            log_debug('Entering deleting state for video with registry id %s and platform %s' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_intermediate_state_and_persist('deleting')
            video_model = self.video_model_class.create_from_video_id(self.registry_model.video_id)
            self.interaction.execute_platform_interaction(self.registry_model.target_platform, 'delete', video_model,
                                                          self.registry_model)
            log_debug('Finished deleting state for video with registry id %s and platform %s' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
            self.next_state.run()
        except Exception as e:
            log_error(traceback.format_exc())
            traceback.print_exc()
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            message = 'Cannot delete video with id %s and registry id %s. %s' % (
            video_id, registry_id, build_message_from_exception_chain(e))
            log_error(message)
            self.registry_model.message = message
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
            log_debug('Entering deleted state for video with registry id %s and platform %s' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
            self.registry_model.set_state_and_message_and_persist('deleted',
                                                                  'Content successfully set to private on target platform.')
            self._cleanup()
            log_debug('Finished deleted state for video with registry id %s and platform %s' % (
                self.registry_model.registry_id, self.registry_model.target_platform))
        except Exception as e:
            log_error(traceback.format_exc())
            traceback.print_exc()
            registry_id = self.registry_model.registry_id
            video_id = self.registry_model.video_id
            message = 'Cannot set video with id %s and registry id %s to deleted. %s' % (
            video_id, registry_id, build_message_from_exception_chain(e))
            log_error(message)
            self.registry_model.message = message
            self._fire_error()

    @classmethod
    def create_deleted_state(cls, registry_model):
        return cls(registry_model)
