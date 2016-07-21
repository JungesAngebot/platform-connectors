from connector.facebook import upload_video_to_facebook, update_video_on_facebook, unpublish_video_on_facebook, \
    delete_video_on_facebook


def dummy(video, registry):
    pass


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
                'upload': dummy,
                'update': dummy,
                'unpublish': dummy,
                'delete': dummy
            }
        }

    def execute_platform_interaction(self, platform, interaction, video, registry_model):
        if platform in self.registered_platforms and interaction in self.registered_platforms[platform]:
            self.registered_platforms[platform][interaction](video, registry_model)
        else:
            raise Exception('Target platform %s with interaction %s does not exist!')
