from connector.db import RegistryModel


class DownloadingError:
    def run(self):
        pass


class Downloading:

    def __init__(self, registry_id):
        self.error_state = DownloadingError
        self.next_state = Uploading
        self.registry_id = registry_id

    def _next_state(self, video):
        self.next_state().run(None)

    def run(self):
        registry_model = RegistryModel.create_from_registry_id(self.registry_id)

    def on_error(self):
        self.error_state().run()

    @classmethod
    def create_downloading_state(cls, registry_id):
        return cls(registry_id)


class Uploading:
    def run(self, video):
        pass
