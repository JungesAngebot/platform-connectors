import hashlib
import time
import traceback
from random import random

import httplib2
from commonspy.logging import log_info, log_error, log_debug
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from connector.db import VideoModel, RegistryModel

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
    # if 'tags' in metadata:
    #        video_hash_code.update(bytes(metadata['tags'].encode('UTF-8')))

    return video_hash_code.hexdigest()


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
            if response is not None:
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
        # chunk size: 512 MB
        media_body=MediaFileUpload(video.filename, chunksize=512 * 1024 * 1024, resumable=True)
    )
    return resumable_upload(insert_request)


def upload_thumbnail_for_video_if_exists(youtube, content_owner, image_filename, yt_video_id, registry: RegistryModel):
    """
    Set a thumbnail for an existing video.

    :param youtube: the youtube connection
    :param content_owner: id of content owner
    :param image_filename: path of thumbnail tu set
    :param yt_video_id: youtube id of video
    :return:
    """
    try:
        if image_filename:
            youtube.thumbnails().set(
                videoId=yt_video_id,
                media_body=image_filename,
                onBehalfOfContentOwner=content_owner
            ).execute()
        else:
            log_info("No thumbnail for youtube video id %s" % yt_video_id)

    except Exception as e:
        registry.message = 'Error uploading thumb of registry entry %s to youtube. Error: %s' % (
            registry.registry_id, e)
        log_error(registry.message)
        log_error(e.__traceback__)


def upload_video_to_youtube(youtube, video: VideoModel, registry: RegistryModel, content_owner, channel_id):
    """ Triggers the video upload initialization method.
    For each video the gathered metadata will be set
    and the video will be uploaded. In case of an error
    the upload mechanism retries the upload. Uploading
    errors are logged into a mongo db collection.
    """

    try:
        video_id = upload(youtube, video, content_owner, channel_id)

        if video_id and video_id != '':
            registry.target_platform_video_id = video_id
            upload_thumbnail_for_video_if_exists(youtube, content_owner, video.image_filename, video_id, registry)
            registry.set_state_and_persist('active')
        else:
            raise Exception('Upload failed, no youtube_id responded for registry %s' % registry.registry_id)

    except Exception as e:
        raise Exception('Error uploading video of registry entry %s to youtube.' % registry.registry_id) from e

    return registry.target_platform_video_id


def update_video_on_youtube(youtube, video: VideoModel, registry: RegistryModel, content_owner):
    """ Update metadata of video on youtube. """

    if video.hash_code == registry.video_hash_code:
        log_info('Metadata of registry entry %s not changed, so no update needed.' % registry.registry_id)
        return

    youtube_id = registry.target_platform_video_id

    if youtube_id is None:
        raise UpdateError('Youtube_id not found for ' + registry.registry_id)

    try:
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
            onBehalfOfContentOwner=content_owner,
            body=dict(
                snippet=video_metadata,
                id=youtube_id
            )
        ).execute()
    except Exception as e:
        raise Exception('Error updating video of registry entry %s on youtube.' % registry.registry_id) from e


def unpublish_video_on_youtube(youtube, video: VideoModel, registry: RegistryModel, content_owner):
    """ Set the privacyStatus to 'private' of the given video if it
    was uploaded to youtube.
    """
    youtube_id = registry.target_platform_video_id

    if youtube_id is None:
        raise UnpublishError('Youtube_id not found for ' + registry.registry_id)
    try:
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
            onBehalfOfContentOwner=content_owner,
            body=dict(
                status=video_list_snippet,
                id=youtube_id
            )
        ).execute()
    except Exception as e:
        raise Exception('Error unpublishing video of registry entry %s on youtube.' % registry.registry_id) from e


