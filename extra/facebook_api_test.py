#!/usr/bin/env python3
from connector.db import VideoModel, RegistryModel
from connector.facebook import upload_video_to_facebook

video = VideoModel()
video.title = "Test-Title 2"
video.description = "Test-Description 2"
video.keywords = "test,cool,nice,slow"
video.download_url = "https://cdnsecakmi.kaltura.com/p/1985051/sp/198505100/raw/entry_id/1_vlep34nc/version/0"
video.image_filename = "/home/swrlnxdef/Downloads/est02.png"
registry = RegistryModel()
registry.mapping_id = '5784e74283446200011bd4f8'
registry.status = 'notified'
registry.intermediate_state = 'uploading'

upload_video_to_facebook(video, registry)
