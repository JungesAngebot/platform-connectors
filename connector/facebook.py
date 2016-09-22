import datetime
import hashlib
import json
import traceback

import requests
from commonspy.logging import log_info, log_warning

from connector.db import MappingModel, VideoModel, RegistryModel

API_URL = 'https://graph.facebook.com/v2.7/'


def upload_video_to_facebook(video: VideoModel, registry: RegistryModel):
    """
    Upload a video with thumbnail to facebook.

    :param video: information about the video to upload
    :param registry: current status of processing

    """
    if registry.target_platform_video_id or registry.intermediate_state != 'uploading':
        raise Exception('Upload not triggered because registry %s is not in correct state' % registry.registry_id)

    video_url = API_URL + 'me/videos'
    mapping = MappingModel.create_from_mapping_id(registry.mapping_id)
    try:
        body = {
            'access_token': str(mapping.target_id),
            'title': video.title,
            'description': video.description,
            # Facebook await ids. Add detection later.
            # 'content_tags': video.keywords,
            'scheduled_publish_time': (datetime.datetime.now() + datetime.timedelta(days=150)).strftime('%s'),
            'published': 'false',
            'file_url': video.download_url
        }

        if video.image_filename:
            files = {
                'thumb': open(video.image_filename, 'rb'),
            }
            result = requests.post(video_url, data=body, files=files)
        else:
            result = requests.post(video_url, data=body)

        log_info('Facebook result: %s' % result.content)

        if result.status_code == 200:
            facebook_video_id = result.json()['id']
            registry.target_platform_video_id = facebook_video_id
            registry.set_state_and_persist('active')
            _upload_captions_if_exist(video, facebook_video_id, mapping)
        else:
            raise Exception('Invalid response: %s' % result.content)

    except Exception as e:
        raise Exception('Error uploading video of registry entry %s to facebook.' % registry.registry_id) from e


def _upload_captions_if_exist(video:VideoModel, facebook_video_id, mapping):
    try:
        video_captions_url = API_URL + '%s/captions' % facebook_video_id
        if video.captions_filename:
            body = {
                'default_locale': 'de_DE'
            }
            files = {
                'captions_file': ('captions.de_DE.srt', open(video.captions_filename, 'rb'), 'application/octet-stream')
            }
            headers = {
                'Authorization': 'OAuth %s' % str(mapping.target_id),
            }
            result = requests.post(video_captions_url, data=body, files=files, headers=headers)
            if result.status_code == 200:
                log_info('Successfully uploaded captions for video %s' % video.video_id)
            else:
                raise Exception('Invalid response: %s' % result.content)
        else:
            log_info('No captions to upload for video %s' % video.video_id)
    except Exception as e:
        log_warning('Error uploading captions for video %s. Error: %s' % (video.video_id, e))
        log_warning(traceback.format_exc())


def update_video_on_facebook(video: VideoModel, registry: RegistryModel):
    """

    Update metadata of video on facebook if necessary.

    :param video: information about the video to upload
    :param registry: current status of processing

    """
    if registry.target_platform_video_id is None or registry.intermediate_state != 'updating':
        raise Exception('Upload not triggered because registry %s is not in correct state' % registry.registry_id)

    if video.hash_code == registry.video_hash_code:
        log_info('Metadata of registry entry %s not changed, so no update needed.' % registry.registry_id)
        return

    mapping = MappingModel.create_from_mapping_id(registry.mapping_id)
    try:
        get_metadata_url = API_URL + '/' + registry.target_platform_video_id + '?access_token=' + str(
            mapping.target_id) + '&fields=description,content_tags,title'

        metadata_result = requests.get(get_metadata_url).json()

        video_remote_hash = create_metadata_hash(metadata_result)

        if registry.video_hash_code != video_remote_hash:
            log_info('Metadata of video %s was changed on facebook. No update allowed.' % registry.registry_id)
            return

        body = {
            'access_token': str(mapping.target_id),
            'name': video.title,
            'description': video.description
        }

        update_url = API_URL + '/' + registry.target_platform_video_id

        result = requests.post(update_url, body)

        if result.status_code != 200:
            raise Exception('Invalid response: %s' % result.content)

    except Exception as e:
        raise Exception('Error updating video of registry entry %s on facebook.' % registry.registry_id) from e


def unpublish_video_on_facebook(video: VideoModel, registry: RegistryModel):
    """

    Unpublish video on facebook.

    :param video: information about the video to upload
    :param registry: current status of processing

    """
    if registry.target_platform_video_id is None or registry.intermediate_state not in ('unpublishing', 'deleting'):
        raise Exception('Unpublishing not triggered because registry %s is not in correct state' % registry.registry_id)

    mapping = MappingModel.create_from_mapping_id(registry.mapping_id)
    try:

        body = {
            'access_token': str(mapping.target_id),
            'expire_now': 'true',
        }

        update_url = API_URL + '/' + registry.target_platform_video_id

        result = requests.post(update_url, body)

        if result.status_code != 200:
            raise Exception('Invalid response: %s' % result.content)

    except Exception as e:
        raise Exception('Error unpublishing video of registry entry %s on facebook.' % registry.registry_id) from e


def delete_video_on_facebook(video: VideoModel, registry: RegistryModel):
    """

    We do not delete videos, just unpublish them. So method forward to unpublish_video_on_facebook().

    :param video: information about the video to upload
    :param registry: current status of processing

    """
    unpublish_video_on_facebook(video, registry)


def create_metadata_hash(metadata):
    """

    Create hash for metadata read for a video from facebook.

    :param metadata: metadata-response
    :return: md5-hash of values
    """
    video_hash_code = hashlib.md5()
    if 'title' in metadata:
        video_hash_code.update(bytes(metadata['title'].encode('UTF-8')))
    if 'description' in metadata:
        video_hash_code.update(bytes(metadata['description'].encode('UTF-8')))
    # Facebook await ids. Add detection later.
    # if 'content_tags' in metadata:
    #    video_hash_code.update(bytes(metadata['content_tags'].encode('UTF-8')))

    return video_hash_code.hexdigest()
