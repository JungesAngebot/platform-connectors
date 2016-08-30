from connector.facebook import upload_video_to_facebook, update_video_on_facebook, unpublish_video_on_facebook, \
    delete_video_on_facebook
from connector.youtube_mcn import upload_video_to_youtube_mcn, delete_video_on_youtube_mcn, unpublish_video_on_youtube_mcn, \
    update_video_on_youtube_mcn
from connector.youtube_direct import upload_video_to_youtube_direct, delete_video_on_youtube_direct, \
    unpublish_video_on_youtube_direct, update_video_on_youtube_direct


def dummy(video=None, registry=None):
    return video, registry


class PlatformInteraction(object):
    def __init__(self):
        self.registered_platforms = {
            'facebook': {
                'upload': upload_video_to_facebook,
                'update': update_video_on_facebook,
                'unpublish': unpublish_video_on_facebook,
                'delete': delete_video_on_facebook
            },
            'youtube': {
                'upload': upload_video_to_youtube_mcn,
                'update': update_video_on_youtube_mcn,
                'unpublish': unpublish_video_on_youtube_mcn,
                'delete': delete_video_on_youtube_mcn
            },
            'youtube_direct': {
                'upload': upload_video_to_youtube_direct,
                'update': update_video_on_youtube_direct,
                'unpublish': unpublish_video_on_youtube_direct,
                'delete': delete_video_on_youtube_direct
            }
        }

    def execute_platform_interaction(self, platform, interaction, video, registry_model):
        if platform in self.registered_platforms and interaction in self.registered_platforms[platform]:
            self.registered_platforms[platform][interaction](video, registry_model)
        else:
            raise Exception('Target platform %s with interaction %s does not exist!')
