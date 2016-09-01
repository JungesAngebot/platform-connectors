import urllib

import httplib2
import requests
from googleapiclient.discovery import build
from oauth2client.client import AccessTokenCredentials

from connector import config
from connector.db import VideoModel, RegistryModel, MappingModel
from connector.youtube import YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, upload_video_to_youtube, \
    update_video_on_youtube, unpublish_video_on_youtube


def youtube_direct_inst(target_id):
    access_token = access_token_from_refresh_token(target_id)
    credentials = AccessTokenCredentials(access_token, "MyAgent/1.0", None)

    if credentials is None or credentials.invalid:
        raise Exception('Cannot create access_token from refresh_token.')

    http = httplib2.Http()
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                    http=credentials.authorize(http))

    return youtube


def access_token_from_refresh_token(refresh_token):
    data = urllib.parse.urlencode({
        'grant_type': 'refresh_token',
        'client_id': config.property('youtube.client_id'),
        'client_secret': config.property('youtube.client_secret'),
        'refresh_token': refresh_token
    })
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    response = requests.post(config.property('youtube.token_uri'), data=data, headers=headers).json()
    if 'error' in response:
        raise Exception('Error getting access_token: %s' % response['error'])

    return response['access_token']


def upload_video_to_youtube_direct(video: VideoModel, registry: RegistryModel):
    if registry.target_platform_video_id or registry.intermediate_state != 'uploading':
        raise Exception('Upload not triggered because registry %s is not in correct state' % registry.registry_id)

    try:
        mapping = MappingModel.create_from_mapping_id(registry.mapping_id)
        youtube = youtube_direct_inst(mapping.target_id)
        content_owner = None
        channel_id = None
        upload_video_to_youtube(youtube, video, registry, content_owner, channel_id)
    except Exception as e:
        raise Exception('Error initializing direct youtube upload request for entry %s.' % registry.registry_id) from e


def update_video_on_youtube_direct(video: VideoModel, registry: RegistryModel):
    if registry.target_platform_video_id is None or registry.intermediate_state != 'updating':
        raise Exception('Upload not triggered because registry %s is not in correct state' % registry.registry_id)
    try:
        mapping = MappingModel.create_from_mapping_id(registry.mapping_id)
        youtube = youtube_direct_inst(mapping.target_id)
        content_owner = None
        update_video_on_youtube(youtube, video, registry, content_owner)
    except Exception as e:
        raise Exception('Error initializing direct youtube update request for entry %s.' % registry.registry_id) from e


def unpublish_video_on_youtube_direct(video: VideoModel, registry: RegistryModel):
    if registry.target_platform_video_id is None or registry.intermediate_state not in ('unpublishing', 'deleting'):
        raise Exception('Unpublishing not triggered because registry %s is not in correct state' % registry.registry_id)
    try:
        mapping = MappingModel.create_from_mapping_id(registry.mapping_id)
        youtube = youtube_direct_inst(mapping.target_id)
        content_owner = None
        unpublish_video_on_youtube(youtube, video, registry, content_owner)
    except Exception as e:
        raise Exception('Error initializing direct youtube unpublish request for entry %s.' % registry.registry_id) from e


def delete_video_on_youtube_direct(video: VideoModel, registry: RegistryModel):
    unpublish_video_on_youtube_direct(video, registry)
