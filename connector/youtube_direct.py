import urllib

import httplib2
import os
import random
import sys
import time

import requests
from commonspy.logging import log_info, log_error
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets, AccessTokenCredentials
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

from connector import APP_ROOT
from connector import config
from connector.db import VideoModel, RegistryModel, MappingModel

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google Developers Console at
# https://console.developers.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "client_secrets.json"

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the Developers Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


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


def get_authenticated_service(target_id):
    access_token = access_token_from_refresh_token(target_id)
    credentials = AccessTokenCredentials(access_token, "MyAgent/1.0", None)

    if credentials is None or credentials.invalid:
        raise Exception('Cannot create access_token from refresh_token.')

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                 http=credentials.authorize(httplib2.Http()))


def upload(youtube, video: VideoModel, content_owner, channel_id):
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
        part=",".join(body.keys()),
        body=body,
        onBehalfOfContentOwner=content_owner,
        onBehalfOfContentOwnerChannel=channel_id,
        media_body=MediaFileUpload(video.filename, chunksize=512 * 1024 * 1024, resumable=True)
    )

    return resumable_upload(insert_request)


# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    video_id = None
    while response is None:
        try:
            log_info("Uploading file...")
            status, response = insert_request.next_chunk()
            if 'id' in response:
                video_id = response['id']
                log_info("Video id '%s' was successfully uploaded." % response['id'])
            else:
                raise Exception("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                     e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            log_error('Error during upload, retryingit: Message %s' % error)
            retry += 1
            if retry > MAX_RETRIES:
                raise Exception("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            log_info("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)
    return video_id


def upload_thumbnail_for_video_if_exists(youtube, image_filename, yt_video_id, registry: RegistryModel):
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
            ).execute()
        else:
            log_info("No thumbnail for youtube video id %s" % yt_video_id)

    except Exception as e:
        registry.message = 'Error uploading thumb of registry entry %s to youtube. Error: %s' % (registry.registry_id, e)
        log_error(registry.message)
        log_error(e.__traceback__)



def upload_video_to_youtube_direct(video: VideoModel, registry: RegistryModel):
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
        youtube = get_authenticated_service(mapping.target_id)
        video_id = upload(youtube, video, None, None)

        if video_id and video_id != '':
            registry.target_platform_video_id = video_id
            upload_thumbnail_for_video_if_exists(youtube, video.image_filename, video_id, registry)
            registry.set_state_and_persist('active')
        else:
            raise Exception('Upload failed, no youtube_id responded for registry %s' % registry.registry_id)

    except Exception as e:
        raise Exception('Error uploading video of registry entry %s to youtube.' % registry.registry_id) from e

    return registry.target_platform_video_id




