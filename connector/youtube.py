import logging
import sys
import time
from random import random

import httplib2
from commonspy.logging import logger, Message
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

from connector import APP_ROOT
from connector.db import MessageDbo, RegistryDbo

""" This module handles youtube video upload, update
and unpublish. Videos are only uploaded to multi
channel networks. Single channel upload (for non
youtube partners) is not supported.
"""

INVALID_CREDENTIALS = b"Invalid Credentials"

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE_CONTENT_ID_API_SERVICE_NAME = "youtubePartner"
YOUTUBE_CONTENT_ID_API_VERSION = "v1"

youtube_scopes = (
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtubepartner'
)


class UpdateError(Exception):
    """ Error during update operations. """

    def __init__(self, *args, **kwargs):
        pass


class UnpublishError(Exception):
    """ Error during unpublish operations. """

    def __init__(self, *args, **kwargs):
        pass


def get_content_owner_id(youtube_partner):
    """ Function to gather the youtube content owner
    id. This id is required to upload a video to
    a multi channel network on youtube.
    """
    content_owners_list_response = None
    try:
        content_owners_list_response = youtube_partner.contentOwners().list(
            fetchMine=True
        ).execute()
    except HttpError as e:
        if INVALID_CREDENTIALS in e.content:
            logging.error("The request is not authorized by a Google Account that "
                          "is linked to a YouTube content owner. Please delete '%s' and "
                          "re-authenticate with a YouTube content owner account." %
                          "{0}-oauth2.json".format(sys.argv[0]))
            raise

    return content_owners_list_response["items"][0]["id"]


def youtube_inst():
    """ Authenticates at the youtube api.
    The connector will always upload to multi channel
    networks on youtube. Therefor two youtube
    api scopes are required:
    - Standard Youtube Scope (full read / write access)
    - Youtube partner scope
    """
    flow = flow_from_clientsecrets(
        APP_ROOT + '/config/client_secret.json',
        scope=' '.join(youtube_scopes),
        message='No client secrets provided.'
    )

    storage = Storage("{0}-oauth2.json".format(sys.argv[0]))
    credentials = storage.get()
    if credentials is None:
        credentials = run_flow(flow, storage)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                    http=credentials.authorize(httplib2.Http()))

    youtube_partner = build(YOUTUBE_CONTENT_ID_API_SERVICE_NAME,
                            YOUTUBE_CONTENT_ID_API_VERSION, http=credentials.authorize(httplib2.Http()))

    return youtube, youtube_partner


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
            print("Uploading file...")
            status, response = insert_request.next_chunk()
            if 'id' in response:
                video_id = response['id']
                print("Video id '%s' was successfully uploaded." % video_id)
            else:
                exit("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            print(e.resp)
            raise

        if error is not None:
            print(error)
            retry += 1
            if retry > 10:
                exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)
    return video_id


def initialize_upload(youtube, options, channel_id):
    """ initialized the youtube video upload. This
    mechanism uses the youtube partner authentication / client
    and is only able to upload videos to a multi channel
    youtube network.

    :param youtube: youtube client (standard and partner)
    :param options: video options and metadata
    :param channel_id: the target channel
    :return: resumable upload
    """
    tags = options['keywords']
    # if options['keywords']:
    #     tags = options['keywords'].split(',')
    body = dict(
        snippet=dict(
            title=options['title'],
            description=options['description'],
            tags=tags,
            categoryId=options['category']
        ),
        status=dict(
            privacyStatus=options['privacy_status']
        )
    )
    try:
        inser_request = youtube[0].videos().insert(
            part=','.join(body.keys()),
            body=body,
            onBehalfOfContentOwner=get_content_owner_id(youtube[1]),
            onBehalfOfContentOwnerChannel=channel_id,
            media_body=MediaFileUpload(options['filename'], chunksize=-1, resumable=True)
        )
        return resumable_upload(inser_request)
    except FileNotFoundError as e:
        message_dbo = MessageDbo()
        message_dbo.add_upload_error(options['filename'], options['title'], e.__str__())
    return None


