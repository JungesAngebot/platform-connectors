#!/usr/bin/env python3
import hashlib

from connector import youtube
from connector.db import VideoModel, RegistryModel
from connector.youtube import upload_video_to_youtube


def createHash(video:VideoModel):
    video_hash_code = hashlib.md5()
    video_hash_code.update(bytes(video.title.encode('UTF-8')))
    video_hash_code.update(bytes(video.description.encode('UTF-8')))
    return video_hash_code.hexdigest()

video = VideoModel()
video.title = "Test-Title 2"
video.description = "Test-Description 2"
video.keywords = "test,cool,nice,slow"
video.filename = "/home/swrlnxdef/Downloads/Malte_running.mp4"
video.download_url = "https://cdnsecakmi.kaltura.com/p/1985051/sp/198505100/raw/entry_id/1_vlep34nc/version/0"
video.image_filename = "/home/swrlnxdef/Downloads/est02.png"


video.hash_code = createHash(video)

registry = RegistryModel()
registry.mapping_id = '575abf5ce39baa00011dbbb2'
registry.status = 'notified'
registry.intermediate_state = 'uploading'

upload_video_to_youtube(video, registry)


