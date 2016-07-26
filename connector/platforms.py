from connector.facebook import upload_video_to_facebook, update_video_on_facebook, unpublish_video_on_facebook, \
    delete_video_on_facebook
from connector.youtube import upload_video_to_youtube, delete_video_on_youtube, unpublish_video_on_youtube, \
    update_video_on_youtube


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
                'upload': upload_video_to_youtube,
                'update': update_video_on_youtube,
                'unpublish': unpublish_video_on_youtube,
                'delete': delete_video_on_youtube
            }
        }

    def execute_platform_interaction(self, platform, interaction, video, registry_model):
        if platform in self.registered_platforms and interaction in self.registered_platforms[platform]:
            self.registered_platforms[platform][interaction](video, registry_model)
        else:
            raise Exception('Target platform %s with interaction %s does not exist!')
