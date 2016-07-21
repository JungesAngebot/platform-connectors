import datetime
import requests

from connector.db import MappingModel, VideoModel, RegistryModel


def upload_video_to_facebook(video: VideoModel, registry: RegistryModel):
    mapping = MappingModel.create_from_mapping_id(registry.mapping_id)

    url = "https://graph.facebook.com/v2.7/me/videos"

    body = {
        'access_token': str(mapping.target_id),
        'title': video.title,
        'description': video.description,
        'scheduled_publish_time': (datetime.datetime.now() + datetime.timedelta(days=150)).strftime('%s'),
        'published': 'false',
        'file_url': video.download_url
    }
    files = {
        'thumb': open("/home/swrlnxdef/Downloads/est02.png", 'rb'),
    }
    try:
        result = requests.post(url, data=body, files=files)
        if result.status_code == 200:
            registry.target_platform_video_id = result.json()['id']
            registry.set_state_and_persist("active")
        else:
            raise Exception("Invalid response.", result.json())

    except Exception as e:
        raise Exception("Error uploading video of registry entry %s to facebook." % registry.registry_id, e)
