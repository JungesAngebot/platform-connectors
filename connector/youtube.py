import sys

import httplib2
from googleapiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets, Storage
from oauth2client.tools import run_flow

from connector import APP_ROOT

INVALID_CREDENTIALS = b"Invalid Credentials"

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE_CONTENT_ID_API_SERVICE_NAME = "youtubePartner"
YOUTUBE_CONTENT_ID_API_VERSION = "v1"

youtube_scopes = (
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtubepartner'
)


def create_youtube_instance():
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