def upload_video_to_youtube(video):
    """ Triggers the video upload initialization method.
    For each video the gathered metadata will be set
    and the video will be uploaded. In case of an error
    the upload mechanism retries the upload. Uploading
    errors are logged into a mongo db collection.
    """
    options = dict(
        keywords=video.tags,
        title=video.title,
        description=video.description,
        category=22,
        privacy_status='private',
        filename=video.filename
    )
    youtube = youtube_inst()
    message_dbo = MessageDbo()
    try:
        video_id = initialize_upload(youtube, options, video.target_channel)

        if video_id is None or video_id == '':
            message_dbo.add_upload_error(video.filename, video.title, 'Unable to upload video to youtube.')
        else:
            registry_dbo = RegistryDbo()
            registry_dbo.register(video.video_id, video_id, options)
            message_dbo.add_upload_success(video.filename, video.title)
        return video_id
    except HttpError as e:
        message_dbo.add_upload_error(video.filename, video.title, e)
    return None


def update_video_on_youtube(video):
    """ Update metadata of video on youtube. """
    registry_dbo = RegistryDbo()

    youtube_id = registry_dbo.youtube_id_by_video_id(video.video_id)

    if youtube_id is None:
        raise UpdateError('Youtube_id not found for ' + video.video_id)

    youtube = youtube_inst()

    video_list_response = youtube[0].videos().list(
        id=youtube_id,
        part='snippet'
    ).execute()
    if not video_list_response['items']:
        raise UpdateError('Video not found for id ' + youtube_id)

    video_list_snippet = video_list_response['items'][0]['snippet']
    video_list_snippet['title'] = video.title
    video_list_snippet['description'] = video.description
    video_list_snippet['categoryId'] = 22

    if "tags" not in video_list_snippet:
        video_list_snippet["tags"] = []
    video_list_snippet["tags"].append([])

    youtube[0].videos().update(
        part='snippet',
        onBehalfOfContentOwner=get_content_owner_id(youtube[1]),
        body=dict(
            snippet=video_list_snippet,
            id=youtube_id
        )
    ).execute()


def log_video_state(youtube_video_id):
    """ Function to log the state of a video already uploaded to video.
    If a video is already uploaded to youtube, the connector will not upload it
    again. Instead it will
    """
    youtube = youtube_inst()[0]
    result = youtube.videos().list(
        part='status',
        id=youtube_video_id
    ).execute()
    video = result['items'][0]
    logger.debug(Message('Youtube already uploaded: Privacy Status: ' + video['status']['privacyStatus']).__dict__)
    logger.debug(Message('Youtube already uploaded: Upload Status: ' + video['status']['uploadStatus']).__dict__)
    logger.debug(Message('Youtube already uploaded: License Status: ' + video['status']['license']).__dict__)


def unpublish_video_on_youtube(video):
    """ Set the privacyStatus to 'private' of the given video if it
    was uploaded to youtube.

    If the video was not uploaded an UnpublishError is thrown.
    """
    registry_dbo = RegistryDbo()

    youtube_id = registry_dbo.youtube_id_by_video_id(video.video_id)

    if youtube_id is None:
        raise UnpublishError('Youtube_id not found for ' + video.video_id)

    youtube = youtube_inst()

    video_list_response = youtube[0].videos().list(
        id=youtube_id,
        part='status'
    ).execute()
    if not video_list_response['items']:
        raise UnpublishError('Video with id ' + youtube_id + " not found on youtube.")

    video_list_snippet = video_list_response['items'][0]['status']
    video_list_snippet['privacyStatus'] = 'private'
    youtube[0].videos().update(
        part='status',
        onBehalfOfContentOwner=get_content_owner_id(youtube[1]),
        body=dict(
            status=video_list_snippet,
            id=youtube_id
        )
    ).execute()


def check_video_upload_successful(youtube_video_id):
    youtube = youtube_inst()

    response = youtube[0].videos().list(
        part='status',
        id=youtube_video_id
    ).execute()

    print(response['status']['uploadStatus'])