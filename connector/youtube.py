import hashlib
import logging
import os
import sys
import time
from random import random

import httplib2
from commonspy.logging import log_info, log_error
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials

from connector import APP_ROOT
from connector.db import VideoModel, RegistryModel, MappingModel

""" This module handles youtube video upload, update
and unpublish. Videos are only uploaded to multi
channel networks. Single channel upload (for non
youtube partners) is not supported.
"""
# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError,)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = (500, 502, 503, 504,)

INVALID_CREDENTIALS = b"Invalid Credentials"
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
YOUTUBE_CONTENT_ID_API_SERVICE_NAME = 'youtubePartner'
YOUTUBE_CONTENT_ID_API_VERSION = 'v1'

youtube_scopes = (
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtubepartner',
    'https://www.googleapis.com/auth/youtube.force-ssl'
)


class UpdateError(Exception):
    """ Error during update operations. """

    def __init__(self, *args, **kwargs):
        pass


class UnpublishError(Exception):
    """ Error during unpublish operations. """

    def __init__(self, *args, **kwargs):
        pass


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
    #    if 'tags' in metadata:
    #        video_hash_code.update(bytes(metadata['tags'].encode('UTF-8')))

    return video_hash_code.hexdigest()


def youtube_inst():
    """ Authenticates at the youtube api.
    The connector will always upload to multi channel
    networks on youtube. Therefor four youtube
    api scopes are required:
    - Standard Youtube Scope (full read / write access)
    - Youtube partner scope
    - Youtube Upload Scope
    - Youtube force-ssl Scope
    """

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        APP_ROOT + '/config/client_secrets.json', scopes=youtube_scopes)

    http = httplib2.Http()
    http = credentials.authorize(http)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                    http=http)

    youtube_partner = build(YOUTUBE_CONTENT_ID_API_SERVICE_NAME,
                            YOUTUBE_CONTENT_ID_API_VERSION, http=http)

    return youtube, youtube_partner


def get_content_owner_id(youtube_partner):
    """ Function to gather the youtube content owner
    id. This id is required to upload a video to
    a multi channel network on youtube.
    """

    try:
        content_owners_list_response = youtube_partner.contentOwners().list(
            fetchMine=True
        ).execute()
    except HttpError as e:
        raise Exception(
            'The request is not authorized by a Google Account that is linked to a YouTube content owner.') from e

    return content_owners_list_response['items'][0]['id']


