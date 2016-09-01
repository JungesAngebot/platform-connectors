#!/usr/bin/env python3

"""
This script is used for generating youtube refresh_tokens. These tokens are required for uploading videos
to youtube channels that are not part of the Junges Angebot MCN.

To generate a token perform the following steps:
 1) make sure the file config/client_secret_installed.json is present, if not copy it from the installer Project from GitHub
 2) Start the script
 3) The script prints out a link. Copy it and send it to the person owning the youtube channel.
 4) The channel owner opens the link in the browser and logs in with his credentials and acknowledges the scopes required for the uploader.
 5) The channel owner now sees a page presenting a token. He has to send this token to us.
 6) Copy the token to the command prompt shown by this script.
 7) The script prints out the refresh_token. This now can be copied and pasted to the platform connector mappings

"""

from oauth2client import client

flow = client.flow_from_clientsecrets(
    '../config/client_secret_installed.json',
    scope=['https://www.googleapis.com/auth/youtube.upload'],
    redirect_uri='urn:ietf:wg:oauth:2.0:oob')

auth_uri = flow.step1_get_authorize_url()

print(auth_uri)

auth_code = input("Auth Code: ")

credentials = flow.step2_exchange(auth_code)


print(credentials.refresh_token)
