from concurrent.futures import ThreadPoolExecutor

from flask import Flask

from connector import youtube, facebook


def create_app():
    app = Flask(__name__)
    app.register_blueprint(youtube)
    app.register_blueprint(facebook)
    return app


def execute_async(function, video_id):
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(function, video_id)


@youtube.route('/upload/youtube/<string:category_id>/<string:video_id>')
def upload_video_to_youtube(category_id, video_id):
    pass


@youtube.route('/update/youtube/<string:category_id>/<string:video_id>')
def update_video_on_youtube(category_id, video_id):
    pass


@youtube.route('/unpublish/youtube/<string:category_id>/<string:video_id>')
def unpublish_video_on_youtube(category_id, video_id):
    pass


@facebook.route('/upload/facebook/<string:category_id>/<string:video_id>')
def upload_video_to_facebook(category_id, video_id):
    pass


@facebook.route('/update/facebook/<string:category_id>/<string:video_id>')
def update_video_on_facebook(category_id, video_id):
    pass


@facebook.route('/unpublish/facebook/<string:category_id>/<string:video_id>')
def unpublish_video_on_facebook(category_id, video_id):
    pass
