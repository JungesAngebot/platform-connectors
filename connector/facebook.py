import datetime
import hashlib
import os
import traceback
import time

import requests
from commonspy.logging import log_info, log_warning, log_debug

from connector.db import MappingModel, VideoModel, RegistryModel

API_URL = 'https://graph.facebook.com/v2.7/'
MAX_RETRY = 5
CHUNK_TIMEOUT = 45
CHUNK_ERROR_WAIT_SECONDS = 2


def upload_video_to_facebook(video: VideoModel, registry: RegistryModel):
    """
    Upload a video with thumbnail to facebook by chunking the file.

    :param video: information about the video to upload
    :param registry: current status of processing

    """
    if registry.target_platform_video_id or registry.intermediate_state != 'uploading':
        raise Exception('Upload not triggered because registry %s is not in correct state' % registry.registry_id)

    video_url = API_URL + 'me/videos'
    mapping = MappingModel.create_from_mapping_id(registry.mapping_id)

    try:
        # START
        file_size = os.path.getsize(video.filename)
        body = {
            'access_token': str(mapping.target_id),
            'upload_phase': 'start',
            'file_size': file_size
        }
        start_result = requests.post(video_url, data=body)

        if start_result.status_code != 200:
            raise Exception('Registry: %s. Error starting upload session %s' % (registry.registry_id, start_result.content))

        log_debug('Registry %s. Start result: %s' % (registry.registry_id, start_result.content))
        start_result_content = start_result.json()
        session_id = start_result_content['upload_session_id']
        start_offset = int(start_result_content['start_offset'])
        end_offset = int(start_result_content['end_offset'])
        video_id = start_result_content['video_id']
        log_info('Registry: %s. Upload session started with session_id: %s, start_offset: %s, end_offset: %s, file_size: %s' % (registry.registry_id, session_id, start_offset, end_offset, file_size))

        # TRANSFER
        file = open(video.filename, 'rb')
        while end_offset > start_offset:
            percent_uploaded = (start_offset / file_size) * 100
            log_info('Registry: %s. Uploading chunk for session_id: %s, percent done: %d%%, start_offset: %s, end_offset: %s, file_size: %s' % (
                registry.registry_id, session_id, percent_uploaded, start_offset, end_offset, file_size))
            start_offset, end_offset = upload_chunk(0, video_url, file, session_id, start_offset, end_offset, str(mapping.target_id), registry.registry_id)

        # FINISH
        log_info('Registry: %s. Uploading chunks finished. Sending finsh request session_id: %s' % (registry.registry_id, session_id))
        body = {
            'access_token': str(mapping.target_id),
            'title': video.title,
            'description': video.description,
            # Facebook await ids. Add detection later.
            # 'content_tags': video.keywords,
            'scheduled_publish_time': (datetime.datetime.now() + datetime.timedelta(days=150)).strftime('%s'),
            'published': 'false',
            'upload_phase': 'finish',
            'upload_session_id': session_id,
            'fields': 'id'
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
            registry.target_platform_video_id = video_id
            registry.set_state_and_persist('active')
        else:
            raise Exception('Invalid response: %s' % result.content)

    except Exception as e:
        raise Exception('Error uploading video of registry entry %s to facebook.' % registry.registry_id) from e


def upload_chunk(retry_count, video_url, file, session_id, start_offset, end_offset, access_token, registry_id):
    if retry_count > MAX_RETRY:
        raise Exception(
            'Registry: %s. Giving up uploading chunk with session_id: %s, start_offset: %s, end_offset: %s' % (
            registry_id, session_id, start_offset, end_offset))

    try:
        file.seek(start_offset)
        bytes_to_read = end_offset - start_offset
        transfer_body = {
            'access_token': access_token,
            'upload_phase': 'transfer',
            'upload_session_id': session_id,
            'start_offset': start_offset,
        }
        transfer_file = {
            'video_file_chunk': file.read(bytes_to_read)
        }
        transfer_result = requests.post(video_url, data=transfer_body, files=transfer_file, timeout=CHUNK_TIMEOUT)
        if transfer_result.status_code == 200:
            transfer_result_content = transfer_result.json()
            new_start_offset = transfer_result_content['start_offset']
            new_end_offset = transfer_result_content['end_offset']
            return int(new_start_offset), int(new_end_offset)
        else:
            new_retry_count = retry_count + 1
            log_warning('Registry: %s, Error uploading chunk. Retry: %s/%s. Response was %s' % (registry_id, new_retry_count, MAX_RETRY, transfer_result.content))
            return upload_chunk(new_retry_count, video_url, file, session_id, start_offset, end_offset, access_token, registry_id)
    except Exception as e:
        new_retry_count = retry_count + 1
        log_warning('Registry: %s, Error uploading chunk. Retry: %s/%s.' % (registry_id, new_retry_count, MAX_RETRY))
        log_warning('Registry: %s, Exception: %s' % (registry_id, traceback.format_exc()))
        time.sleep(CHUNK_ERROR_WAIT_SECONDS)
        return upload_chunk(new_retry_count, video_url, file, session_id, start_offset, end_offset, access_token, registry_id)


def upload_video_to_facebook_unchunked(video: VideoModel, registry: RegistryModel):
    """
    Upload a video with thumbnail to facebook by specifying the download URL. This method has restrictions, so that no
    video can be uploaded with more than 1 GB or a lenght of 20 min plus.

    :param video: information about the video to upload
    :param registry: current status of processing

    """
    if registry.target_platform_video_id or registry.intermediate_state != 'uploading':
        raise Exception(
            'Upload not triggered because registry %s is not in correct state' % registry.registry_id)

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
            registry.target_platform_video_id = result.json()['id']
            registry.set_state_and_persist('active')
        else:
            raise Exception('Invalid response: %s' % result.content)

    except Exception as e:
        raise Exception('Error uploading video of registry entry %s to facebook.' % registry.registry_id) from e


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
