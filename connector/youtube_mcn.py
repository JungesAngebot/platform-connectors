import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials

from connector import APP_ROOT
from connector.db import RegistryModel, MappingModel
from connector.db import VideoModel
from connector.youtube import youtube_scopes, YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, \
    YOUTUBE_CONTENT_ID_API_SERVICE_NAME, YOUTUBE_CONTENT_ID_API_VERSION, upload_video_to_youtube, \
    update_video_on_youtube, unpublish_video_on_youtube, claim_video_on_youtube, SuccessWithWarningException


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


def upload_video_to_youtube_mcn(video: VideoModel, registry: RegistryModel):
    if registry.target_platform_video_id or registry.intermediate_state != 'uploading':
        raise Exception('Upload not triggered because registry %s is not in correct state' % registry.registry_id)

    try:
        mapping = MappingModel.create_from_mapping_id(registry.mapping_id)
        youtube, youtube_partner = youtube_inst()
        content_owner = get_content_owner_id(youtube_partner)
        channel_id = mapping.target_id
        video_id = upload_video_to_youtube(youtube, video, registry, content_owner, channel_id)
        claim_video_on_youtube(youtube_partner, content_owner, video_id, video, registry)
    except SuccessWithWarningException as warning:
        raise warning
    except Exception as e:
        raise Exception('Error initializing MCN youtube upload request for entry %s.' % registry.registry_id) from e


def update_video_on_youtube_mcn(video: VideoModel, registry: RegistryModel):
    if registry.target_platform_video_id is None or registry.intermediate_state != 'updating':
        raise Exception('Upload not triggered because registry %s is not in correct state' % registry.registry_id)
    try:
        youtube, youtube_partner = youtube_inst()
        content_owner = get_content_owner_id(youtube_partner)
        update_video_on_youtube(youtube, video, registry, content_owner)
    except Exception as e:
        raise Exception('Error initializing MCN youtube update request for entry %s.' % registry.registry_id) from e


def unpublish_video_on_youtube_mcn(video: VideoModel, registry: RegistryModel):
    if registry.target_platform_video_id is None or registry.intermediate_state not in ('unpublishing', 'deleting'):
        raise Exception('Unpublishing not triggered because registry %s is not in correct state' % registry.registry_id)
    try:
        youtube, youtube_partner = youtube_inst()
        content_owner = get_content_owner_id(youtube_partner)
        unpublish_video_on_youtube(youtube, video, registry, content_owner)
    except Exception as e:
        raise Exception('Error initializing MCN youtube unpublish request for entry %s.' % registry.registry_id) from e


def delete_video_on_youtube_mcn(video: VideoModel, registry: RegistryModel):
    unpublish_video_on_youtube_mcn(video, registry)

