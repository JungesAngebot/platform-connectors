#!/usr/bin/env python3
from connector.db import VideoModel, RegistryModel
from connector.facebook import upload_video_to_facebook

video = VideoModel()
video.title = "Test-Title 1"
video.description = "Test-Description 1"

registry = RegistryModel()
registry.mapping_id = '5784e74283446200011bd4f8'

print(upload_video_to_facebook(video, registry))

