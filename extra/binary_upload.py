#!/usr/bin/env python3
import argparse
import os
import urllib.request

import sys

import httplib2
from oauth2client.service_account import ServiceAccountCredentials

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
    urllib.request.urlretrieve(args.url, 'binary', reporthook)
