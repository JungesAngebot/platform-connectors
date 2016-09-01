from functools import partial

from commonspy.logging import log_info

from connector import config
from connector.facebook import upload_video_to_facebook, update_video_on_facebook, unpublish_video_on_facebook, \
    delete_video_on_facebook
from connector.youtube_mcn import upload_video_to_youtube_mcn, delete_video_on_youtube_mcn, unpublish_video_on_youtube_mcn, \
    update_video_on_youtube_mcn
from connector.youtube_direct import upload_video_to_youtube_direct, delete_video_on_youtube_direct, \
    unpublish_video_on_youtube_direct, update_video_on_youtube_direct


def test_mode_action(action, video, registry):
    log_info("DRY MODE action: '%s' | video: %s | registry: %s" % (action, video.__dict__, registry.__dict__))

registered_platforms = {
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

test_mode_platforms = {
    'facebook': {
        'upload': partial(test_mode_action, 'facebook upload'),
        'update': partial(test_mode_action, 'facebook update'),
        'unpublish': partial(test_mode_action, 'facebook unpublish'),
        'delete': partial(test_mode_action, 'facebook delete')
    },
    'youtube': {
        'upload': partial(test_mode_action, 'youtube upload'),
        'update': partial(test_mode_action, 'youtube update'),
        'unpublish': partial(test_mode_action, 'youtube unpublish'),
        'delete': partial(test_mode_action, 'youtube delete')
    },
    'youtube_direct': {
        'upload': partial(test_mode_action, 'youtube_direct upload'),
        'update': partial(test_mode_action, 'youtube_direct update'),
        'unpublish': partial(test_mode_action, 'youtube_direct unpublish'),
        'delete': partial(test_mode_action, 'youtube_direct delete')
    }
}

class PlatformInteraction(object):
    def __init__(self):
        if config.property('test_mode'):
            self.registered_platforms = test_mode_platforms
        else:
            self.registered_platforms = registered_platforms

    def execute_platform_interaction(self, platform, interaction, video, registry_model):
        if platform in self.registered_platforms and interaction in self.registered_platforms[platform]:
            self.registered_platforms[platform][interaction](video, registry_model)
        else:
            raise Exception('Target platform %s with interaction %s does not exist!')
