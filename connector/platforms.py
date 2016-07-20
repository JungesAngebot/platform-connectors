
class PlatformInteraction(object):
    def __init__(self):
        self.registered_platforms = {
            'facebook': {
                'upload': None,
                'update': None,
                'unpublish': None,
                'delete': None
            },
            'youtube': {
                'upload': None,
                'update': None,
                'unpublish': None,
                'delete': None
            }
        }