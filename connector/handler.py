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
            log_info('New video detected. Starting upload workflow.')
            Downloading.create_downloading_state(registry_model).run()
        elif registry_model.status == 'active':
            log_info('Existing video will be updated.')
            Updating.create_updating_state(registry_model).run()
        elif registry_model.status == 'inactive':
            log_info('Detected inactive video. Activating it again.')
            Active.create_active_state(registry_model).run()
        elif registry_model.status == 'error':
            log_info('Previous workflow ended with error. Retrying...')
            if registry_model.intermediate_state == 'downloading' or registry_model.intermediate_state == 'uploading':
                log_info('Retrying upload.')
                Downloading.create_downloading_state(registry_model).run()
            elif registry_model.intermediate_state == 'updating':
                log_info('Retrying updating...')
                Updating.create_updating_state(registry_model).run()
    except Exception as e:
        log_error(e)
        return jsonify({'status': 'error'})
    return jsonify({'status': 'success'})


@api.route('/unpublish/<string:registry_id>')
def unpublish_request(registry_id):
    log_info('Going to execute unpublish event for registry id %s.' % registry_id)
    try:
        registry_model = RegistryModel.create_from_registry_id(registry_id)
        if registry_model.status == 'active' or registry_model.status == 'error':
            log_info('Unpublishing video...')
            Unpublish.create_unpublish_state(registry_model).run()
    except Exception as e:
        log_error(e)
        return jsonify({'status': 'error'})
    return jsonify({'status': 'success'})


@api.route('/delete/<string:registry_id>')
def delete_request(registry_id):
    log_info('Going to delete video with registry id %s.' % registry_id)
    try:
        registry_model = RegistryModel.create_from_registry_id(registry_id)
        Deleting.create_deleting_state(registry_model).run()
    except Exception as e:
        log_error(e)
        return jsonify({'status': 'error'})
    return jsonify({'status': 'success'})
