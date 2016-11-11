import traceback

from commonspy.logging import log_error, log_info
from flask import Flask, jsonify

from connector import api
from connector.db import RegistryModel
from connector.states import Downloading, Updating, Unpublish, Deleting, Active


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api)
    return app


@api.route('/update/<string:registry_id>')
def update_request(registry_id):
    log_info('Going to execute update / upload for registry id %s' % registry_id)
    try:
        registry_model = RegistryModel.create_from_registry_id(registry_id)
        if registry_model.status == 'notified':
            log_info('New video detected. Starting upload workflow. registry id: %s' % registry_id)
            Downloading.create_downloading_state(registry_model).run()
        elif registry_model.status == 'active':
            if registry_model.captions_uploaded:
                # log_info('Captions already uploaded for video. Updating an existing video is currently not supported. Ignoring request. registry id: %s' % registry_id)
                Updating.create_updating_state(registry_model).run()
            else:
                log_info('Captions will be uploaded for video if set in Kaltura. Existing video will be updated. registry id: %s' % registry_id)
                Updating.create_updating_state(registry_model).run()
        elif registry_model.status == 'inactive':
            log_info('Detected inactive video. Activating it again. registry id: %s' % registry_id)
            Active.create_active_state(registry_model).run()
        elif registry_model.status == 'error':
            log_info('Previous workflow ended with error. Retrying... registry id: %s' % registry_id)
            if registry_model.intermediate_state == 'downloading' or registry_model.intermediate_state == 'uploading':
                log_info('Retrying upload. registry id: %s' % registry_id)
                Downloading.create_downloading_state(registry_model).run()
            elif registry_model.intermediate_state == 'updating':
                log_info('Retrying updating... registry id: %s' % registry_id)
                Updating.create_updating_state(registry_model).run()
            else:
                log_info('No proper intermediate state found. Starting download... registry id: %s' % registry_id)
                Downloading.create_downloading_state(registry_model).run()
    except Exception as e:
        log_error(traceback.format_tb(e.__traceback__))
        traceback.print_tb(e.__traceback__)
        return jsonify({'status': 'error'})
    return jsonify({'status': 'success'})


@api.route('/unpublish/<string:registry_id>')
def unpublish_request(registry_id):
    log_info('Going to execute unpublish event for registry id %s.' % registry_id)
    try:
        registry_model = RegistryModel.create_from_registry_id(registry_id)
        if registry_model.status == 'active' or registry_model.status == 'error':
            log_info('Unpublishing video... registry id: %s' % registry_id)
            Unpublish.create_unpublish_state(registry_model).run()
    except Exception as e:
        log_error(traceback.format_tb(e.__traceback__))
        traceback.print_tb(e.__traceback__)
        return jsonify({'status': 'error'})
    return jsonify({'status': 'success'})


@api.route('/delete/<string:registry_id>')
def delete_request(registry_id):
    log_info('Going to delete video with registry id %s.' % registry_id)
    try:
        registry_model = RegistryModel.create_from_registry_id(registry_id)
        Deleting.create_deleting_state(registry_model).run()
    except Exception as e:
        log_error(traceback.format_tb(e.__traceback__))
        traceback.print_tb(e.__traceback__)
        return jsonify({'status': 'error'})
    return jsonify({'status': 'success'})