def claim_video_on_youtube(youtube_partner, content_owner_id, target_platform_video_id, video: VideoModel, registry: RegistryModel):
    """ Performs all steps to claim a video on the youtube platform and upload a referenc.

    After these steps have been performed successfully a UploadPolicy and a MatchPolicy are set for the
    video content. Thus, all videos with the same content are automatically claimed and our policies 'track' are
    applied to it.
    """
    try:
        log_info("Setting policies for video: %s" % video.__dict__)
        asset_id = create_asset(youtube_partner, content_owner_id, video.title, video.description)
        set_asset_ownership(youtube_partner, content_owner_id, asset_id)
        claim_id = claim_video(youtube_partner, content_owner_id, asset_id, target_platform_video_id)
        # The following methods are required to set the match policy for a video.
        # Currently we do not set this automatically.
        # set_match_policy(youtube_partner, asset_id)
        # create_reference(youtube_partner, asset_id, video.filename)
    except Exception as e:
        log_error('Error setting policies on video with id "%s" and id on target platform "%s". Error %s' % (video.video_id, target_platform_video_id, e))
        log_error(traceback.format_tb(e.__traceback__))
        registry.set_message_and_persist("Warning while setting policies: %s" % e)
        raise SuccessWithWarningException() from e


def create_asset(youtube_partner, content_owner_id, title, description):
    """ This creates a new asset corresponding to a video on the web.
    The asset is linked to the corresponding YouTube video via a
    claim that will be created later.
    """
    body = dict(
        type="web",
        metadata=dict(
            title=title,
            description=description
        )
    )

    assets_insert_response = youtube_partner.assets().insert(
        onBehalfOfContentOwner=content_owner_id,
        body=body
    ).execute()
    log_info("Asset created: %s" % assets_insert_response)
    return assets_insert_response["id"]


def set_asset_ownership(youtube_partner, content_owner_id, asset_id):
    # This specifies that content_owner_id owns 100% of the asset worldwide.
    body = dict(
        general=[dict(
            owner=content_owner_id,
            ratio=100,
            type="exclude",
            territories=[]
        )]
    )

    youtube_partner.ownership().update(
        onBehalfOfContentOwner=content_owner_id,
        assetId=asset_id,
        body=body
    ).execute()


def claim_video(youtube_partner, content_owner_id, asset_id, video_id):
    """ Creates a claim for the video.
    This makes sure the UsagePolicy is set correctly.
    """
    log_info("Claiming video %s for asset %s." % (video_id, asset_id))
    policy = dict(
        id='S167739528016254'
    )

    body = dict(
        assetId=asset_id,
        videoId=video_id,
        policy=policy,
        contentType="audiovisual"
    )

    claims_insert_response = youtube_partner.claims().insert(
        onBehalfOfContentOwner=content_owner_id,
        body=body
    ).execute()

    log_info("Video claimed. %s" % claims_insert_response)
    return claims_insert_response["id"]

# We do not set the match policy automatically. Hence, the following methods are currently not required
# As this behaviour may change in the future the methods are currenly just commentet out.
#
# def set_match_policy(youtube_partner, asset_id):
#     match_policy_response = youtube_partner.assetMatchPolicy().update(
#         assetId=asset_id,
#         body={
#             'policyId': 'S167739528016254'
#         }
#     ).execute()
#     log_info('Added match policy: %s' % match_policy_response)
#     return match_policy_response
#
#
# def create_reference_from_claim(youtube_partner, claim_id, content_owner):
#     """ Creates a reference from the specified claim_id
#
#     needs the video to be completely processed on youtube. Currently this is not an option in our workflow.
#     """
#     reference_response = youtube_partner.references().insert(
#         claimId=claim_id,
#         onBehalfOfContentOwner=content_owner,
#         body={
#             'contentType':'audiovisual'
#         }
#     ).execute()
#     log_info('Created reference: %s' % reference_response)
#     return reference_response
#
#
# def create_reference(youtube_partner, asset_id, reference_file):
#     """ Create a reference by uploading the video content.
#     Uploads the specified reference_file to youtube so that a reference object is created. The reference file
#     usually is the same file as the video to be uploaded.
#     """
#     log_info("Uploading reference for asset %s. File: %s" % (asset_id, reference_file))
#     reference_service = youtube_partner.references()
#     media = MediaFileUpload(reference_file, resumable=True)
#     request = reference_service.insert(
#         body={'assetId': asset_id, 'contentType': 'audiovisual'},
#         media_body=media)
#     status, response = request.next_chunk()
#     while response is None:
#         status, response = request.next_chunk()
#     log_info('Reference for asset %s has been created: %s' % (asset_id, response))
#


class SuccessWithWarningException(Exception):
    """ Raised if in some step a warnings message should remain in the registry database but the overall state
    sould still be set to 'active'.
    """
    def __init__(self, *args, **kwargs):
        pass