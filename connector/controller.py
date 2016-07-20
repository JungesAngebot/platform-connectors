from commonspy.logging import log_info, log_error

from connector.db import change_status_of_process, get_registry_entry_by_registry_id, get_asset_metadata
from connector.youtube import upload_video_to_youtube
from connector.facebook import upload_video_to_facebook
import urllib.request


def gather_metadata(registry_id):
    change_status_of_process(registry_id, 'gathering metadata')
    registry = get_registry_entry_by_registry_id(registry_id)
    asset = get_asset_metadata(registry.videoId)
    return asset, registry


def download_video(asset, registry_id):
    change_status_of_process(registry_id, 'downloading')
    log_info('Going to download video %s.' % asset.download_url)
    try:
        urllib.request.urlretrieve(asset.download_url, asset.sourceId + '.mpeg')
    except Exception as e:
        change_status_of_process(registry_id, 'error')
        log_error("Download of video %s from kaltura failed." % asset.sourceId)


def upload_video(registry_id):
    registry = get_registry_entry_by_registry_id(registry_id)

    if registry.status not in ('notified', 'error'):
        log_error('Upload canceled for registry entry %s because status is %s' % (registry_id, registry.status))
        raise Exception('Upload canceled for registry entry %s because status is %s' % (registry_id, registry.status))

    asset, registry = gather_metadata(registry_id)

    if 'targetPlatform' in registry:
        download_video(asset, registry_id)

        if 'youtube' == registry['targetPlatform']:
            upload_video_to_youtube(asset)
        elif 'facebook' == registry['targetPlatform']:
            upload_video_to_facebook(asset, None)


"""
- _id (= videoId-categoryId)
- videoId
- categoryId
- status (notified, metadatagathering, downloading, uploading, error, success)
- message
- targetPlarform
- targetPlatformVideoId
- mappingId
"""
