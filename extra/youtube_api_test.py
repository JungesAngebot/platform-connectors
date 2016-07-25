#!/usr/bin/env python3

from connector import youtube

youtube_api, youtube_partner_api = youtube.youtube_inst()

youtube.get_content_owner_id(youtube_partner_api)
