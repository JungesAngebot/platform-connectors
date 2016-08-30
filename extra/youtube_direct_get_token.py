#!/usr/bin/env python3
import json

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

# ,
# 'https://www.googleapis.com/auth/youtube',
# 'https://www.googleapis.com/auth/youtube.force-ssl',
# 'https://www.googleapis.com/auth/youtubepartner'