def resumable_upload(insert_request):
    """ Actually uploads the video to youtube.
    If an error occours the function will retry the
    upload. (with time span between uploads).
    """
    response = None
    error = None
    retry = 0
    video_id = None
    while response is None:
        try:
            log_info('Uploading file...')
            status, response = insert_request.next_chunk()
            if 'id' in response:
                video_id = response['id']
                log_info('Video id %s was successfully uploaded.' % video_id)
            else:
                raise Exception('The upload failed with an unexpected response: %s' % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = 'A retriable HTTP error %d occurred:\n%s' % (e.resp.status, e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = 'A retriable error occurred: %s' % e

        if error is not None:
            log_error('Error during upload, retrying it. Message: %s' % error)
            retry += 1
            if retry > 10:
                raise Exception('No longer attempting to retry.')

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            log_info('Sleeping %f seconds and then retrying...' % sleep_seconds)
            time.sleep(sleep_seconds)
    return video_id


def upload(youtube, video: VideoModel, content_owner_id, channel_id):
    """ initialized the youtube video upload. This
    mechanism uses the youtube partner authentication / client
    and is only able to upload videos to a multi channel
    youtube network.

    :param youtube: youtube client (partner)
    :param video: video metadata
    :param content_owner_id: the id of the channel owner
    :param channel_id: the target channel
    :return: resumable upload
    """

    body = dict(
        snippet=dict(
            title=video.title,
            description=video.description,
            tags=video.keywords,
            categoryId=22
        ),
        status=dict(
            privacyStatus='private'
        )
    )

    insert_request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        onBehalfOfContentOwner=content_owner_id,
        onBehalfOfContentOwnerChannel=channel_id,
        media_body=MediaFileUpload(video.filename, chunksize=-1, resumable=True)
    )
    return resumable_upload(insert_request)


def upload_thumbnail_for_video_if_exists(youtube, content_owner, image_filename, yt_video_id):
    """
    Set a thumbnail for an existing video.

    :param youtube: the youtube connection
    :param content_owner: id of content owner
    :param image_filename: path of thumbnail tu set
    :param yt_video_id: youtube id of video
    :return:
    """
    if image_filename:
        youtube.thumbnails().set(
            videoId=yt_video_id,
            media_body=image_filename,
            onBehalfOfContentOwner=content_owner
        ).execute()
    else:
        log_info("No thumbnail for youtube video id %s" % yt_video_id)


def upload_video_to_youtube(video: VideoModel, registry: RegistryModel):
    """ Triggers the video upload initialization method.
    For each video the gathered metadata will be set
    and the video will be uploaded. In case of an error
    the upload mechanism retries the upload. Uploading
    errors are logged into a mongo db collection.
    """

    if registry.target_platform_video_id or registry.intermediate_state != 'uploading':
        raise Exception('Upload not triggered because registry %s is not in correct state' % registry.registry_id)

    try:
        mapping = MappingModel.create_from_mapping_id(registry.mapping_id)
        youtube, youtube_partner = youtube_inst()
        content_owner = get_content_owner_id(youtube_partner)
        video_id = upload(youtube, video, content_owner, mapping.target_id)

        if video_id and video_id != '':
            upload_thumbnail_for_video_if_exists(youtube, content_owner, video.image_filename, video_id)

            registry.target_platform_video_id = video_id
            registry.set_state_and_persist('active')
        else:
            raise Exception('Upload failed, no youtube_id responded for registry %s' % registry.registry_id)
        return video_id
    except Exception as e:
        raise Exception('Error uploading video of registry entry %s to youtube.' % registry.registry_id, e)


def update_video_on_youtube(video: VideoModel, registry: RegistryModel):
    """ Update metadata of video on youtube. """
    if registry.target_platform_video_id is None or registry.intermediate_state != 'updating':
        raise Exception('Upload not triggered because registry %s is not in correct state' % registry.registry_id)

    if video.hash_code == registry.video_hash_code:
        log_info('Metadata of registry entry %s not changed, so no update needed.' % registry.registry_id)
        return

    youtube_id = registry.target_platform_video_id

    if youtube_id is None:
        raise UpdateError('Youtube_id not found for ' + registry.registry_id)

    try:
        youtube, youtube_partner = youtube_inst()

        video_list_response = youtube.videos().list(
            id=youtube_id,
            part='snippet'
        ).execute()
        if not video_list_response['items']:
            raise UpdateError('Video not found for id ' + youtube_id)

        video_metadata = video_list_response['items'][0]['snippet']

        video_remote_hash = create_metadata_hash(video_metadata)

        if registry.video_hash_code != video_remote_hash:
            log_info('Metadata of video %s was changed on youtube. No update allowed.' % registry.registry_id)
            return

        video_metadata['title'] = video.title
        video_metadata['description'] = video.description
        video_metadata['tags'] = video.keywords

        youtube.videos().update(
            part='snippet',
            onBehalfOfContentOwner=get_content_owner_id(youtube_partner),
            body=dict(
                snippet=video_metadata,
                id=youtube_id
            )
        ).execute()
    except Exception as e:
        raise Exception('Error updating video of registry entry %s on youtube.' % registry.registry_id) from e


def unpublish_video_on_youtube(video: VideoModel, registry: RegistryModel):
    """ Set the privacyStatus to 'private' of the given video if it
    was uploaded to youtube.

    """
    if registry.target_platform_video_id is None or registry.intermediate_state not in ('unpublishing', 'deleting'):
        raise Exception('Unpublishing not triggered because registry %s is not in correct state' % registry.registry_id)

    youtube_id = registry.target_platform_video_id

    if youtube_id is None:
        raise UnpublishError('Youtube_id not found for ' + registry.registry_id)
    try:
        youtube, youtube_partner = youtube_inst()

        video_list_response = youtube.videos().list(
            id=youtube_id,
            part='status'
        ).execute()
        if not video_list_response['items']:
            raise UnpublishError('Video with id %s not found on youtube.' % youtube_id)

        video_list_snippet = video_list_response['items'][0]['status']
        video_list_snippet['privacyStatus'] = 'private'
        youtube.videos().update(
            part='status',
            onBehalfOfContentOwner=get_content_owner_id(youtube_partner),
            body=dict(
                status=video_list_snippet,
                id=youtube_id
            )
        ).execute()
    except Exception as e:
        raise Exception('Error unpublishing video of registry entry %s on youtube.' % registry.registry_id) from e


def delete_video_on_youtube(video: VideoModel, registry: RegistryModel):
    unpublish_video_on_youtube(video, registry)
