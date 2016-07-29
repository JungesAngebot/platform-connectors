#!/usr/bin/env python3
import argparse
import os
import random
import urllib.request

import sys

import httplib2
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials
httplib2.debuglevel = 4
APP_ROOT = os.path.dirname(os.path.abspath(__file__)).replace(os.sep + 'extra', '')

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


def youtube_instance():
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        APP_ROOT + '/config/client_secrets.json', scopes=youtube_scopes
    )

    http = httplib2.Http()
    http = credentials.authorize(http)

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, http=http)

    youtube_partner = build(YOUTUBE_CONTENT_ID_API_SERVICE_NAME, YOUTUBE_CONTENT_ID_API_VERSION, http=http)

    return youtube, youtube_partner


def content_owner_id(youtube_partner):
    try:
        content_owners_list_response = youtube_partner.contentOwners().list(
            fetchMine=True
        ).execute()
    except HttpError as e:
        raise Exception() from e

    return content_owners_list_response['items'][0]['id']


def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    video_id = None

    while response is None:
        try:
            status, response = insert_request.next_chunk()
            if 'id' in response:
                video_id = response['id']
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                pass
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            pass
        if error is not None:
            retry += 1
            if retry > 10:
                exit(-1)
            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            time.sleep(sleep_seconds)
    return video_id


def upload():
    body = dict(
        snippet=dict(
            title='Upload test 2',
            description='Description of upload test 2',
            categoryId=22
        ),
        status=dict(
            privacyStatus='private'
        )
    )

    insert_request = youtube_instance()[0].videos().insert(
        part=','.join(body.keys()),
        body=body,
        onBehalfOfContentOwner=content_owner_id(youtube_instance()[1]),
        onBehalfOfContentOwnerChannel='UCMf4KYUStK86PiTd4An1jvg',
        # chunk size: 100
        media_body=MediaFileUpload('binary', chunksize=512 * 1024 * 1024, resumable=True)
    )

    return resumable_upload(insert_request)


def reporthook(block_num, block_size, total_size):
    read_so_far = block_num * block_size
    if total_size > 0:
        percent = read_so_far * 1e2 / total_size
        s = '\r%5.1f%% %*d / %d' % (
            percent, len(str(total_size)), read_so_far, total_size)
        sys.stderr.write(s)
        if read_so_far >= total_size:
            sys.stderr.write('\n')
    else:
        sys.stderr.write('read %d\n' % (read_so_far,))


parser = argparse.ArgumentParser()

parser.add_argument('-url')

args = parser.parse_args()

if args.url:
    # urllib.request.urlretrieve(args.url, 'binary', reporthook)
    upload()
