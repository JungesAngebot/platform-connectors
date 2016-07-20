from concurrent.futures import ThreadPoolExecutor

from commonspy.logging import log_info
from flask import Flask, jsonify

from connector import youtube, api
from connector.db import change_status_of_process


def create_app():
    app = Flask(__name__)
    app.register_blueprint(youtube)
    return app


def execute_async(function, video_id):
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(function, video_id)


@api.route('/upload/<string:registry_id>')
def upload_video(registry_id):
    log_info('Going to upload video with registry id %s.' % registry_id)

    try:
        pass
    except Exception:
        change_status_of_process(registry_id, 'error')
        return jsonify(dict(
            status='error',
            registry_id=registry_id
        ))

    return jsonify(dict(
        status='success',
        registry_id=registry_id
    ))


@api.route('/update/<string:registry_id>')
def update_video(registry_id):
    log_info('Going to update video with registry id %s.' % registry_id)

    try:
        pass
    except Exception:
        change_status_of_process(registry_id, 'error')
        return jsonify(dict(
            status='error',
            registry_id=registry_id
        ))

    return jsonify(dict(
        status='success',
        registry_id=registry_id
    ))


@api.route('/unpublish/<string:registry_id>')
def unpublish_video(registry_id):
    log_info('Going to unpublish video with registry id %s.' % registry_id)

    try:
        pass
    except Exception:
        change_status_of_process(registry_id, 'error')
        return jsonify(dict(
            status='error',
            registry_id=registry_id
        ))

    return jsonify(dict(
        status='success',
        registry_id=registry_id
    ))
