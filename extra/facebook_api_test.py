#!/usr/bin/env python3
import hashlib

from connector.db import VideoModel, RegistryModel
from connector.facebook import upload_video_to_facebook, update_video_on_facebook, unpublish_video_on_facebook, \
    delete_video_on_facebook


def createHash(video:VideoModel):
    video_hash_code = hashlib.md5()
    video_hash_code.update(bytes(video.title.encode('UTF-8')))
    video_hash_code.update(bytes(video.description.encode('UTF-8')))
    return video_hash_code.hexdigest()

video = VideoModel()
video.title = "Test-Title 2"
video.description = "Test-Description 2"
video.keywords = "test,cool,nice,slow"
video.download_url = "https://cdnsecakmi.kaltura.com/p/1985051/sp/198505100/raw/entry_id/1_vlep34nc/version/0"
video.image_filename = "/home/swrlnxdef/Downloads/est02.png"


video.hash_code = createHash(video)

registry = RegistryModel()
registry.mapping_id = '5784e74283446200011bd4f8'
registry.status = 'notified'
registry.intermediate_state = 'uploading'

upload_video_to_facebook(video, registry)
registry.video_hash_code = video.hash_code
video.title = "Test-Title 3"
video.hash_code = createHash(video)
registry.intermediate_state='updating'
update_video_on_facebook(video, registry)
registry.intermediate_state='unpublishing'
unpublish_video_on_facebook(video, registry)
registry.intermediate_state='deleting'
delete_video_on_facebook(video, registry)
